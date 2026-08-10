#!/usr/bin/env python3
"""Semantic linter for mumax3 .mx3 input files.

`mumax3 -vet` compiles a script: it catches undefined names, wrong argument
counts and unsupported syntax. It does not catch scripts that compile and then
mean the wrong thing. This linter covers that second layer.

The motivating case, verified against the real binary:

    SetGridSize(128e-9, 32, 1)     # vet says OK

128e-9 is truncated to int 0, the grid has zero cells, and the run dies at
startup. Worse are the ones that do not die: a cell larger than the exchange
length runs to completion and produces plausible, wrong physics.

Rules are grouped so you can lint by intent:

    physics     unit slips and discretisation errors        (wrong results)
    structure   ordering and completeness of the script     (nothing runs / nothing saved)
    fork        mumax3-ultrafast tuning knobs used as no-ops or without caveat
    convention  house style for generated scripts           (assumption header)
    perf        performance advisories                      (never blocking)

Usage:
    lint_mx3.py FILE...                      all rules
    lint_mx3.py --only physics,structure FILE...
    lint_mx3.py --skip convention FILE...
    lint_mx3.py --json FILE...

Exit: 0 clean or warnings only, 1 at least one ERROR, 2 usage/IO problem.

Standard library only. No third-party dependency, by design: this has to run
wherever mumax3 runs.
"""

from __future__ import annotations

import argparse
import ast
import json
import math
import re
import sys
from dataclasses import dataclass, asdict
from pathlib import Path

MU0 = 4e-7 * math.pi  # T·m/A

ALL_CATEGORIES = ("physics", "structure", "fork", "convention", "perf")

# Plausible ranges for the two parameters that set the exchange length.
# Outside these, a unit mistake is far more likely than an exotic material.
MSAT_RANGE = (1e3, 1e7)  # A/m   (permalloy 800e3; iron 1.7e6)
AEX_RANGE = (1e-13, 1e-10)  # J/m   (permalloy 13e-12)

# Evolution calls: anything that advances or minimises the state.
EVOLVE = ("run", "steps", "relax", "minimize", "runwhile")
# Anything that writes a result to disk.
OUTPUT = (
    "save", "saveas", "autosave", "snapshot", "snapshotas", "autosnapshot",
    "tablesave", "tableautosave", "tableadd", "tableaddvar", "tableprint",
    "fprintln",
)


@dataclass
class Finding:
    rule: str
    category: str
    severity: str  # ERROR | WARN | INFO
    line: int
    message: str
    hint: str = ""

    def fmt(self, path: str) -> str:
        loc = f"{path}:{self.line}" if self.line else path
        out = f"{loc}: {self.severity}: [{self.rule}] {self.message}"
        if self.hint:
            out += f"\n    -> {self.hint}"
        return out


# --------------------------------------------------------------------------
# Parsing helpers
# --------------------------------------------------------------------------

def strip_comments(src: str) -> str:
    """Blank out // and /* */ comments, preserving line structure."""
    out = []
    i, n = 0, len(src)
    in_block = in_line = in_str = False
    while i < n:
        c = src[i]
        nxt = src[i + 1] if i + 1 < n else ""
        if in_block:
            if c == "*" and nxt == "/":
                in_block = False
                out.append("  ")
                i += 2
                continue
            out.append("\n" if c == "\n" else " ")
        elif in_line:
            if c == "\n":
                in_line = False
                out.append("\n")
            else:
                out.append(" ")
        elif in_str:
            out.append(c)
            if c == '"' and src[i - 1] != "\\":
                in_str = False
        else:
            if c == "/" and nxt == "*":
                in_block = True
                out.append("  ")
                i += 2
                continue
            if c == "/" and nxt == "/":
                in_line = True
                out.append("  ")
                i += 2
                continue
            if c == '"':
                in_str = True
            out.append(c)
        i += 1
    return "".join(out)


_ALLOWED_NODES = (
    ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.USub, ast.UAdd,
    ast.Mod, ast.Name, ast.Load,
)
_CONSTS = {"pi": math.pi, "inf": math.inf, "mu0": MU0}


