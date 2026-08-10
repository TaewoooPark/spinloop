#!/usr/bin/env python3
"""Is the mesh fine enough?

Runs the same physics at several cell sizes and reports the coarsest one whose
answer you can trust.

    converge.py TEMPLATE.mx3 --grid-param N --cell-param cell \
                --metric "loop:coercivity" --cells 32 64 128

The template must declare the two together, so that halving the cell doubles
the grid and the physical size stays put:

    N  := 64
    dx := 4e-9
    SetGridSize(N, N, 1)
    SetCellSize(dx, dx, 2e-9)

Both are rewritten on each trial with N*cell held constant. Rewriting them in
Python rather than computing the grid inside mx3 avoids the float-to-int
truncation trap that `mumax3 -vet` does not catch.

Why this is worth doing here: a convergence study is five runs of the same
problem. On a queue that is five waits and nobody bothers. On a laptop that
finishes in seconds it is the difference between a number and a result.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve()
for cand in (HERE.parents[3] / "lib", HERE.parents[2] / "lib"):
    if (cand / "mx3lib").is_dir():
        sys.path.insert(0, str(cand))
        break

from mx3lib import observe, physics, run  # noqa: E402

sys.path.insert(0, str(HERE.parents[2] / "mx3-tune" / "scripts"))
try:
    from tune import measure  # reuse one definition of every metric
except ImportError:  # standalone checkout
    measure = None


@dataclass
class Point:
    cells: int
    cell_size: float
    value: float | None
    status: str
    duration_s: float
    error: str = ""


@dataclass
class Result:
    metric: str
    converged: bool = False
    recommended_cell: float | None = None
    points: list = field(default_factory=list)
    note: str = ""
    exchange_length: float | None = None
    elapsed_s: float = 0.0


def rewrite(template: str, grid_param: str, cell_param: str,
            n: int, cell: float) -> str:
    """Set both declarations. Neither is optional: changing one alone changes
    the physical size of the sample, which is a different simulation."""
    out = template
    for name, value, fmt in ((grid_param, n, "{:d}"), (cell_param, cell, "{:.6g}")):
        pat = re.compile(rf"^(\s*{re.escape(name)}\s*:?=\s*)([^/\n]+)", re.MULTILINE)
        out, count = pat.subn(lambda m: m.group(1) + fmt.format(value), out)
        if count == 0:
            raise ValueError(
                f"the template has no line declaring {name!r}. It needs both:\n"
                f"    {grid_param} := 64\n    {cell_param} := 4e-9\n"
                f"and must use them in SetGridSize/SetCellSize.\n"
                f"NOTE: mx3 identifiers are case-insensitive, so 'cell' collides "
                f"with the built-in Cell() and will not compile. Use dx, N, dcell."
            )
    return out


def read_declared(template: str, name: str) -> float:
    m = re.search(rf"^\s*{re.escape(name)}\s*:?=\s*([0-9.eE+-]+)", template, re.MULTILINE)
    if not m:
        raise ValueError(f"cannot read the declared value of {name!r}")
    return float(m.group(1))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("template", type=Path)
    ap.add_argument("--grid-param", default="N")
    ap.add_argument("--cell-param", default="dx")
    ap.add_argument("--metric", required=True,
                    help="what to watch, e.g. 'loop:coercivity', 'last:mz', "
                         "'velocity:ext_dwpos'")
    ap.add_argument("--cells", nargs="+", type=int, default=[32, 64, 128],
                    help="grid sizes to try, coarse to fine")
    ap.add_argument("--tolerance", type=float, default=0.02,
                    help="relative agreement that counts as converged")
    ap.add_argument("--Ms", type=float, help="for the exchange-length check")
    ap.add_argument("--A", type=float, help="for the exchange-length check")
    ap.add_argument("--run-timeout", type=float, default=900)
    ap.add_argument("--workdir", type=Path, default=Path("converge_runs"))
    ap.add_argument("--json", type=Path)
    args = ap.parse_args()

    if not args.template.is_file():
        print(f"no such template: {args.template}", file=sys.stderr)
        return 2
    if measure is None:
        print("cannot import the shared metric definitions (mx3-tune/scripts/tune.py)",
              file=sys.stderr)
        return 2
    ok, why = run.available()
    if not ok:
        print(f"ENV: {why}", file=sys.stderr)
        return 2

    template = args.template.read_text(encoding="utf-8")
    try:
        n0 = read_declared(template, args.grid_param)
        c0 = read_declared(template, args.cell_param)
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 2

    extent = n0 * c0          # the physical size we must preserve
    args.workdir.mkdir(parents=True, exist_ok=True)
    started = time.time()

    print(f"Sample is {extent*1e9:.1f} nm across; holding that fixed.")
    if args.Ms and args.A:
        lex = physics.exchange_length(args.A, args.Ms)
        print(f"Exchange length is {lex*1e9:.2f} nm - cells above that cannot "
              f"resolve a wall.")
    print(f"Watching {args.metric}.\n")

    points: list[Point] = []
    for n in sorted(args.cells):
        cell = extent / n
        script = args.workdir / f"{args.template.stem}_n{n}.mx3"
        script.write_text(rewrite(template, args.grid_param, args.cell_param, n, cell),
                          encoding="utf-8")

        res = run.run_one(script, timeout=args.run_timeout)
        value, err = None, res.error
        if res.ok and res.output:
            try:
                value = measure(res.output, args.metric)
            except ValueError as exc:
                err = str(exc)
        points.append(Point(n, cell, value, res.status, res.duration_s, err))

        shown = "failed" if value is None else f"{value:.6g}"
        flag = ""
        if args.Ms and args.A:
            lex = physics.exchange_length(args.A, args.Ms)
            if cell > lex:
                flag = "   (cell exceeds exchange length)"
        print(f"  {n:>4} cells   cell = {cell*1e9:6.2f} nm   "
              f"{args.metric} = {shown:<14} {res.duration_s:5.1f}s{flag}")
        if err and value is None:
            print(f"       {err}")

    usable = [(p.cell_size, p.value) for p in points if p.value is not None]
    result = Result(metric=args.metric, points=[asdict(p) for p in points],
                    elapsed_s=time.time() - started)
    if args.Ms and args.A:
        result.exchange_length = physics.exchange_length(args.A, args.Ms)

    print()
    if len(usable) < 3:
        result.note = (f"only {len(usable)} of {len(points)} runs produced a value; "
                       f"at least three are needed to see a trend")
        print(f"INCONCLUSIVE: {result.note}")
    else:
        conv = observe.convergence(usable, tolerance=args.tolerance)
        result.converged = conv.converged
        result.recommended_cell = conv.converged_at
        result.note = conv.note
        if conv.converged:
            print(f"CONVERGED at {conv.converged_at*1e9:.2f} nm and finer.")
            print(f"  {conv.note}")
            coarse = max(p for p, _ in usable)
            fine = min(p for p, _ in usable)
            vc = dict(usable)[coarse]
            vf = dict(usable)[fine]
            if vf and abs(vf) > 0:
                print(f"  For scale: the coarsest run ({coarse*1e9:.2f} nm) differs "
                      f"from the finest by {abs(vc-vf)/abs(vf):.1%}.")
        else:
            print("NOT CONVERGED.")
            print(f"  {conv.note}")

    if result.exchange_length:
        over = [p for p in points if p.cell_size > result.exchange_length]
        if over:
            print(f"  Note: {len(over)} of these cells exceed the exchange length "
                  f"({result.exchange_length*1e9:.2f} nm) and cannot resolve a "
                  f"domain wall regardless of what the trend looks like.")

    if args.json:
        args.json.write_text(json.dumps(asdict(result), indent=2), encoding="utf-8")
        print(f"  full report: {args.json}")

    return 0 if result.converged else 1


if __name__ == "__main__":
    sys.exit(main())
