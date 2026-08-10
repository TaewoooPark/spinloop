#!/usr/bin/env python3
"""Search a parameter until the simulation hits a target.

    tune.py TEMPLATE.mx3 --param Ku1_value --range 0.2e6 1.2e6 \
            --goal "last:mz >= 0.9" --budget 20 --time 1800

The template is an ordinary .mx3 with one line declaring the parameter:

    Ku1_value := 0.5e6

Every trial rewrites that one number and runs the script. Nothing else about
the template changes, so what ran is always readable.

Strategy: scan, then narrow. A coarse scan across the range runs as ONE batch
(`mumax3 -j`), which is where the fork's aggregate speed-up lives. If the goal
is bracketed between two neighbouring points, bisect into that bracket until
the tolerance or the budget runs out.

Scan-then-narrow is chosen over anything cleverer because its report is
readable: "I tried these five, it happens between these two, I looked there."
A researcher can check that reasoning without knowing what an optimiser is.

Stops for exactly one of four reasons, always reported:
    reached     the goal was met
    bracketed   the goal lies between two values but the tolerance was not met
    exhausted   the budget ran out
    impossible  the metric never approaches the target anywhere in the range
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import time
from dataclasses import dataclass, asdict, field
from pathlib import Path

HERE = Path(__file__).resolve()
for cand in (HERE.parents[3] / "lib", HERE.parents[2] / "lib"):
    if (cand / "mx3lib").is_dir():
        sys.path.insert(0, str(cand))
        break

from mx3lib import OutputDir, observe, run  # noqa: E402


# ---------------------------------------------------------------------------
# goals
# ---------------------------------------------------------------------------

COMPARATORS = ("==", ">=", "<=", ">", "<", "!=")


@dataclass
class Goal:
    metric: str        # last:mz | loop:coercivity | velocity:ext_dwpos | settled:mz
    comparator: str
    target: float
    tolerance: float = 0.0

    @classmethod
    def parse(cls, text: str, tolerance: float = 0.0) -> "Goal":
        for c in ("==", ">=", "<=", "!=", ">", "<"):
            if c in text:
                lhs, rhs = text.split(c, 1)
                return cls(lhs.strip(), c, float(rhs.strip()), tolerance)
        raise ValueError(
            f"goal {text!r} has no comparator. Write it like "
            f"'last:mz >= 0.9' or 'loop:coercivity == 0.02'. "
            f"Comparators: {', '.join(COMPARATORS)}"
        )

    def satisfied(self, value: float) -> bool:
        if value != value:  # NaN
            return False
        t, tol = self.target, self.tolerance
        if self.comparator == "==":
            return abs(value - t) <= (tol if tol else abs(t) * 0.02)
        if self.comparator == "!=":
            return abs(value - t) > (tol if tol else abs(t) * 0.02)
        return {">=": value >= t, "<=": value <= t,
                ">": value > t, "<": value < t}[self.comparator]

    def distance(self, value: float) -> float:
        """How far from satisfied, for bracketing. Zero once met."""
        if value != value:
            return float("inf")
        if self.satisfied(value):
            return 0.0
        return abs(value - self.target)

    def describe(self) -> str:
        return f"{self.metric} {self.comparator} {self.target:g}"


def measure(out: OutputDir, metric: str) -> float:
    """Evaluate a metric against one finished run.

    Metrics are deliberately few and each maps to something the engine or the
    table already provides -- a goal you cannot measure is a loop that cannot
    terminate.
    """
    table = out.table
    if table is None:
        raise ValueError(
            f"{out.path} has no table.txt, so nothing can be measured. "
            f"The template must call TableSave() or TableAutoSave()."
        )

    kind, _, arg = metric.partition(":")
    kind, arg = kind.strip(), arg.strip()

    if kind == "last":
        if not table.has(arg):
            raise ValueError(
                f"no column {arg!r} in table.txt (has: {table.names}). "
                f"Add it in the template with TableAdd({arg})."
            )
        return table.last(arg)

    if kind == "min" or kind == "max":
        if not table.has(arg):
            raise ValueError(f"no column {arg!r}; columns are {table.names}")
        col = [v for v in table.column(arg) if v == v]
        if not col:
            raise ValueError(f"column {arg!r} is empty or all NaN")
        return min(col) if kind == "min" else max(col)

    if kind == "abs":
        if not table.has(arg):
            raise ValueError(f"no column {arg!r}; columns are {table.names}")
        return abs(table.last(arg))

    if kind == "loop":
        field_col = "B_extx"
        for cand in ("B_extx", "B_exty", "B_extz"):
            if table.has(cand):
                field_col = cand
                break
        moment = {"B_extx": "mx", "B_exty": "my", "B_extz": "mz"}[field_col]
        r = observe.hysteresis(table.column(field_col), table.column(moment))
        val = getattr(r, arg, None)
        if val is None:
            raise ValueError(
                f"loop metric {arg!r} is not one of coercivity, remanence, "
                f"saturation, squareness"
            )
        return float(val)

    if kind == "velocity":
        col = arg or "ext_dwpos"
        if not table.has(col):
            raise ValueError(f"no column {col!r}; record it with TableAdd({col})")
        return observe.velocity(table.column("t"), table.column(col)).velocity

    if kind == "settled":
        return 0.0 if observe.settled(table.column(arg)).settled else 1.0

    raise ValueError(
        f"unknown metric kind {kind!r}. Use last:, min:, max:, abs:, loop:, "
        f"velocity: or settled:"
    )


# ---------------------------------------------------------------------------
# template
# ---------------------------------------------------------------------------

def substitute(template: str, param: str, value: float) -> str:
    """Replace the parameter's declared value, leaving everything else alone."""
    pattern = re.compile(
        rf"^(\s*{re.escape(param)}\s*:?=\s*)([^/\n]+)", re.MULTILINE)
    new, n = pattern.subn(lambda m: f"{m.group(1)}{value:.6g}", template)
    if n == 0:
        raise ValueError(
            f"the template has no line declaring {param!r}. Add one, e.g.\n"
            f"    {param} := 0.5e6\n"
            f"and use {param} wherever the value is needed."
        )
    return new