def safe_number(expr: str, symbols: dict | None = None):
    """Evaluate a purely numeric mx3 expression. None if it is not one.

    Uses ast rather than eval: a lint tool must not execute what it reads.
    `symbols` resolves script-local constants, so the common `N := 32;
    SetMesh(N, N, N, ...)` idiom is understood instead of skipped.
    """
    expr = expr.strip()
    if not expr:
        return None
    env = dict(_CONSTS)
    if symbols:
        env.update(symbols)
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError:
        return None
    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED_NODES):
            return None
        if isinstance(node, ast.Name) and node.id.lower() not in env:
            return None
    try:
        return eval(  # noqa: S307 - AST whitelisted above, names restricted
            compile(tree, "<mx3>", "eval"),
            {"__builtins__": {}},
            env,
        )
    except Exception:
        return None


def split_args(argstr: str) -> list[str]:
    """Split a call's argument list on top-level commas."""
    args, depth, cur = [], 0, ""
    for ch in argstr:
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        if ch == "," and depth == 0:
            args.append(cur)
            cur = ""
        else:
            cur += ch
    if cur.strip():
        args.append(cur)
    return [a.strip() for a in args]


CALL_RE = re.compile(r"\b([A-Za-z_]\w*)\s*\(")
ASSIGN_RE = re.compile(r"^\s*([A-Za-z_]\w*)\s*(?::?=)\s*(.+?)\s*$")
METHOD_RE = re.compile(r"\b([A-Za-z_]\w*)\s*\.\s*([A-Za-z_]\w*)\s*\(")


@dataclass
class Call:
    name: str
    args: list[str]
    line: int


@dataclass
class Assign:
    name: str
    value: str
    line: int


class Script:
    """A parsed view of an .mx3 file: ordered calls and assignments."""

    def __init__(self, path: Path):
        self.path = path
        self.raw = path.read_text(encoding="utf-8", errors="replace")
        self.code = strip_comments(self.raw)
        self.lines = self.code.splitlines()
        self.raw_lines = self.raw.splitlines()
        self.calls: list[Call] = []
        self.assigns: list[Assign] = []
        self.methods: list[tuple[str, str, int]] = []
        self.symbols: dict[str, float] = {}
        self._parse()
        self._build_symbols()

    def _build_symbols(self) -> None:
        """Resolve script-local numeric constants in declaration order, so a
        later one may be defined in terms of an earlier one."""
        for a in self.assigns:
            v = safe_number(a.value, self.symbols)
            if v is not None:
                self.symbols[a.name] = v

    def num(self, expr: str):
        """Evaluate an expression in this script's symbol table."""
        return safe_number(expr, self.symbols)

    def _parse(self) -> None:
        for idx, line in enumerate(self.lines, start=1):
            for m in METHOD_RE.finditer(line):
                self.methods.append((m.group(1).lower(), m.group(2).lower(), idx))
            for m in CALL_RE.finditer(line):
                start = m.end()
                depth, j = 1, start
                while j < len(line) and depth:
                    if line[j] == "(":
                        depth += 1
                    elif line[j] == ")":
                        depth -= 1
                    j += 1
                inner = line[start:j - 1] if depth == 0 else line[start:]
                # a method call's receiver was already captured above
                pre = line[:m.start()].rstrip()
                if pre.endswith("."):
                    continue
                self.calls.append(Call(m.group(1).lower(), split_args(inner), idx))
            am = ASSIGN_RE.match(line)
            if am and "==" not in line and not CALL_RE.match(line.strip()):
                name, value = am.group(1), am.group(2)
                # skip `for i := 0; ...` style headers
                if name.lower() not in ("for", "if", "else"):
                    self.assigns.append(Assign(name.lower(), value.strip(), idx))

    def call(self, name: str) -> list[Call]:
        return [c for c in self.calls if c.name == name.lower()]

    def has_call(self, *names: str) -> bool:
        low = {n.lower() for n in names}
        return any(c.name in low for c in self.calls)

    def assigned(self, name: str) -> list[Assign]:
        return [a for a in self.assigns if a.name == name.lower()]

    def last_value(self, name: str):
        """Last numerically-resolvable value assigned to `name`."""
        for a in reversed(self.assigned(name)):
            v = self.num(a.value)
            if v is not None:
                return v, a.line
        return None, 0

    def first_line_of(self, *names: str) -> int:
        low = {n.lower() for n in names}
        hits = [c.line for c in self.calls if c.name in low]
        return min(hits) if hits else 0


# --------------------------------------------------------------------------
# Rules
# --------------------------------------------------------------------------

