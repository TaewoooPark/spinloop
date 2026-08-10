#!/usr/bin/env python3
"""Check a reproduction against the targets taken from the paper.

    verify_repro.py spec.json sim.out

Reports each target as PASS or FAIL with the size of the gap, and -- when
something fails -- which parameters you are permitted to change.

That last part is the point. A reproduction can always be forced to agree by
adjusting the material constants until it does, and the result is worthless:
you have fitted the paper's figure, not reproduced its physics. So the spec
divides parameters in two, and this tool enforces the division:

    stated    the paper gives a value. NEVER adjustable. If the reproduction
              only works with a different Ms than the paper reports, that is a
              finding to report, not a number to change.
    assumed   the paper is silent. Adjustable, because you invented the value
              in the first place -- but every adjustment stays on the record.

Solver settings that are not physics (OpenBC, EnableDemag, cell size, solver
choice) live in `numerics` and are adjustable too, with the same caveat: they
must be justified by what the paper's model actually contains, not by whether
they improve the agreement.

Spec format: see references/reproduction-protocol.md.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
for cand in (HERE.parents[3] / "lib", HERE.parents[2] / "lib"):
    if (cand / "mx3lib").is_dir():
        sys.path.insert(0, str(cand))
        break

from mx3lib import OutputDir  # noqa: E402

sys.path.insert(0, str(HERE.parents[2] / "mx3-tune" / "scripts"))
from tune import measure  # noqa: E402  - one definition of every metric


KIND_NOTE = {
    "analytic": "closed form given in the paper - the strongest kind of target",
    "stated": "a number printed in the paper's text or table",
    "digitised": "read off a figure by hand - carries the reader's own error",
    "qualitative": "not a number; judged by eye",
}


def check(spec: dict, out: OutputDir) -> list[dict]:
    results = []
    for t in spec.get("targets", []):
        name = t.get("name", t.get("metric", "?"))
        kind = t.get("kind", "stated")
        if kind == "qualitative":
            results.append({"name": name, "kind": kind, "status": "MANUAL",
                            "note": t.get("expected_text", "judge by eye")})
            continue

        metric = t.get("metric")
        expected = t.get("expected")
        tol = t.get("tolerance")
        if metric is None or expected is None:
            results.append({"name": name, "kind": kind, "status": "SKIPPED",
                            "note": "target has no metric/expected"})
            continue

        try:
            got = measure(out, metric)
        except ValueError as exc:
            results.append({"name": name, "kind": kind, "status": "ERROR",
                            "note": str(exc)})
            continue

        if tol is None:
            tol = abs(expected) * 0.05 if expected else 0.05
        gap = got - expected
        rel = abs(gap) / abs(expected) if expected else float("inf")
        ok = abs(gap) <= tol
        results.append({
            "name": name, "kind": kind, "metric": metric,
            "expected": expected, "got": got, "gap": gap, "relative": rel,
            "tolerance": tol, "status": "PASS" if ok else "FAIL",
            "source": t.get("source", ""),
        })
    return results


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec", type=Path)
    ap.add_argument("outdir", type=Path)
    ap.add_argument("--json", type=Path)
    args = ap.parse_args()

    if not args.spec.is_file():
        print(f"no such spec: {args.spec}", file=sys.stderr)
        return 2
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    try:
        out = OutputDir(args.outdir)
    except NotADirectoryError as exc:
        print(exc, file=sys.stderr)
        return 2

    paper = spec.get("paper", {})
    title = paper.get("title") or paper.get("id") or args.spec.stem
    print(f"Reproduction check: {title}")
    if paper.get("figure"):
        print(f"  target figure: {paper['figure']}")
    print()

    results = check(spec, out)
    if not results:
        print("The spec declares no targets, so nothing was checked.")
        print("A reproduction without a target is not a reproduction - it is a run.")
        print("Add at least one: a closed form from the paper, a number from its")
        print("text, or points you read off the figure.")
        return 1

    width = max(len(r["name"]) for r in results)
    failed = []
    for r in results:
        if r["status"] in ("MANUAL", "SKIPPED", "ERROR"):
            print(f"  {r['status']:<7} {r['name']:<{width}}  {r.get('note','')}")
            continue
        mark = "PASS   " if r["status"] == "PASS" else "FAIL   "
        print(f"  {mark} {r['name']:<{width}}  "
              f"expected {r['expected']:.6g}, got {r['got']:.6g}  "
              f"({r['relative']:.1%} off)")
        if r["source"]:
            print(f"          {' ' * width}  source: {r['source']}")
        if r["status"] == "FAIL":
            failed.append(r)

    # A target that could not be evaluated is NOT a target that passed.
    unchecked = [r for r in results if r["status"] in ("ERROR", "SKIPPED")]
    manual = [r for r in results if r["status"] == "MANUAL"]

    print()
    if unchecked:
        print(f"{len(unchecked)} target(s) could not be evaluated at all:")
        for r in unchecked:
            print(f"  {r['name']}: {r.get('note','')}")
        print("These are not passes. Fix the script or the spec so they can be")
        print("measured, then re-run - a reproduction is only as good as the")
        print("targets that were actually checked.")
        print()

    if not failed and not unchecked:
        print("All quantitative targets met.")
        if manual:
            print(f"  ({len(manual)} qualitative target(s) still need your eye.)")
        stated = spec.get("stated", {})
        assumed = spec.get("assumed", {})
        print(f"  {len(stated)} parameters taken from the paper, "
              f"{len(assumed)} assumed.")
        if assumed:
            print("  Agreement was reached with these assumptions, which the paper")
            print("  does not state - a different set might agree equally well:")
            for k, v in assumed.items():
                why = v.get("why", "") if isinstance(v, dict) else ""
                val = v.get("value") if isinstance(v, dict) else v
                print(f"    {k} = {val}   {why}")
        return 0

    if not failed and unchecked:
        return 1

    print(f"{len(failed)} target(s) missed. Work through these in order:")
    print()
    print("1. NUMERICS first - these are not the paper's physics, and getting")
    print("   them wrong looks exactly like a physics disagreement:")
    for k, v in (spec.get("numerics") or {}).items():
        print(f"     {k} = {v}")
    print("     Check especially: cell size converged? boundary conditions?")
    print("     demagnetisation included or not, matching the paper's model?")
    print()
    print("2. ASSUMED parameters - you invented these, so they are fair game:")
    assumed = spec.get("assumed", {})
    if assumed:
        for k, v in assumed.items():
            val = v.get("value") if isinstance(v, dict) else v
            print(f"     {k} = {val}")
        print("     Vary ONE at a time with mx3-tune. Two free parameters against")
        print("     one target is under-determined.")
    else:
        print("     (none declared - if the paper really stated everything, the")
        print("      disagreement is in the numerics or in the model itself)")
    print()
    print("3. STATED parameters - DO NOT ADJUST:")
    for k in (spec.get("stated") or {}):
        print(f"     {k}")
    print("     If agreement needs one of these changed, that is the result:")
    print("     report the value that would be required and the discrepancy.")
    print("     Do not change it and call it a reproduction.")

    if args.json:
        args.json.write_text(json.dumps(
            {"targets": results, "spec": str(args.spec), "outdir": str(args.outdir)},
            indent=2), encoding="utf-8")
    return 1


if __name__ == "__main__":
    sys.exit(main())
