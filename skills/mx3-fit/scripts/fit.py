#!/usr/bin/env python3
"""Fit several parameters of a mumax3 model to measured numbers: Levenberg-Marquardt over simulation runs.

    fit.py init   SPEC.json [--force]         check the spec, write the scripts of the starting set, create the state
    fit.py step   SPEC.json --budget 1500     run what fits in BUDGET seconds, save, exit; call again to continue
    fit.py status SPEC.json                   where the fit stands
    fit.py eval   SPEC.json --set Ms=8e5,alpha=0.01 --budget 900    evaluate one set by hand (recorded, cached)
    fit.py report SPEC.json                   best set, chi2, residuals, uncertainties, correlations

Words. A *run* is one simulation (one template with numbers filled in) and gives one measured number. An
*evaluation* is every run of the spec for one parameter set. chi2 = sum(((model - data) / sigma)^2).

Method. Evaluate the start; a finite-difference Jacobian (one evaluation per free parameter); then
Levenberg-Marquardt trial steps, each one evaluation, with Broyden updates of the Jacobian in between and a fresh
finite-difference Jacobian every `jacobian_every` accepted steps or when steps keep failing. When chi2 stops
falling, a last finite-difference Jacobian at the best set gives the uncertainties and correlations. Typical cost:
1 + P + (5 to 15) + P evaluations for P parameters.

Everything is saved after every run, so a `step` call that runs out of budget loses nothing: the next call goes on
from there. Identical scripts are never run twice (results are cached by script content), and several data may come
from one run: give them the same template and settings and different measure commands.

SPEC (JSON; paths relative to the directory you run fit.py from):
{
  "workdir": "scratch/fit",                 state.json, ledger.csv, report.md and report.json go here
  "script_dir": "scratch/fit/runs",         where the generated .mx3 go (default <workdir>/runs)
  "params": {
    "Ms":    {"init": 8.0e5, "min": 4e5, "max": 1.6e6, "placeholder": "@MS@"},
    "alpha": {"init": 0.02, "min": 0.002, "max": 0.2, "placeholder": "@ALPHA@"}
  },                                        placeholder: any text in the templates (required);
                                            scale: "log" (default when min > 0) or "lin"
  "constants": {"@TRUN@": "2e-9"},          optional: text substituted in every template
  "runs": [
    {"id": "f050", "template": "model/fmr.mx3.in", "set": {"@B@": "0.050"},
     "measure": "python3 tools/freq.py {out}", "value": 7.31e9, "sigma": 2e7},
    {"id": "m000", "template": "model/static.mx3.in", "set": {"@B@": "0"},
     "measure": "python3 tools/mz.py {out}", "value": 0.42, "sigma": 0.01, "skip_for": ["alpha"]}
  ],
  "record": "python3 tools/log_run.py {script} {value}",   optional, after every run that produced a value
  "run_timeout": 900, "jacobian_step": 0.02, "jacobian_every": 4, "max_evals": 60, "tolerance": 1e-3,
  "chi2_abs_tol": 0.1, "max_step": 0.5, "final_jacobian": true
}
- measure: a command line (run by bash) whose last printed number is the run's value; {out} is the output dir.
- record: placeholders {label} {id} {script} {out} {value} {sigma} {data} and {param:NAME}.
- skip_for: parameters this run's value cannot depend on (e.g. damping, for a run that only minimises the
  energy). Their Jacobian evaluations reuse the base value instead of running it. Only list what physics
  guarantees; when unsure, leave it out.
- jacobian_step: step in the scaled parameter: 0.02 is +2 % for a log parameter, 2 % of (max - min) for lin.
- max_step: largest change of any scaled parameter in one trial step (0.5 is a factor 1.65 for log).
- Converged: when a step lowers chi2 (or is expected to) by less than max(tolerance * chi2, chi2_abs_tol). A chi2
  change of 0.1 moves the parameters by about 0.3 sigma, below what the data resolve; smaller "improvements" of a
  simulated chi2 are mostly numerical noise.
Scripts are named <label>_<id>.mx3 (label e001, e002, ... = evaluation number); numbers are written with repr()
(exact float round-trip).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[3] / "lib"))
from mx3lib import run as mx3run  # noqa: E402

NUM = re.compile(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")
DEFAULTS = {"run_timeout": 900, "jacobian_step": 0.02, "jacobian_every": 4, "max_evals": 60, "tolerance": 1e-3,
            "chi2_abs_tol": 0.1, "max_step": 0.5, "final_jacobian": True, "constants": {}}


# ------------------------------------------------------------------ spec

def load_spec(path):
    try:
        spec = json.loads(Path(path).read_text(encoding="utf-8-sig"))     # tolerate a BOM (Windows editors)
    except (OSError, json.JSONDecodeError) as e:
        sys.exit(f"spec {path}: {e}")
    for k in ("params", "runs"):
        if not spec.get(k):
            sys.exit(f"spec: '{k}' is missing or empty")
    for k, v in DEFAULTS.items():
        spec.setdefault(k, v)
    spec.setdefault("workdir", "scratch/fit")
    spec.setdefault("script_dir", str(Path(spec["workdir"]) / "runs"))
    names = list(spec["params"])
    for n, p in spec["params"].items():
        for k in ("init", "min", "max"):
            if k not in p:
                sys.exit(f"spec: parameter {n} needs '{k}'")
        p["init"], p["min"], p["max"] = float(p["init"]), float(p["min"]), float(p["max"])
        if not (p["min"] < p["max"] and p["min"] <= p["init"] <= p["max"]):
            sys.exit(f"spec: parameter {n} needs min <= init <= max and min < max")
        if not p.get("placeholder"):
            sys.exit(f"spec: parameter {n} needs 'placeholder', the text that stands for it in the templates")
        p.setdefault("scale", "log" if p["min"] > 0 else "lin")
        if p["scale"] not in ("log", "lin"):
            sys.exit(f"spec: parameter {n}: scale is log or lin")
        if p["scale"] == "log" and p["min"] <= 0:
            sys.exit(f"spec: parameter {n} is log-scaled, so it needs min > 0")
    ids = [r.get("id") for r in spec["runs"]]
    if len(set(ids)) != len(ids) or None in ids:
        sys.exit("spec: every run needs an 'id', and ids must be unique")
    for r in spec["runs"]:
        for k in ("template", "measure", "value", "sigma"):
            if k not in r:
                sys.exit(f"spec: run {r['id']} needs '{k}'")
        r["value"], r["sigma"] = float(r["value"]), float(r["sigma"])
        if not r["sigma"] > 0:
            sys.exit(f"spec: run {r['id']} needs sigma > 0")
        if not Path(r["template"]).is_file():
            sys.exit(f"spec: run {r['id']}: template {r['template']} not found (paths are relative to {Path.cwd()})")
        bad = [s for s in r.get("skip_for", []) if s not in spec["params"]]
        if bad:
            sys.exit(f"spec: run {r['id']}: skip_for names {bad}, which are not parameters")
    if len(spec["runs"]) < len(names):
        print(f"WARNING: {len(spec['runs'])} data for {len(names)} parameters: the fit is under-determined", flush=True)
    spec["_names"] = names
    return spec


def to_x(spec, p):
    out = []
    for n in spec["_names"]:
        q, v = spec["params"][n], float(p[n])
        out.append(math.log(v) if q["scale"] == "log" else v / (q["max"] - q["min"]))
    return np.array(out)


def to_p(spec, x):
    p = {}
    for n, xi in zip(spec["_names"], x):
        q = spec["params"][n]
        v = math.exp(xi) if q["scale"] == "log" else xi * (q["max"] - q["min"])
        p[n] = float(min(max(v, q["min"]), q["max"]))
    return p


def clip_x(spec, x):
    return to_x(spec, to_p(spec, x))


def fmt(v):
    return repr(float(v))


def script_text(spec, run, p):
    text = Path(run["template"]).read_text(encoding="utf-8")
    for n in spec["_names"]:
        text = text.replace(spec["params"][n]["placeholder"], fmt(p[n]))
    for k, v in {**spec["constants"], **run.get("set", {})}.items():
        text = text.replace(k, str(v))
    left = sorted(set(re.findall(r"\{\{\w+\}\}|@[A-Za-z_]\w*@|\$\{\w+\}", text)))
    if left:
        sys.exit(f"run {run['id']}: {left} look like placeholders that the spec does not fill")
    return text


# ------------------------------------------------------------------ state

def state_path(spec):
    return Path(spec["workdir"]) / "state.json"


def load_state(spec):
    sp = state_path(spec)
    if not sp.exists():
        sys.exit(f"no fit in {sp.parent}: run `fit.py init SPEC` first")
    return json.loads(sp.read_text(encoding="utf-8"))


def save_state(spec, st):
    sp = state_path(spec)
    tmp = sp.with_suffix(".tmp")
    tmp.write_text(json.dumps(st, indent=1), encoding="utf-8")
    tmp.replace(sp)


def pid_alive(pid):
    if os.name == "nt":
        import ctypes
        k32 = ctypes.windll.kernel32
        h = k32.OpenProcess(0x1000, False, int(pid))            # PROCESS_QUERY_LIMITED_INFORMATION
        if not h:
            return False
        code = ctypes.c_ulong()
        ok = k32.GetExitCodeProcess(h, ctypes.byref(code))
        k32.CloseHandle(h)
        return bool(ok) and code.value == 259                    # STILL_ACTIVE
    try:
        os.kill(int(pid), 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


class Lock:
    """One fit.py at a time per fit. A shell that gives up on a command may leave it running; a second call must not
    write the same state while the first still does."""

    def __init__(self, spec, budget):
        self.path = Path(spec["workdir"]) / "lock.json"
        self.budget = budget

    def __enter__(self):
        if self.path.exists():
            try:
                held = json.loads(self.path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                held = {}
            if held.get("pid") and pid_alive(held["pid"]) and time.time() < held.get("until", 0) + 300:
                sys.exit(f"another fit.py (pid {held['pid']}, started {held.get('started')}) is still working on this fit, "
                         f"probably from a command whose shell gave up waiting. It stops by itself by "
                         f"{time.strftime('%H:%M:%S', time.localtime(held.get('until', 0)))}. Wait until then (or until "
                         f"`fit.py status` shows it finished), then call again. Next time give the shell command a time "
                         f"limit longer than --budget.")
        self.path.write_text(json.dumps({"pid": os.getpid(), "started": time.strftime("%H:%M:%S"),
                                         "until": time.time() + self.budget}), encoding="utf-8")
        return self

    def __exit__(self, *exc):
        try:
            if json.loads(self.path.read_text(encoding="utf-8")).get("pid") == os.getpid():
                self.path.unlink()
        except (OSError, json.JSONDecodeError):
            pass


def find_eval(st, label):
    return next((e for e in st["evals"] if e["label"] == label), None)


def new_eval(spec, st, x, purpose, perturbed=None, base=None):
    st["n_evals"] += 1
    ev = {"label": f"e{st['n_evals']:03d}", "purpose": purpose, "x": [float(v) for v in x],
          "params": to_p(spec, x), "values": {}, "perturbed": perturbed, "base": base, "seconds": 0.0}
    st["evals"].append(ev)
    return ev


# ------------------------------------------------------------------ running one evaluation

def shell(cmd):
    """Run a command line the way the caller's shell would: bash where there is one (Git Bash on Windows)."""
    bash = None
    if os.name == "nt":
        bash = os.environ.get("CLAUDE_CODE_GIT_BASH_PATH") or shutil.which("bash")
    argv = [bash, "-c", cmd] if bash else cmd
    return subprocess.run(argv, shell=not bash, capture_output=True, text=True, encoding="utf-8", errors="replace")