def rule_grid_int(s: Script) -> list[Finding]:
    """SetGridSize/SetMesh cell counts must be integers.

    Verified: SetGridSize(128e-9, 32, 1) passes vet, truncates to 0, and the
    run panics at startup.
    """
    out = []
    # SetMesh is (Nx,Ny,Nz, cx,cy,cz, px,py,pz): only the first triple is a
    # cell count. Arguments 7-9 are PBC repeat counts and are legitimately 0.
    targets = [(c, c.args[:3]) for c in s.call("setgridsize")]
    targets += [(c, c.args[:3]) for c in s.call("setmesh")]
    for call, args in targets:
        for pos, a in enumerate(args):
            if not a:
                continue
            v = s.num(a)
            looks_float = bool(re.search(r"[eE]-|\.", a))
            if looks_float and (v is None or v != int(v) if v is not None else True):
                out.append(Finding(
                    "R-GRID-INT", "physics", "ERROR", call.line,
                    f"{call.name}() argument {pos + 1} is `{a}` - cell counts are "
                    f"integers, not lengths.",
                    "mx3 truncates float to int here and vet will not complain. "
                    "128e-9 becomes 0 cells. Put the length in SetCellSize().",
                ))
            elif v is not None and v == int(v) and int(v) <= 0:
                out.append(Finding(
                    "R-GRID-INT", "physics", "ERROR", call.line,
                    f"{call.name}() argument {pos + 1} evaluates to {int(v)} cells.",
                    "Grid dimensions must be >= 1.",
                ))
    return out


def rule_cell_si(s: Script) -> list[Finding]:
    """Cell sizes are metres. A value in the micron range is nearly always a
    forgotten e-9.

    Severity depends on whether the script models a real material. A script
    with physical Msat/Aex and metre-scale cells has a unit bug. A script with
    neither is a dimensionless fixture - the engine's own language tests use
    `setcellsize(1,1,1)` deliberately - so it only warrants a warning.
    """
    physical = False
    for name, lo, hi in (("msat", *MSAT_RANGE), ("aex", *AEX_RANGE)):
        v, _ = s.last_value(name)
        if v is not None and lo <= abs(v) <= hi:
            physical = True
            break
    sev = "ERROR" if physical else "WARN"
    out = []
    targets = [(c, c.args[:3]) for c in s.call("setcellsize")]
    targets += [(c, c.args[3:6]) for c in s.call("setmesh")]
    for call, args in targets:
        for pos, a in enumerate(args):
            v = s.num(a)
            if v is None:
                continue
            if v <= 0:
                out.append(Finding(
                    "R-CELL-SI", "physics", "ERROR", call.line,
                    f"cell size {pos + 1} is {a} = {v:g} m (must be positive).",
                ))
            elif v > 1e-6:
                hint = "Cell sizes are in metres. 4 nm is 4e-9, not 4 or 4e-6."
                if sev == "WARN":
                    hint += (" This script sets no physical Msat/Aex, so the "
                             "mesh may be a dimensionless fixture on purpose.")
                out.append(Finding(
                    "R-CELL-SI", "physics", sev, call.line,
                    f"cell size {pos + 1} is {a} = {v:g} m ({v * 1e9:.0f} nm) - "
                    f"implausibly large.",
                    hint,
                ))
    return out


def rule_msat(s: Script) -> list[Finding]:
    out = []
    for a in s.assigned("msat"):
        v = s.num(a.value)
        if v is None:
            continue
        if v == 0:
            continue  # legitimate: switching a region off
        if not (MSAT_RANGE[0] <= v <= MSAT_RANGE[1]):
            out.append(Finding(
                "R-MSAT", "physics", "WARN", a.line,
                f"Msat = {v:g} A/m is outside the plausible range "
                f"{MSAT_RANGE[0]:g}..{MSAT_RANGE[1]:g}.",
                "Msat is A/m. 800 emu/cm3 is 800e3 A/m; 1.7 T is 1.35e6 A/m.",
            ))
    return out


def rule_aex(s: Script) -> list[Finding]:
    out = []
    for a in s.assigned("aex"):
        v = s.num(a.value)
        if v is None or v == 0:
            continue
        if not (AEX_RANGE[0] <= abs(v) <= AEX_RANGE[1]):
            out.append(Finding(
                "R-AEX", "physics", "WARN", a.line,
                f"Aex = {v:g} J/m is outside the plausible range "
                f"{AEX_RANGE[0]:g}..{AEX_RANGE[1]:g}.",
                "Aex is J/m. Permalloy is 13e-12.",
            ))
    return out


