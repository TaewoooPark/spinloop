#!/usr/bin/env python3
"""Compare a measured hysteresis loop against a simulated one.

    compare_loop.py measured.csv sim.out --field-unit mT --normalise

Reads a two-column measurement (field, signal) in whatever units the
instrument wrote, normalises both loops, and reports how far apart they are --
in the quantities a magnetist actually compares: coercivity, remanence,
squareness, and the point-by-point difference.

This is the honest half of "match my measurement". Fitting parameters to a
loop is an inverse problem with more than one answer: coercivity in particular
depends on the reversal mechanism, on defects the simulation does not have,
and on the sweep rate. A simulated loop that reproduces Mr/Ms and the shape
but not Hc is the normal outcome, not a failure -- and saying so is more
useful than tuning until the numbers agree for the wrong reason.

Accepted measurement formats: CSV or whitespace-separated text, with or
without a header line. Comment lines starting with #, % or ; are skipped.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

HERE = Path(__file__).resolve()
for cand in (HERE.parents[3] / "lib", HERE.parents[2] / "lib"):
    if (cand / "mx3lib").is_dir():
        sys.path.insert(0, str(cand))
        break

from mx3lib import OutputDir, observe  # noqa: E402

# Everything is converted to tesla internally.
FIELD_UNITS = {
    "T": 1.0,
    "mT": 1e-3,
    "Oe": 1e-4,
    "kOe": 1e-1,
    "A/m": 4e-7 * math.pi,
    "kA/m": 4e-7 * math.pi * 1e3,
}


@dataclass
class LoopComparison:
    measured_coercivity: float | None
    simulated_coercivity: float | None
    coercivity_ratio: float | None
    measured_squareness: float | None
    simulated_squareness: float | None
    rms_difference: float | None
    verdict: str = ""
    notes: list = None


def read_measurement(path: Path, field_col: int, signal_col: int,
                     unit: str) -> tuple[list[float], list[float]]:
    scale = FIELD_UNITS.get(unit)
    if scale is None:
        raise ValueError(f"unknown field unit {unit!r}; known: {', '.join(FIELD_UNITS)}")

    B, sig = [], []
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line[0] in "#%;":
            continue
        parts = [p for p in line.replace(",", " ").split() if p]
        if len(parts) <= max(field_col, signal_col):
            continue
        try:
            b = float(parts[field_col])
            s = float(parts[signal_col])
        except ValueError:
            continue          # header row
        B.append(b * scale)
        sig.append(s)

    if len(B) < 5:
        raise ValueError(
            f"only {len(B)} usable rows in {path}. Expected two numeric columns "
            f"(field, signal); use --field-col/--signal-col if they are elsewhere."
        )
    return B, sig


def normalise(y: list[float]) -> list[float]:
    """Centre and scale to +/-1, so an arbitrary instrument signal (volts,
    degrees of Kerr rotation, emu) can be compared with a reduced magnetisation.

    Uses the mean of the top and bottom deciles as the saturation levels rather
    than the extremes, so one noisy point does not set the scale.
    """
    s = sorted(y)
    k = max(1, len(s) // 10)
    low = sum(s[:k]) / k
    high = sum(s[-k:]) / k
    mid = (high + low) / 2
    half = (high - low) / 2
    if half == 0:
        return [0.0 for _ in y]
    return [(v - mid) / half for v in y]


def branches(B: list[float], y: list[float]) -> dict[str, tuple[list, list]]:
    """Split a loop into its descending and ascending sweeps.

    A hysteresis loop is multivalued in B: at any field below saturation there
    are two moments, one per branch. Sorting the whole loop by field and
    interpolating therefore compares nothing meaningful -- it averages the two
    branches together and reports the loop's own opening as if it were
    disagreement. Branches must be matched by sweep direction.
    """
    out: dict[str, tuple[list, list]] = {}
    for lo, hi in observe._split_branches(B):
        seg_B, seg_y = B[lo:hi], y[lo:hi]
        if len(seg_B) < 3:
            continue
        key = "descending" if seg_B[-1] < seg_B[0] else "ascending"
        # keep the longest sweep of each direction
        if key not in out or len(seg_B) > len(out[key][0]):
            out[key] = (seg_B, seg_y)
    return out


def resample(x: list[float], y: list[float], grid: list[float]) -> list[float]:
    """Linear interpolation of y(x) onto `grid`. Single-valued input only --
    callers pass one branch at a time."""
    pairs = sorted(zip(x, y))
    xs = [p[0] for p in pairs]
    ys = [p[1] for p in pairs]
    out = []
    for g in grid:
        if g <= xs[0]:
            out.append(ys[0])
        elif g >= xs[-1]:
            out.append(ys[-1])
        else:
            lo, hi = 0, len(xs) - 1
            while hi - lo > 1:
                mid = (lo + hi) // 2
                if xs[mid] <= g:
                    lo = mid
                else:
                    hi = mid
            span = xs[hi] - xs[lo]
            t = 0.0 if span == 0 else (g - xs[lo]) / span
            out.append(ys[lo] + t * (ys[hi] - ys[lo]))
    return out


def compare(mB: list[float], mS: list[float],
            sB: list[float], sM: list[float]) -> LoopComparison:
    notes: list[str] = []
    mS_n = normalise(mS)
    sM_n = normalise(sM)

    meas = observe.hysteresis(mB, mS_n)
    sim = observe.hysteresis(sB, sM_n)
    if meas.note:
        notes.append(f"measured: {meas.note}")
    if sim.note:
        notes.append(f"simulated: {sim.note}")

    ratio = None
    if meas.coercivity and sim.coercivity:
        ratio = sim.coercivity / meas.coercivity

    # Branch-by-branch difference over the field range both loops cover.
    lo = max(min(mB), min(sB))
    hi = min(max(mB), max(sB))
    rms = None
    if hi > lo:
        m_br, s_br = branches(mB, mS_n), branches(sB, sM_n)
        shared = sorted(set(m_br) & set(s_br))
        if shared:
            grid = [lo + (hi - lo) * i / 60 for i in range(61)]
            per: list[float] = []
            for key in shared:
                a = resample(*m_br[key], grid)
                b = resample(*s_br[key], grid)
                per.append(math.sqrt(
                    sum((p - q) ** 2 for p, q in zip(a, b)) / len(grid)))
            rms = sum(per) / len(per)
            notes.append(
                f"compared {', '.join(shared)} branch"
                f"{'es' if len(shared) > 1 else ''} separately"
            )
            if len(shared) == 1:
                notes.append(
                    "only one sweep direction is common to both; a full loop "
                    "on each side would compare more"
                )
        else:
            notes.append(
                "could not identify matching sweep directions in the two loops; "
                "shape was not compared"
            )
    else:
        notes.append(
            f"no overlapping field range (measured {min(mB):.3g}..{max(mB):.3g} T, "
            f"simulated {min(sB):.3g}..{max(sB):.3g} T) - sweep the simulation "
            f"over the measured range before comparing"
        )

    verdict = _verdict(ratio, meas, sim, rms)
    return LoopComparison(
        measured_coercivity=meas.coercivity,
        simulated_coercivity=sim.coercivity,
        coercivity_ratio=ratio,
        measured_squareness=meas.squareness,
        simulated_squareness=sim.squareness,
        rms_difference=rms,
        verdict=verdict,
        notes=notes,
    )


def _verdict(ratio, meas, sim, rms) -> str:
    if ratio is None:
        return ("Cannot compare coercivity: one of the loops never crosses zero. "
                "Widen the field range.")
    shape_ok = (rms is not None and rms < 0.15)
    if 0.8 <= ratio <= 1.25 and shape_ok:
        return "Coercivity and shape both agree within tolerance."
    if shape_ok:
        return (
            f"The shape matches but the simulated coercivity is {ratio:.2f}x the "
            f"measured one. This is the usual outcome: a defect-free simulated "
            f"element reverses coherently and overestimates Hc, often by several "
            f"times. Matching Mr/Ms and the loop shape is the meaningful "
            f"agreement; forcing Hc to match by tuning Ku or Ms will give you "
            f"parameters that are wrong for every other observable."
        )
    if 0.8 <= ratio <= 1.25:
        return ("Coercivity agrees but the loop shapes differ - the reversal "
                "mechanism in the simulation is probably not the one in the sample "
                "(check geometry, edge roughness, and whether the field is along "
                "the same axis).")
    return ("Neither coercivity nor shape agrees. Check first that the field axis "
            "and units match, then the sample geometry, before adjusting material "
            "parameters.")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("measured", type=Path)
    ap.add_argument("simulated", type=Path, help="mumax3 output directory")
    ap.add_argument("--field-unit", default="mT", choices=sorted(FIELD_UNITS))
    ap.add_argument("--field-col", type=int, default=0)
    ap.add_argument("--signal-col", type=int, default=1)
    ap.add_argument("--sim-field", default="B_extx")
    ap.add_argument("--sim-moment", default="mx")
    ap.add_argument("--json", type=Path)
    ap.add_argument("--plot", type=Path, help="overlay both loops here (needs matplotlib)")
    args = ap.parse_args()

    try:
        mB, mS = read_measurement(args.measured, args.field_col,
                                  args.signal_col, args.field_unit)
    except (ValueError, OSError) as exc:
        print(exc, file=sys.stderr)
        return 2

    try:
        out = OutputDir(args.simulated)
    except NotADirectoryError as exc:
        print(exc, file=sys.stderr)
        return 2
    table = out.table
    if table is None:
        print(f"{args.simulated} has no table.txt", file=sys.stderr)
        return 2
    if not table.has(args.sim_field):
        print(f"the simulation did not record {args.sim_field!r}; add "
              f"TableAdd(B_ext) to the script. Columns: {table.names}",
              file=sys.stderr)
        return 2

    res = compare(mB, mS, table.column(args.sim_field), table.column(args.sim_moment))

    def mt(v):
        return "n/a" if v is None else f"{v*1e3:.3g} mT"

    print(f"                  measured      simulated")
    print(f"  coercivity      {mt(res.measured_coercivity):<13} {mt(res.simulated_coercivity)}")
    print(f"  squareness      {res.measured_squareness or float('nan'):<13.3f} "
          f"{res.simulated_squareness or float('nan'):.3f}")
    if res.rms_difference is not None:
        print(f"  branch RMS      {res.rms_difference:.3f}  (0 = identical, "
              f"normalised units)")
    print()
    print(res.verdict)
    for n in res.notes or []:
        print(f"  - {n}")

    if args.plot:
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            fig, ax = plt.subplots(figsize=(6, 4.5))
            ax.plot([b * 1e3 for b in mB], normalise(mS), "o-", ms=3,
                    label="measured", alpha=0.8)
            ax.plot([b * 1e3 for b in table.column(args.sim_field)],
                    normalise(table.column(args.sim_moment)), "s-", ms=3,
                    label="simulated", alpha=0.8)
            ax.set_xlabel("B (mT)")
            ax.set_ylabel("normalised moment")
            ax.legend()
            ax.grid(alpha=0.3)
            fig.tight_layout()
            fig.savefig(args.plot, dpi=140)
            print(f"\n  overlay: {args.plot}")
        except ImportError:
            print("\n  (matplotlib not installed; skipped the overlay)")

    if args.json:
        args.json.write_text(json.dumps(asdict(res), indent=2), encoding="utf-8")

    return 0


if __name__ == "__main__":
    sys.exit(main())