def qpath(p):
    return shlex.quote(str(p).replace("\\", "/"))


def measure(cmd, out_dir):
    r = shell(cmd.replace("{out}", qpath(out_dir)))
    lines = [l for l in (r.stdout or "").splitlines() if l.strip()]
    nums = NUM.findall(lines[-1]) if lines else []
    if r.returncode != 0 or not nums:
        return None, ((r.stderr or "") + (r.stdout or "")).strip()[-300:] or f"exit {r.returncode}, no number printed"
    return float(nums[-1]), ""


def ledger_append(spec, row):
    path = Path(spec["workdir"]) / "ledger.csv"
    new = not path.exists()
    with open(path, "a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(row))
        if new:
            w.writeheader()
        w.writerow(row)


def write_scripts(spec, ev):
    """Write the evaluation's scripts (one file per distinct script text) without running them."""
    sdir = Path(spec["script_dir"])
    sdir.mkdir(parents=True, exist_ok=True)
    paths, seen = [], set()
    for run in spec["runs"]:
        text = script_text(spec, run, ev["params"])
        if text in seen:
            continue
        seen.add(text)
        script = sdir / f"{ev['label']}_{run['id']}.mx3"
        if not script.exists() or script.read_text(encoding="utf-8") != text:
            script.write_text(text, encoding="utf-8", newline="\n")
        paths.append(script)
    return paths


def record(spec, ev, run, script, out, value):
    cmd = spec["record"]
    for k, v in {"{label}": ev["label"], "{id}": run["id"], "{script}": qpath(script), "{out}": qpath(out),
                 "{value}": fmt(value), "{sigma}": fmt(run["sigma"]), "{data}": fmt(run["value"])}.items():
        cmd = cmd.replace(k, v)
    cmd = re.sub(r"\{param:([A-Za-z_]\w*)\}", lambda m: fmt(ev["params"][m.group(1)]), cmd)
    rr = shell(cmd)
    if rr.returncode:
        print(f"    record hook failed for {Path(script).name}: "
              f"{((rr.stderr or '') + (rr.stdout or '')).strip()[-200:]}", flush=True)


def evaluate(spec, st, ev, deadline):
    """Run what is still missing for evaluation `ev`. True when it is complete, False when the budget ran out.

    The cache is keyed by script content: a script is simulated once, and every measure command applied to it is
    remembered, so several data can come from one run (e.g. a frequency and a decay rate from one ringdown)."""
    base = find_eval(st, ev.get("base")) if ev.get("base") else None
    sdir = Path(spec["script_dir"])
    sdir.mkdir(parents=True, exist_ok=True)
    timeout = float(spec["run_timeout"])
    for run in spec["runs"]:
        rid, mcmd = run["id"], run["measure"]
        if rid in ev["values"]:
            continue
        row = {"label": ev["label"], "purpose": ev["purpose"], "id": rid, "value": None, "data": run["value"],
               "sigma": run["sigma"], "residual": None, "status": "", "seconds": 0.0, "script": "", "sha256": "",
               **{f"p_{n}": ev["params"][n] for n in spec["_names"]}}
        if ev.get("perturbed") in run.get("skip_for", []) and base and base["values"].get(rid) is not None:
            ev["values"][rid] = base["values"][rid]
            ledger_append(spec, {**row, "value": ev["values"][rid], "status": f"reused from {base['label']} (skip_for)"})
            save_state(spec, st)
            continue
        text = script_text(spec, run, ev["params"])
        sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
        hit = st["cache"].get(sha)
        if hit and mcmd in hit["values"]:
            value = hit["values"][mcmd]
            ev["values"][rid] = value
            ledger_append(spec, {**row, "value": value, "status": "cached (this script and measure already done)",
                                 "script": hit["script"], "sha256": sha,
                                 "residual": None if value is None else (value - run["value"]) / run["sigma"]})
            save_state(spec, st)
            continue
        if hit and Path(hit["out"]).is_dir():           # simulated before, measured differently: measure only
            script, out, secs, status = Path(hit["script"]), Path(hit["out"]), 0.0, "ok (measured on an earlier run)"
            value, err = measure(mcmd, out)
        else:
            expect = st["dur"].get(rid, st.get("slowest_run_s", 0.0))
            left = deadline - time.time()
            if left < max(1.3 * expect + 5, 10):
                return False
            script = sdir / f"{ev['label']}_{rid}.mx3"
            if not script.exists() or script.read_text(encoding="utf-8") != text:
                script.write_text(text, encoding="utf-8", newline="\n")
            res = mx3run.run_one(script, timeout=min(timeout, left))
            for w in res.warnings:
                print(f"    WARNING {script.name}: {w}", flush=True)
            ev["seconds"] = ev.get("seconds", 0.0) + res.duration_s
            if res.status == "timeout" and res.duration_s < 0.95 * timeout:
                key = f"{ev['label']}/{rid}"
                st["budget_timeouts"][key] = st["budget_timeouts"].get(key, 0) + 1
                if st["budget_timeouts"][key] < 2:
                    print(f"    {script.name}: stopped at the end of the budget; it runs again in the next call",
                          flush=True)
                    save_state(spec, st)
                    return False
            st["dur"][rid] = res.duration_s
            st["slowest_run_s"] = max(st.get("slowest_run_s", 0.0), res.duration_s)
            out = res.outdir or mx3run.default_outdir(script)
            secs, status = res.duration_s, res.status
            if res.ok:
                st["cache"][sha] = {"script": str(script), "out": str(out), "values": {}}
                value, err = measure(mcmd, out)
            else:
                value, err = None, res.error or res.status
        ev["values"][rid] = value
        if sha in st["cache"] and value is not None:     # a failed measure is retried next time (the tool may be fixed)
            st["cache"][sha]["values"][mcmd] = value
        if value is None:
            print(f"    {script.name}: no value ({status}: {err[:200]})", flush=True)
        ledger_append(spec, {**row, "value": value, "status": status if value is not None else f"{status}: {err[:120]}",
                             "seconds": round(secs, 1), "script": str(script), "sha256": sha,
                             "residual": None if value is None else (value - run["value"]) / run["sigma"]})
        if spec.get("record") and value is not None:
            record(spec, ev, run, script, out, value)
        save_state(spec, st)
    return True


def residuals(spec, ev):
    out = []
    for run in spec["runs"]:
        v = ev["values"].get(run["id"])
        out.append(float("nan") if v is None else (v - run["value"]) / run["sigma"])
    return np.array(out)


def chi2_of(r):
    return float(np.sum(r * r)) if np.all(np.isfinite(r)) else float("inf")


def show(ev):
    return (f"  {ev['label']} {ev['purpose']:<24} chi2 {ev.get('chi2', float('nan')):<10.5g} " +
            " ".join(f"{k}={v:.6g}" for k, v in ev["params"].items()) + f"   ({ev.get('seconds', 0):.0f} s)")


# ------------------------------------------------------------------ Levenberg-Marquardt with Broyden updates

def plan_trial(spec, st):
    J, r = np.array(st["J"]), np.array(st["r"])
    A, g = J.T @ J, J.T @ r
    d = np.diag(A).copy()
    d = np.maximum(d, 1e-9 * max(float(d.max()), 1e-30))
    dx = -np.linalg.solve(A + st["lam"] * np.diag(d), g)
    big = float(np.max(np.abs(dx))) if len(dx) else 0.0
    if big > float(spec["max_step"]):
        dx *= float(spec["max_step"]) / big
    xt = clip_x(spec, np.array(st["x"]) + dx)
    st["x_trial"] = [float(v) for v in xt]
    r0 = float(r @ r)
    rp = r + J @ (xt - np.array(st["x"]))
    st["pred_dec"] = r0 - float(rp @ rp)                           # chi2 decrease the linear model expects


def negligible(spec, chi2, decrease):
    return decrease < max(float(spec["tolerance"]) * chi2, float(spec["chi2_abs_tol"]))


def jacobian_is_current(spec, st):
    """The finite-difference Jacobian was taken at the best set, or within a tenth of a step of it."""
    if st.get("J_fd_at") == st.get("best"):
        return True
    if st.get("J_fd_x") is None:
        return False
    return float(np.max(np.abs(np.array(st["x"]) - np.array(st["J_fd_x"])))) < 0.1 * float(spec["jacobian_step"])


def start_jacobian(st, final=False):
    st["phase"], st["jac_cols"], st["jac_final"] = "jacobian", [], final


def finish(st, why):
    st["phase"], st["stop"] = "done", why


def advance(spec, st, deadline):
    """Run the fit's state machine until it is done or the deadline comes."""
    h = float(spec["jacobian_step"])
    n = len(spec["_names"])
    while time.time() < deadline and st["phase"] != "done":
        if not st.get("pending"):
            if st["n_evals"] >= int(spec["max_evals"]):
                finish(st, f"max_evals ({spec['max_evals']}) reached")
                save_state(spec, st)
                break
            if st["phase"] == "jacobian":
                j = len(st["jac_cols"])
                x = np.array(st["x"])
                xj = x.copy()
                xj[j] += h
                xj = clip_x(spec, xj)
                if abs(xj[j] - x[j]) < 0.5 * h:          # at the upper bound: step down instead
                    xj = x.copy()
                    xj[j] -= h
                    xj = clip_x(spec, xj)
                ev = new_eval(spec, st, xj, f"jacobian {spec['_names'][j]}", perturbed=spec["_names"][j],
                              base=st["best"])
            else:
                if negligible(spec, st["chi2"], st.get("pred_dec", float("inf"))):
                    if jacobian_is_current(spec, st):
                        finish(st, "converged: no step is expected to lower chi2 by more than the tolerance")
                        save_state(spec, st)
                        break
                    start_jacobian(st)                   # the Broyden Jacobian may mislead: check with a fresh one
                    save_state(spec, st)
                    continue
                ev = new_eval(spec, st, np.array(st["x_trial"]), f"trial lambda={st['lam']:.2g}")
            st["pending"] = ev["label"]
            save_state(spec, st)
        ev = find_eval(st, st["pending"])
        if not evaluate(spec, st, ev, deadline):
            save_state(spec, st)
            break
        st["pending"] = None
        r = residuals(spec, ev)
        c2 = chi2_of(r)
        ev["chi2"] = c2
        print(show(ev), flush=True)
        xe = np.array(ev["x"])
        if st["phase"] == "start":
            if not np.isfinite(c2):
                bad = [run["id"] for run, ri in zip(spec["runs"], r) if not np.isfinite(ri)]
                finish(st, f"the starting set has runs without a value ({', '.join(bad)}): see ledger.csv, fix the "
                           f"template or measure command, then `fit.py init SPEC --force`")
            else:
                st["x"], st["r"], st["chi2"], st["best"] = [float(v) for v in xe], r.tolist(), c2, ev["label"]
                start_jacobian(st)
        elif st["phase"] == "jacobian":
            j = len(st["jac_cols"])
            dx = xe[j] - st["x"][j]
            col = (r - np.array(st["r"])) / dx
            if not np.all(np.isfinite(col)):
                bad = [run["id"] for run, c in zip(spec["runs"], col) if not np.isfinite(c)]
                st["warnings"].append(f"{ev['label']}: no value for {', '.join(bad)}; their derivative "
                                      f"d/d{spec['_names'][j]} is set to 0")
                col = np.nan_to_num(col, nan=0.0, posinf=0.0, neginf=0.0)
            st["jac_cols"].append(col.tolist())
            if len(st["jac_cols"]) == n:
                st["J"] = np.array(st["jac_cols"]).T.tolist()
                st["J_fd"], st["J_fd_at"], st["J_fd_x"] = st["J"], st["best"], st["x"]
                st["accepted_since_full"], st["rejects"] = 0, 0
                if st.get("jac_final"):
                    finish(st, st.get("converged_why", "converged"))
                else:
                    st["phase"] = "trial"
                    plan_trial(spec, st)
        else:  # trial
            J, x0, r0 = np.array(st["J"]), np.array(st["x"]), np.array(st["r"])
            s = xe - x0
            if np.all(np.isfinite(r)) and float(s @ s) > 0:
                st["J"] = (J + np.outer((r - r0) - J @ s, s) / float(s @ s)).tolist()     # Broyden rank-1 update
            if c2 < st["chi2"]:
                dec = st["chi2"] - c2
                small = negligible(spec, st["chi2"], dec)
                step = float(np.max(np.abs(s)))
                st["x"], st["r"], st["chi2"], st["best"] = [float(v) for v in xe], r.tolist(), c2, ev["label"]
                st["lam"] = max(st["lam"] / 3, 1e-7)
                st["rejects"] = 0
                st["accepted_since_full"] += 1
                st["history"].append({"label": ev["label"], "chi2": c2, "accepted": True})
                if small or step < 1e-4:
                    st["converged_why"] = (f"the last step lowered chi2 by only {dec:.3g}" if small
                                           else "the last step changed the parameters by < 1e-4")
                    if spec["final_jacobian"] and not jacobian_is_current(spec, st):
                        start_jacobian(st, final=True)
                    else:
                        finish(st, st["converged_why"])
                elif st["accepted_since_full"] >= int(spec["jacobian_every"]):
                    start_jacobian(st)
                else:
                    plan_trial(spec, st)
            else:
                st["lam"] *= 4
                st["rejects"] += 1
                st["history"].append({"label": ev["label"], "chi2": c2, "accepted": False})
                if st["rejects"] >= 3 and not jacobian_is_current(spec, st):
                    st["lam"] = max(st["lam"] / 16, 1e-3)
                    start_jacobian(st)
                elif st["rejects"] >= 5:
                    finish(st, "no step from the best set lowers chi2 in five tries (a minimum, a narrow valley, or "
                               "simulation noise larger than the remaining improvement)")
                else:
                    plan_trial(spec, st)
        save_state(spec, st)


# ------------------------------------------------------------------ report

def report(spec, st, write=True):
    names = spec["_names"]
    best = find_eval(st, st.get("best"))
    if not best:
        print("no complete evaluation yet")
        return
    r = residuals(spec, best)
    c2 = chi2_of(r)
    m, n = len(r), len(names)
    dof = max(m - n, 1)
    fresh = jacobian_is_current(spec, st)
    J = np.array(st["J_fd"] if fresh else st["J"]) if st.get("J") else None
    lines = [f"# fit report, {time.strftime('%Y-%m-%d %H:%M:%S')}", "",
             f"best set {best['label']}: chi2 = {c2:.5g} for {m} data and {n} free parameters "
             f"(dof {dof}; at the noise level chi2 is about {dof} +- {math.sqrt(2 * dof):.1f})",
             f"state: {st['phase']}" + (f" ({st['stop']})" if st.get("stop") else "") +
             f"; {st['n_evals']} evaluations, {sum(h['accepted'] for h in st['history'])} accepted steps", ""]
    out = {"best": best["label"], "chi2": c2, "dof": dof, "params": best["params"], "sigma": {},
           "sigma_scaled": {}, "correlation": None, "jacobian": ("finite-difference at the best set" if st.get("J_fd_at") == best["label"] else
                         f"finite-difference at {st.get('J_fd_at')}, within 0.1 step of the best set") if fresh else
           ("Broyden-updated (approximate)" if J is not None else None)}
    if J is not None:
        lines.append("Jacobian: " + out["jacobian"])
        try:
            C = np.linalg.inv(J.T @ J)
            sx = np.sqrt(np.clip(np.diag(C), 0, None))
            den = np.outer(np.where(sx > 0, sx, 1), np.where(sx > 0, sx, 1))
            corr = C / den
            scale = math.sqrt(max(c2 / dof, 1.0))
            lines += ["", "| parameter | value | 1 sigma | relative | 1 sigma x sqrt(chi2/dof) if > 1 | note |",
                      "|---|---|---|---|---|---|"]
            for i, k in enumerate(names):
                q, v = spec["params"][k], best["params"][k]
                s = v * sx[i] if q["scale"] == "log" else sx[i] * (q["max"] - q["min"])
                out["sigma"][k], out["sigma_scaled"][k] = s, s * scale
                note = "AT A BOUND" if v <= q["min"] * (1 + 1e-9) or v >= q["max"] * (1 - 1e-9) else ""
                lines.append(f"| {k} | {v:.6g} | {s:.3g} | {s / abs(v) if v else float('nan'):.2%} | "
                             f"{s * scale:.3g} | {note} |")
            out["correlation"] = corr.tolist()
            pairs = [(names[i], names[j], corr[i, j]) for i in range(n) for j in range(i + 1, n)]
            lines += ["", "correlations: " + "; ".join(f"{a}-{b} {c:+.2f}" for a, b, c in pairs)]
            strong = [f"{a}-{b}" for a, b, c in pairs if abs(c) > 0.9]
            if strong:
                lines.append(f"strongly correlated (|c| > 0.9): {', '.join(strong)}: the data fix a combination of "
                             f"these better than each one")
            sens = np.abs(J) / np.maximum(np.abs(J).sum(axis=1, keepdims=True), 1e-300)
            lines += ["", "what each datum responds to (share of |d residual / d scaled parameter|):"]
            for i, run in enumerate(spec["runs"]):
                order = np.argsort(-sens[i])[:2]
                lines.append(f"  {run['id']:<14} " + ", ".join(f"{names[k]} {sens[i, k]:.0%}" for k in order))
        except np.linalg.LinAlgError:
            lines.append("the Jacobian is singular: some parameter changes no datum, or two act identically")
    lines += ["", "| run | data | model | sigma | residual (sigma) |", "|---|---|---|---|---|"]
    for run, ri in zip(spec["runs"], r):
        v = best["values"].get(run["id"])
        lines.append(f"| {run['id']} | {run['value']:.6g} | {'-' if v is None else f'{v:.6g}'} | {run['sigma']:.3g} "
                     f"| {ri:+.2f} |")
    order = np.argsort(-np.abs(np.nan_to_num(r, nan=1e30)))[:3]
    lines += ["", "largest residuals: " + ", ".join(f"{spec['runs'][i]['id']} ({r[i]:+.1f})" for i in order)]
    if st.get("warnings"):
        lines += ["", "warnings:"] + [f"  {w}" for w in st["warnings"][-10:]]
    text = "\n".join(lines)
    print(text)
    if write:
        (Path(spec["workdir"]) / "report.md").write_text(text + "\n", encoding="utf-8")
        (Path(spec["workdir"]) / "report.json").write_text(json.dumps(out, indent=1), encoding="utf-8")


# ------------------------------------------------------------------ commands

def cmd_init(spec, a):
    Path(spec["workdir"]).mkdir(parents=True, exist_ok=True)
    with Lock(spec, 60):
        _init(spec, a)


def _init(spec, a):
    wd = Path(spec["workdir"])
    prev = {}
    if state_path(spec).exists():
        if not a.force:
            sys.exit(f"{state_path(spec)} exists: this fit has started. `fit.py step` continues it; "
                     f"`init --force` starts over (finished runs stay cached)")
        prev = json.loads(state_path(spec).read_text(encoding="utf-8"))
    p0 = {k: v["init"] for k, v in spec["params"].items()}
    st = {"phase": "start", "x": [float(v) for v in to_x(spec, p0)], "n_evals": prev.get("n_evals", 0),
          "evals": [], "history": [], "lam": 1e-2, "pending": None, "cache": prev.get("cache", {}), "dur": {},
          "budget_timeouts": {}, "warnings": [], "accepted_since_full": 0, "rejects": 0,
          "created": time.strftime("%Y-%m-%dT%H:%M:%S")}
    ev = new_eval(spec, st, np.array(st["x"]), "start")
    st["pending"] = ev["label"]
    paths = write_scripts(spec, ev)
    save_state(spec, st)
    n = len(spec["_names"])
    print(f"fit initialised in {wd}: {n} parameters, {len(spec['runs'])} runs per evaluation.\n"
          f"The starting set's scripts are written ({paths[0]} ... {paths[-1].name}): vet one before `fit.py step`.\n"
          f"Expected cost: 1 + {n} (Jacobian) + 5 to 15 (steps) + {n} (final Jacobian) evaluations.")


def cmd_step(spec, a):
    t0 = time.time()
    with Lock(spec, a.budget):
        st = load_state(spec)
        advance(spec, st, t0 + a.budget)
    st = load_state(spec)
    msg = f"stopped after {time.time() - t0:.0f} s: phase {st['phase']}"
    if st.get("stop"):
        msg += f" ({st['stop']})"
    if st.get("pending"):
        ev = find_eval(st, st["pending"])
        msg += f"; {ev['label']} ({ev['purpose']}) has {len(ev['values'])}/{len(spec['runs'])} runs"
    if st.get("best"):
        msg += f"; best chi2 {st['chi2']:.5g} at {st['best']}"
    print(msg)
    print("next: `fit.py report SPEC`" if st["phase"] == "done" else "next: `fit.py step SPEC --budget N` again")


def cmd_status(spec, a):
    st = load_state(spec)
    print(f"phase {st['phase']}" + (f" ({st['stop']})" if st.get("stop") else "") +
          f"; {st['n_evals']} evaluations; lambda {st['lam']:.2g}; pending {st.get('pending')}; "
          f"slowest run {st.get('slowest_run_s', 0):.0f} s")
    for e in st["evals"][-15:]:
        done = len(e["values"])
        tag = "" if done == len(spec["runs"]) else f"  [{done}/{len(spec['runs'])} runs]"
        print(show(e) + tag)
    if st.get("best"):
        print(f"best: {st['best']}, chi2 {st['chi2']:.5g}")
    for w in st.get("warnings", [])[-5:]:
        print(f"warning: {w}")


def cmd_eval(spec, a):
    with Lock(spec, a.budget):
        _eval(spec, a)


def _eval(spec, a):
    st = load_state(spec)
    p = {k: v["init"] for k, v in spec["params"].items()}
    best = find_eval(st, st.get("best"))
    if best:
        p.update(best["params"])
    for kv in (a.set or "").split(","):
        if kv.strip():
            k, _, v = kv.partition("=")
            if k.strip() not in spec["params"]:
                sys.exit(f"unknown parameter {k.strip()}; the parameters are {', '.join(spec['_names'])}")
            p[k.strip()] = float(v)
    x = to_x(spec, p)
    ev = next((e for e in st["evals"] if e["purpose"] == "manual" and np.allclose(e["x"], x, rtol=0, atol=1e-12)
               and len(e["values"]) < len(spec["runs"])), None)
    if ev is None:
        ev = new_eval(spec, st, x, "manual")
    save_state(spec, st)
    done = evaluate(spec, st, ev, time.time() + a.budget)
    if done:
        ev["chi2"] = chi2_of(residuals(spec, ev))
        print(show(ev))
    else:
        print(f"{ev['label']}: {len(ev['values'])}/{len(spec['runs'])} runs done; the same command continues it")
    save_state(spec, st)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["init", "step", "status", "eval", "report"])
    ap.add_argument("spec")
    ap.add_argument("--budget", type=float, default=100,
                    help="seconds this call may use (default 100); keep it below your shell's command time limit")
    ap.add_argument("--set", help="eval: NAME=value,... (the others from the best set so far, else from init)")
    ap.add_argument("--force", action="store_true", help="init: start over (finished runs stay cached)")
    a = ap.parse_args()
    spec = load_spec(a.spec)
    if a.command == "report":
        report(spec, load_state(spec))
    else:
        {"init": cmd_init, "step": cmd_step, "status": cmd_status, "eval": cmd_eval}[a.command](spec, a)


if __name__ == "__main__":
    main()