def rule_exchange_length(s: Script) -> list[Finding]:
    """The classic discretisation error, and the reason this linter exists.

    l_ex = sqrt(2*Aex / (mu0 * Msat^2)). A cell coarser than l_ex cannot
    resolve a domain wall; the run still completes and still looks right.
    """
    msat, msat_line = s.last_value("msat")
    aex, _ = s.last_value("aex")
    if not msat or not aex or msat <= 0 or aex <= 0:
        return []

    cells = []
    for c in s.call("setcellsize"):
        cells.append((c, c.args[:3]))
    for c in s.call("setmesh"):
        cells.append((c, c.args[3:6]))
    if not cells:
        return []

    l_ex = math.sqrt(2 * aex / (MU0 * msat * msat))
    out = []
    for call, args in cells:
        vals = [s.num(a) for a in args]
        vals = [v for v in vals if v is not None and v > 0]
        if not vals:
            continue
        # The z cell may legitimately exceed l_ex in a thin film treated as a
        # single layer, so judge on the in-plane cells.
        inplane = vals[:2] if len(vals) >= 2 else vals
        worst = max(inplane)
        if worst > 2 * l_ex:
            out.append(Finding(
                "R-LEX", "physics", "ERROR", call.line,
                f"in-plane cell {worst * 1e9:.2f} nm exceeds twice the exchange "
                f"length ({l_ex * 1e9:.2f} nm) for Msat={msat:g}, Aex={aex:g}.",
                "The mesh cannot resolve a domain wall. Results will look "
                "plausible and be wrong. Refine the mesh or justify explicitly.",
            ))
        elif worst > l_ex:
            out.append(Finding(
                "R-LEX", "physics", "WARN", call.line,
                f"in-plane cell {worst * 1e9:.2f} nm exceeds the exchange length "
                f"({l_ex * 1e9:.2f} nm) for Msat={msat:g} (line {msat_line}), "
                f"Aex={aex:g}.",
                "Rule of thumb is cell <= l_ex. Refine, or state why the coarser "
                "mesh is acceptable for this observable.",
            ))
    return out


def rule_mesh_order(s: Script) -> list[Finding]:
    """The mesh must exist before anything reads or evolves the state."""
    out = []
    grid = s.first_line_of("setgridsize", "setmesh", "ext_initgeomfromovf")
    cell = s.first_line_of("setcellsize", "setmesh", "ext_initgeomfromovf")
    if not grid:
        out.append(Finding(
            "R-MESH-ORDER", "structure", "ERROR", 0,
            "no SetGridSize() or SetMesh(): the simulation has no mesh.",
        ))
    if not cell:
        out.append(Finding(
            "R-MESH-ORDER", "structure", "ERROR", 0,
            "no SetCellSize() or SetMesh(): cell dimensions are undefined.",
        ))
    if not grid or not cell:
        return out

    mesh_line = max(grid, cell)
    first_evolve = s.first_line_of(*EVOLVE)
    m_assign = [a.line for a in s.assigns if a.name == "m"]
    first_state = min(m_assign) if m_assign else 0
    for label, line in (("m = ...", first_state), ("evolution call", first_evolve)):
        if line and line < mesh_line:
            out.append(Finding(
                "R-MESH-ORDER", "structure", "ERROR", line,
                f"{label} appears at line {line}, before the mesh is complete "
                f"(line {mesh_line}).",
                "Set SetGridSize and SetCellSize before assigning m or running.",
            ))
    return out


def rule_no_output(s: Script) -> list[Finding]:
    """A run that saves nothing burns GPU time for no result."""
    if not s.has_call(*EVOLVE):
        return []
    if s.has_call(*OUTPUT):
        return []
    if s.has_call("expect", "expectv", "expectb", "print"):
        return []  # self-checking or printing script
    return [Finding(
        "R-NO-OUTPUT", "structure", "ERROR", s.first_line_of(*EVOLVE),
        "the script evolves the system but never saves anything.",
        "Add TableAutoSave(...) for scalars, AutoSave(m, ...) for fields, or "
        "Save(m) at the end.",
    )]


def rule_relax_temp(s: Script) -> list[Finding]:
    """Relax()/Minimize() switch thermal noise off.

    engine/minimizer.go: `relaxing = true // disable temperature noise`
    """
    temps = [a for a in s.assigned("temp") if (s.num(a.value) or 1) != 0]
    if not temps:
        return []
    out = []
    for c in s.calls:
        if c.name in ("relax", "minimize"):
            for t in temps:
                if t.line < c.line:
                    out.append(Finding(
                        "R-RELAX-TEMP", "physics", "WARN", c.line,
                        f"{c.name}() runs with Temp set at line {t.line}; "
                        f"relaxation disables thermal noise.",
                        "The relaxation is effectively at T=0. Use Run() for "
                        "finite-temperature dynamics, or set Temp after relaxing.",
                    ))
                    break
    return out