# ---------------------------------------------------------------------------
# trials
# ---------------------------------------------------------------------------

@dataclass
class Trial:
    value: float
    metric_value: float | None
    satisfied: bool
    status: str
    duration_s: float
    outdir: str | None = None
    error: str = ""


@dataclass
class Report:
    goal: str
    param: str
    stopped: str = ""
    reason: str = ""
    best_value: float | None = None
    best_metric: float | None = None
    bracket: list = field(default_factory=list)
    trials: list = field(default_factory=list)
    elapsed_s: float = 0.0
    runs: int = 0


class Tuner:
    def __init__(self, template: Path, param: str, goal: Goal, workdir: Path,
                 budget: int, time_budget: float, jobs: int,
                 run_timeout: float, threshold: bool = False,
                 verbose: bool = True):
        self.template_path = template
        self.template = template.read_text(encoding="utf-8")
        self.param = param
        self.goal = goal
        self.workdir = workdir
        self.budget = budget
        self.time_budget = time_budget
        self.jobs = jobs
        self.run_timeout = run_timeout
        self.threshold = threshold
        self.verbose = verbose
        self.trials: list[Trial] = []
        self.started = time.time()
        self.workdir.mkdir(parents=True, exist_ok=True)

    # -- budget ------------------------------------------------------------

    @property
    def spent(self) -> int:
        return len(self.trials)

    @property
    def elapsed(self) -> float:
        return time.time() - self.started

    def exhausted(self) -> str | None:
        if self.spent >= self.budget:
            return f"run budget spent ({self.budget} runs)"
        if self.elapsed >= self.time_budget:
            return f"time budget spent ({self.time_budget:.0f}s)"
        return None

    def say(self, msg: str) -> None:
        if self.verbose:
            print(msg, flush=True)

    # -- evaluation --------------------------------------------------------

    def _script_for(self, value: float, tag: str) -> Path:
        path = self.workdir / f"{self.template_path.stem}_{tag}.mx3"
        path.write_text(substitute(self.template, self.param, value),
                        encoding="utf-8")
        return path

    def evaluate(self, values: list[float]) -> list[Trial]:
        """Run a set of parameter values, as one batch when there is more than
        one -- that is the whole reason a coarse scan is cheap here."""
        remaining = self.budget - self.spent
        if remaining <= 0:
            return []
        values = values[:remaining]

        scripts = [self._script_for(v, f"{i:02d}_{v:.6g}".replace("+", ""))
                   for i, v in enumerate(values)]

        if len(scripts) == 1:
            results = [run.run_one(scripts[0], timeout=self.run_timeout)]
        else:
            results = run.run_batch(scripts, jobs=self.jobs,
                                    timeout=self.run_timeout * len(scripts))

        out: list[Trial] = []
        for value, res in zip(values, results):
            if res.status == "environment":
                raise EnvironmentError(res.error or "mumax3 cannot run here")
            metric_value, err = None, res.error
            satisfied = False
            if res.ok and res.output:
                try:
                    metric_value = measure(res.output, self.goal.metric)
                    satisfied = self.goal.satisfied(metric_value)
                except ValueError as exc:
                    err = str(exc)
            t = Trial(value, metric_value, satisfied, res.status,
                      res.duration_s, str(res.outdir) if res.outdir else None, err)
            out.append(t)
            self.trials.append(t)

            shown = "failed" if metric_value is None else f"{metric_value:.6g}"
            mark = "  <-- goal met" if satisfied else ""
            self.say(f"  {self.param} = {value:<12.6g} {self.goal.metric} = {shown}{mark}")
            if err and metric_value is None:
                self.say(f"      {err}")
        return out

    # -- search ------------------------------------------------------------

    def search(self, lo: float, hi: float, points: int, tolerance: float) -> Report:
        rep = Report(goal=self.goal.describe(), param=self.param)

        # 1. coarse scan, as one batch
        how = (f"one batch, -j {self.jobs}" if run.supports_parallel_queue()
               else "one batch, sequential - this build has no -j")
        self.say(f"Scanning {points} values of {self.param} from {lo:g} to {hi:g} "
                 f"({how}):")
        step = (hi - lo) / (points - 1) if points > 1 else 0
        grid = [lo + i * step for i in range(points)]
        scanned = self.evaluate(grid)

        usable = [t for t in scanned if t.metric_value is not None]
        if not usable:
            rep.stopped = "impossible"
            rep.reason = ("every trial failed to produce a measurable result. "
                          "The first error above is the one to fix.")
            return self._finish(rep)

        hit = next((t for t in usable if t.satisfied), None)
        if hit and not self.threshold:
            rep.stopped = "reached"
            rep.reason = f"the coarse scan already satisfies {self.goal.describe()}"
            return self._finish(rep, best=hit)

        if hit and self.threshold:
            # "Where does it start happening?" is a different question from
            # "make it happen". Narrow onto the boundary between the last value
            # that fails and the first that succeeds.
            ordered = sorted(usable, key=lambda t: t.value)
            edge = None
            for i in range(len(ordered) - 1):
                if not ordered[i].satisfied and ordered[i + 1].satisfied:
                    edge = (ordered[i], ordered[i + 1])
                    break
                if ordered[i].satisfied and not ordered[i + 1].satisfied:
                    edge = (ordered[i + 1], ordered[i])
                    break
            if edge is None:
                rep.stopped = "reached"
                rep.reason = (f"every value in {lo:g}..{hi:g} satisfies "
                              f"{self.goal.describe()}; the threshold is outside "
                              f"this range")
                return self._finish(rep, best=ordered[0])
            return self._narrow_threshold(rep, edge[0], edge[1], tolerance)

        # 2. bracket: neighbouring pair straddling the target
        bracket = self._bracket(usable)
        if bracket is None:
            closest = min(usable, key=lambda t: self.goal.distance(t.metric_value))
            rep.stopped = "impossible"
            rep.reason = (
                f"{self.goal.metric} never crosses {self.goal.target:g} anywhere in "
                f"{lo:g}..{hi:g}. Closest was {closest.metric_value:.6g} at "
                f"{self.param} = {closest.value:.6g}. Widen the range, or the goal "
                f"may not be reachable with this template."
            )
            return self._finish(rep, best=closest)

        a, b = bracket
        rep.bracket = [a.value, b.value]
        self.say(f"\nThe goal lies between {self.param} = {a.value:.6g} and "
                 f"{b.value:.6g}. Narrowing:")

        # 3. bisect
        lo_t, hi_t = a, b
        while True:
            stop = self.exhausted()
            if stop:
                rep.stopped = "exhausted"
                rep.reason = (f"{stop}; the answer is between {lo_t.value:.6g} and "
                              f"{hi_t.value:.6g}")
                best = min([lo_t, hi_t],
                           key=lambda t: self.goal.distance(t.metric_value))
                return self._finish(rep, best=best)

            if abs(hi_t.value - lo_t.value) <= tolerance:
                rep.stopped = "bracketed"
                rep.reason = (
                    f"narrowed to within {tolerance:g}: the goal is crossed between "
                    f"{lo_t.value:.6g} and {hi_t.value:.6g}, but no single value "
                    f"satisfies it exactly."
                )
                best = min([lo_t, hi_t],
                           key=lambda t: self.goal.distance(t.metric_value))
                return self._finish(rep, best=best)

            mid = (lo_t.value + hi_t.value) / 2
            got = self.evaluate([mid])
            if not got:
                rep.stopped = "exhausted"
                rep.reason = "budget ran out mid-search"
                return self._finish(rep, best=lo_t)
            t = got[0]
            if t.metric_value is None:
                rep.stopped = "impossible"
                rep.reason = (f"the run at {self.param} = {mid:.6g} failed: "
                              f"{t.error}")
                return self._finish(rep, best=lo_t)
            if t.satisfied:
                rep.stopped = "reached"
                rep.reason = f"{self.goal.describe()} is satisfied"
                return self._finish(rep, best=t)

            # keep the half that still straddles the target
            if (a.metric_value - self.goal.target) * (t.metric_value - self.goal.target) < 0:
                hi_t = t
            else:
                lo_t = t

    def _narrow_threshold(self, rep: Report, fails: Trial, works: Trial,
                          tolerance: float) -> Report:
        """Bisect the boundary between a failing and a succeeding value."""
        self.say(f"\n{self.goal.metric} starts satisfying the goal between "
                 f"{self.param} = {fails.value:.6g} and {works.value:.6g}. "
                 f"Narrowing onto the threshold:")
        rep.bracket = [fails.value, works.value]
        while True:
            stop = self.exhausted()
            if stop:
                rep.stopped = "exhausted"
                rep.reason = (f"{stop}; the threshold is between "
                              f"{fails.value:.6g} and {works.value:.6g}")
                return self._finish(rep, best=works)
            if abs(works.value - fails.value) <= tolerance:
                rep.stopped = "reached"
                rep.reason = (
                    f"threshold located: {self.goal.metric} begins to satisfy "
                    f"{self.goal.comparator} {self.goal.target:g} between "
                    f"{self.param} = {fails.value:.6g} and {works.value:.6g}"
                )
                rep.bracket = [fails.value, works.value]
                return self._finish(rep, best=works)

            mid = (fails.value + works.value) / 2
            got = self.evaluate([mid])
            if not got or got[0].metric_value is None:
                rep.stopped = "exhausted" if not got else "impossible"
                rep.reason = (f"could not evaluate {self.param} = {mid:.6g}"
                              + (f": {got[0].error}" if got else ""))
                return self._finish(rep, best=works)
            t = got[0]
            if t.satisfied:
                works = t
            else:
                fails = t

    def _bracket(self, trials: list[Trial]) -> tuple[Trial, Trial] | None:
        """Neighbouring pair whose metric straddles the target."""
        ordered = sorted(trials, key=lambda t: t.value)
        tgt = self.goal.target
        for i in range(len(ordered) - 1):
            a, b = ordered[i], ordered[i + 1]
            if (a.metric_value - tgt) * (b.metric_value - tgt) <= 0:
                return a, b
        return None

    def _finish(self, rep: Report, best: Trial | None = None) -> Report:
        if best is not None:
            rep.best_value = best.value
            rep.best_metric = best.metric_value
        rep.trials = [asdict(t) for t in self.trials]
        rep.elapsed_s = self.elapsed
        rep.runs = self.spent
        return rep


# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(
        description="Search a parameter until the simulation meets a target.",
        formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    ap.add_argument("template", type=Path)
    ap.add_argument("--param", required=True,
                    help="name of the declared parameter to vary")
    ap.add_argument("--range", nargs=2, type=float, required=True,
                    metavar=("LO", "HI"))
    ap.add_argument("--goal", required=True,
                    help="e.g. 'last:mz >= 0.9', 'loop:coercivity == 0.02'")
    ap.add_argument("--points", type=int, default=5, help="coarse scan points")
    ap.add_argument("--budget", type=int, default=20, help="maximum runs")
    ap.add_argument("--time", type=float, default=1800, dest="time_budget",
                    help="maximum seconds")
    ap.add_argument("--tolerance", type=float, default=0.0,
                    help="stop when the bracket is narrower than this")
    ap.add_argument("--goal-tolerance", type=float, default=0.0,
                    help="how close counts as equal, for '=='")
    ap.add_argument("--threshold", action="store_true",
                    help="find WHERE the goal starts being met, not just a value "
                         "that meets it")
    ap.add_argument("--jobs", type=int, default=3, help="queued per GPU for the scan")
    ap.add_argument("--run-timeout", type=float, default=600)
    ap.add_argument("--workdir", type=Path, default=Path("tune_runs"))
    ap.add_argument("--json", type=Path, help="write the full report here")
    ap.add_argument("--keep", action="store_true",
                    help="keep every trial's output directory")
    args = ap.parse_args()

    if not args.template.is_file():
        print(f"no such template: {args.template}", file=sys.stderr)
        return 2

    ok, why = run.available()
    if not ok:
        print(f"ENV: {why}", file=sys.stderr)
        return 2

    try:
        goal = Goal.parse(args.goal, args.goal_tolerance)
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 2

    lo, hi = sorted(args.range)
    tolerance = args.tolerance or (hi - lo) / 100

    print(f"Goal: {goal.describe()}")
    print(f"Varying {args.param} over {lo:g}..{hi:g}, "
          f"at most {args.budget} runs or {args.time_budget:.0f}s\n")

    tuner = Tuner(args.template, args.param, goal, args.workdir,
                  args.budget, args.time_budget, args.jobs, args.run_timeout,
                  threshold=args.threshold)
    try:
        rep = tuner.search(lo, hi, args.points, tolerance)
    except EnvironmentError as exc:
        print(f"\nENV: {exc}", file=sys.stderr)
        return 2
    except ValueError as exc:
        print(f"\n{exc}", file=sys.stderr)
        return 2

    print(f"\n{'-' * 60}")
    print(f"Stopped: {rep.stopped.upper()}")
    print(f"  {rep.reason}")
    if rep.best_value is not None:
        print(f"  best: {args.param} = {rep.best_value:.6g} "
              f"({goal.metric} = {rep.best_metric:.6g})")
    print(f"  {rep.runs} runs in {rep.elapsed_s:.0f}s")

    if args.json:
        args.json.write_text(json.dumps(asdict(rep), indent=2), encoding="utf-8")
        print(f"  full report: {args.json}")

    if not args.keep:
        for t in rep.trials:
            if t["outdir"] and t["value"] != rep.best_value:
                shutil.rmtree(t["outdir"], ignore_errors=True)

    return 0 if rep.stopped == "reached" else 1


if __name__ == "__main__":
    sys.exit(main())