def rule_alpha(s: Script) -> list[Finding]:
    alpha, line = s.last_value("alpha")
    if alpha is None:
        if s.has_call(*EVOLVE):
            return [Finding(
                "R-ALPHA", "physics", "WARN", 0,
                "alpha is never set; the default damping may not be what you want.",
                "Set alpha explicitly (0.02 for dynamics, 1 for fast relaxation).",
            )]
        return []
    out = []
    if alpha == 0 and s.has_call("run", "steps", "relax", "minimize"):
        out.append(Finding(
            "R-ALPHA", "physics", "WARN", line,
            "alpha = 0 with an evolution call: undamped precession never relaxes.",
            "Relax()/Minimize() cannot converge and Run() conserves energy "
            "forever. Use alpha > 0 unless this is deliberate.",
        ))
    if alpha > 1:
        out.append(Finding(
            "R-ALPHA", "physics", "WARN", line,
            f"alpha = {alpha:g} is above 1 (over-damped).",
            "Physical damping is < 1. alpha=1 is the usual fast-relaxation value.",
        ))
    return out


def _truthy_assign(s: Script, name: str):
    for a in reversed(s.assigned(name)):
        val = a.value.strip().lower()
        if val in ("true", "1"):
            return a
        if val in ("false", "0"):
            return None
    return None


def rule_fork_speculative(s: Script) -> list[Finding]:
    """SpeculativeStep closes itself under several conditions - setting it
    there is a silent no-op, not a speed-up."""
    a = _truthy_assign(s, "speculativestep")
    if not a:
        return []
    conflicts = []
    fixdt, _ = s.last_value("fixdt")
    if fixdt:
        conflicts.append("FixDt")
    if [x for x in s.assigned("temp") if (s.num(x.value) or 1) != 0]:
        conflicts.append("finite Temp")
    if s.has_call("relax"):
        conflicts.append("Relax()")
    if _truthy_assign(s, "demagextrapolation"):
        conflicts.append("DemagExtrapolation")
    if not conflicts:
        return []
    return [Finding(
        "R-FORK-SPEC", "fork", "WARN", a.line,
        f"SpeculativeStep = true has no effect here: it closes itself under "
        f"{', '.join(conflicts)}.",
        "Remove it, or restructure so the speculative path can engage.",
    )]


def rule_fork_demag(s: Script) -> list[Finding]:
    a = _truthy_assign(s, "demagextrapolation")
    if not a:
        return []
    solver = None
    line = 0
    for c in s.call("setsolver"):
        v = s.num(c.args[0]) if c.args else None
        if v is not None:
            solver, line = int(v), c.line
    if solver is None:
        return [Finding(
            "R-FORK-DEMAG", "fork", "WARN", a.line,
            "DemagExtrapolation = true without an explicit SetSolver().",
            "Extrapolation applies to solvers 4/5/6 and fails closed elsewhere. "
            "Call SetSolver(5) to make the intent explicit.",
        )]
    if solver not in (4, 5, 6):
        return [Finding(
            "R-FORK-DEMAG", "fork", "WARN", line,
            f"DemagExtrapolation = true with SetSolver({solver}): unsupported, "
            f"so it falls back to exact convolution.",
            "Use solver 4, 5 or 6, or drop DemagExtrapolation.",
        )]
    return []


def rule_fork_accuracy(s: Script) -> list[Finding]:
    """Approximate knobs must be declared in the header, so a reader of the
    output knows the trajectory is not the reference one."""
    used = []
    if _truthy_assign(s, "speculativestep"):
        used.append("SpeculativeStep")
    if _truthy_assign(s, "demagextrapolation"):
        used.append("DemagExtrapolation")
    if not used:
        return []
    head = s.raw[:2000].lower()
    if any(w in head for w in ("approx", "caveat", "unverified", "a/b", "accuracy")):
        return []
    return [Finding(
        "R-FORK-ACC", "fork", "WARN", 0,
        f"{', '.join(used)} changes the trajectory but the header does not say so.",
        "These are approximations: SpeculativeStep diverges ~1% after a few "
        "thousand steps; DemagExtrapolation is problem-dependent. Record it in "
        "the header and A/B against a default run.",
    )]


def rule_header(s: Script) -> list[Finding]:
    head = s.raw[:2500]
    if not head.lstrip().startswith("/*"):
        return [Finding(
            "R-HDR", "convention", "ERROR", 1,
            "missing the leading assumption header block.",
            "Start the file with /* ... */ recording Units, Mesh, Materials, "
            "Outputs, and an Unverified line listing what the reader must check.",
        )]
    low = head.lower()
    missing = [k for k in ("units", "unverified") if k not in low]
    if missing:
        return [Finding(
            "R-HDR", "convention", "ERROR", 1,
            f"header block is missing: {', '.join(missing)}.",
            "The Unverified line is the point of the header: it separates what "
            "was machine-checked from what the physicist must still judge.",
        )]
    return []


def rule_size(s: Script) -> list[Finding]:
    """Below ~128^2 a fixed 172-187 us per-evaluation cost dominates on the
    measured M4; throughput per cell peaks near 256^2."""
    out = []
    for c in s.call("setgridsize"):
        vals = [s.num(a) for a in c.args[:3]]
        if any(v is None for v in vals) or len(vals) < 2:
            continue
        nx, ny = int(vals[0]), int(vals[1])
        if nx * ny < 128 * 128:
            out.append(Finding(
                "R-SIZE", "perf", "INFO", c.line,
                f"grid {nx}x{ny} is in the latency-bound regime.",
                "Below 128^2 a fixed ~172-187 us per evaluation dominates, so a "
                "wider GPU does not help. Batch parameter sweeps with "
                "`mumax3 -j 3 *.mx3` instead of enlarging the mesh.",
            ))
    return out


RULES = (
    rule_grid_int, rule_cell_si, rule_msat, rule_aex, rule_exchange_length,
    rule_mesh_order, rule_no_output, rule_relax_temp, rule_alpha,
    rule_fork_speculative, rule_fork_demag, rule_fork_accuracy,
    rule_header, rule_size,
)


def lint(path: Path, categories: set[str]) -> list[Finding]:
    s = Script(path)
    found: list[Finding] = []
    for rule in RULES:
        try:
            found.extend(f for f in rule(s) if f.category in categories)
        except Exception as exc:  # a broken rule must not block the workflow
            found.append(Finding(
                "R-INTERNAL", "structure", "WARN", 0,
                f"rule {rule.__name__} failed: {exc}",
            ))
    order = {"ERROR": 0, "WARN": 1, "INFO": 2}
    found.sort(key=lambda f: (order[f.severity], f.line))
    return found


def main() -> int:
    p = argparse.ArgumentParser(description="Semantic linter for mumax3 .mx3 files.")
    p.add_argument("files", nargs="+", type=Path)
    p.add_argument("--only", help="comma-separated categories to run")
    p.add_argument("--skip", help="comma-separated categories to skip")
    p.add_argument("--json", action="store_true", help="machine-readable output")
    p.add_argument("--quiet", action="store_true", help="only print ERRORs")
    args = p.parse_args()

    cats = set(ALL_CATEGORIES)
    if args.only:
        cats = {c.strip() for c in args.only.split(",") if c.strip()}
        unknown = cats - set(ALL_CATEGORIES)
        if unknown:
            print(f"unknown category: {', '.join(sorted(unknown))}", file=sys.stderr)
            return 2
    if args.skip:
        cats -= {c.strip() for c in args.skip.split(",")}

    results, n_err, n_warn = {}, 0, 0
    for f in args.files:
        if not f.is_file():
            print(f"not a file: {f}", file=sys.stderr)
            return 2
        findings = lint(f, cats)
        results[str(f)] = findings
        n_err += sum(1 for x in findings if x.severity == "ERROR")
        n_warn += sum(1 for x in findings if x.severity == "WARN")

    if args.json:
        print(json.dumps(
            {k: [asdict(x) for x in v] for k, v in results.items()},
            indent=2, ensure_ascii=False,
        ))
    else:
        for path, findings in results.items():
            shown = [x for x in findings if not (args.quiet and x.severity != "ERROR")]
            if not shown:
                print(f"{path}: clean")
                continue
            for x in shown:
                print(x.fmt(path))
        total = len(args.files)
        print(f"\n{total} file(s): {n_err} error(s), {n_warn} warning(s)")

    return 1 if n_err else 0


if __name__ == "__main__":
    sys.exit(main())
