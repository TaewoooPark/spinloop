#!/usr/bin/env python3
"""Write the .mx3 for a measurement protocol, not just for a physics question.

    protocol.py major  --Ms 800e3 --A 13e-12 --size 200e-9 --thick 20e-9 --Bmax 60
    protocol.py minor  ... --Breverse 25
    protocol.py astroid ... --angles 0 15 30 45 60 75 90
    protocol.py fmr    ... --Bbias 200

An experimentalist does not run "a simulation"; they run a measurement. A VSM
major loop, a minor loop that turns round before saturation, coercivity against
field angle, an FMR ringdown at a bias field. Each is a specific field
sequence, and getting the sequence wrong makes the comparison with the bench
meaningless however good the physics is.

This emits the sequence. Material parameters are yours; the protocol is the
part that is easy to get subtly wrong.

Fields are given in mT and angles in degrees, because that is what the
instrument reads. Everything is converted to SI in the script.
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
for cand in (HERE.parents[3] / "lib", HERE.parents[2] / "lib"):
    if (cand / "mx3lib").is_dir():
        sys.path.insert(0, str(cand))
        break

from mx3lib import physics  # noqa: E402


def header(what: str, a, extra: str = "") -> str:
    lex = physics.exchange_length(a.A, a.Ms)
    cell = a.cell if a.cell else lex / 2
    return f"""/*
  {what}
  Units      : SI throughout (m, A/m, J/m, T, s)
  Mesh       : cells {cell*1e9:.2f} nm, below the {lex*1e9:.2f} nm exchange length
  Materials  : Msat {a.Ms:g} A/m, Aex {a.A:g} J/m, alpha {a.alpha:g}
  Protocol   : {extra}
  Unverified : material parameters are the user's; the geometry is a plain
               {'disc' if a.shape == 'disc' else 'rectangle'} and may not match the real
               patterned element (edge roughness, taper, oxide edge).
               alpha here is a relaxation convenience for a quasi-static loop,
               not the physical damping.
*/
"""


def preamble(a) -> str:
    lex = physics.exchange_length(a.A, a.Ms)
    cell = a.cell if a.cell else lex / 2
    nx = int(math.ceil(a.size / cell))
    nz = max(1, int(round(a.thick / cell)))
    geom = (f"SetGeom(Circle({a.size:g}))" if a.shape == "disc"
            else f"SetGeom(Rect({a.size:g}, {a.size * a.aspect:g}))")
    ny = int(math.ceil(a.size * (1 if a.shape == "disc" else a.aspect) / cell))
    ku = f"\nKu1   = {a.Ku:g}\nanisU = vector(0, 0, 1)" if a.Ku else ""
    dmi = f"\nDind  = {a.D:g}" if a.D else ""
    return f"""
SetGridSize({nx}, {ny}, {nz})
SetCellSize({cell:g}, {cell:g}, {a.thick / nz:g})
{geom}

Msat  = {a.Ms:g}
Aex   = {a.A:g}{ku}{dmi}
alpha = {a.alpha:g}

TableAdd(B_ext)
TableAdd(E_total)
RelaxWallClockTime = {a.guard:g}
"""


def sweep(axis: str, b_from: float, b_to: float, step: float, indent="") -> str:
    """A quasi-static field sweep in mT along a named axis expression."""
    sign = "-=" if b_to < b_from else "+="
    cmp_ = ">=" if b_to < b_from else "<="
    return (f"{indent}for B := {b_from:g}; B {cmp_} {b_to:g}; B {sign} {abs(step):g} {{\n"
            f"{indent}\tB_ext = {axis}\n"
            f"{indent}\tRelax()\n"
            f"{indent}\tTableSave()\n"
            f"{indent}}}\n")


AXIS = {"x": "vector(B*1e-3, 0, 0)", "y": "vector(0, B*1e-3, 0)",
        "z": "vector(0, 0, B*1e-3)"}


def major(a) -> str:
    ax = AXIS[a.axis]
    return (header(f"Major hysteresis loop along {a.axis}, as a VSM or MOKE would measure it.",
                   a, f"saturate at {a.Bmax:g} mT, sweep down and back in {a.step:g} mT steps")
            + preamble(a)
            + f"\nm = Uniform({1 if a.axis=='x' else 0}, {1 if a.axis=='y' else 0}, "
              f"{1 if a.axis=='z' else 0})\n"
              f"B_ext = {ax.replace('B*1e-3', f'{a.Bmax*1e-3:g}')}\nRelax()\n\n"
            + "// descending branch\n" + sweep(ax, a.Bmax, -a.Bmax, a.step)
            + "\n// ascending branch\n" + sweep(ax, -a.Bmax, a.Bmax, a.step)
            + "\nSave(m)\n")


def minor(a) -> str:
    ax = AXIS[a.axis]
    if a.Breverse is None:
        raise SystemExit("minor loop needs --Breverse, the field to turn round at")
    return (header(f"Minor loop along {a.axis}: reverse before saturation.", a,
                   f"saturate at +{a.Bmax:g} mT, down to -{a.Breverse:g} mT, back up")
            + preamble(a)
            + f"\nm = Uniform({1 if a.axis=='x' else 0}, {1 if a.axis=='y' else 0}, "
              f"{1 if a.axis=='z' else 0})\n"
              f"B_ext = {ax.replace('B*1e-3', f'{a.Bmax*1e-3:g}')}\nRelax()\n\n"
            + "// down to the reversal field only - the loop does NOT close\n"
            + sweep(ax, a.Bmax, -a.Breverse, a.step)
            + "\n// back up\n" + sweep(ax, -a.Breverse, a.Bmax, a.step)
            + "\nSave(m)\n")


def astroid(a) -> str:
    """Coercivity against field angle - a far stronger shape test than Hc alone."""
    out = [header("Switching field vs field angle (astroid).", a,
                  f"one loop per angle: {', '.join(str(x) for x in a.angles)} deg")]
    out.append(preamble(a))
    out.append("\n// One angle per run: generate one file per angle and batch them\n"
               "// with `mumax3 -j 3 astroid_*.mx3`. This file is the template;\n"
               "// the angle is the only line that changes.\n")
    out.append(f"angle_deg := {a.angles[0]:g}\n")
    out.append("theta := angle_deg * pi / 180\n")
    out.append("\nm = Uniform(cos(theta), sin(theta), 0)\n")
    ax = "vector(B*1e-3*cos(theta), B*1e-3*sin(theta), 0)"
    out.append(f"B_ext = vector({a.Bmax*1e-3:g}*cos(theta), {a.Bmax*1e-3:g}*sin(theta), 0)\nRelax()\n\n")
    out.append(sweep(ax, a.Bmax, -a.Bmax, a.step))
    out.append("\nSave(m)\n")
    return "".join(out)


def fmr(a) -> str:
    return (header("FMR ringdown at a bias field, as a VNA-FMR or BLS would see it.", a,
                   f"bias {a.Bbias:g} mT, small out-of-plane step, free decay recorded")
            + preamble(a)
            + f"""
alpha = {a.alpha_dyn:g}          // physical damping now, not the relaxation value

m = Uniform(1, 0, 0)
B_ext = vector({a.Bbias*1e-3:g}, 0, 0)
Relax()

// a short transverse step rings every mode, then record the free decay
B_ext = vector({a.Bbias*1e-3:g}, 0, {a.Bpulse*1e-3:g})
Run(20e-12)
B_ext = vector({a.Bbias*1e-3:g}, 0, 0)
TableAutoSave({a.dt:g})
Run({a.record:g})
""")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("protocol", choices=["major", "minor", "astroid", "fmr"])
    ap.add_argument("--Ms", type=float, required=True)
    ap.add_argument("--A", type=float, required=True)
    ap.add_argument("--Ku", type=float, default=0.0)
    ap.add_argument("--D", type=float, default=0.0)
    ap.add_argument("--size", type=float, required=True, help="lateral size, m")
    ap.add_argument("--thick", type=float, required=True, help="m")
    ap.add_argument("--shape", default="disc", choices=["disc", "rect"])
    ap.add_argument("--aspect", type=float, default=0.5, help="rect only")
    ap.add_argument("--cell", type=float, help="m; default is half the exchange length")
    ap.add_argument("--axis", default="x", choices=["x", "y", "z"])
    ap.add_argument("--alpha", type=float, default=1.0, help="relaxation damping")
    ap.add_argument("--alpha-dyn", type=float, default=0.01, dest="alpha_dyn")
    ap.add_argument("--Bmax", type=float, default=60.0, help="mT")
    ap.add_argument("--step", type=float, default=2.0, help="mT")
    ap.add_argument("--Breverse", type=float, help="mT, minor loop turning point")
    ap.add_argument("--angles", type=float, nargs="+", default=[0, 30, 45, 60, 90])
    ap.add_argument("--Bbias", type=float, default=200.0, help="mT")
    ap.add_argument("--Bpulse", type=float, default=10.0, help="mT")
    ap.add_argument("--dt", type=float, default=4e-12, help="table sampling, s")
    ap.add_argument("--record", type=float, default=4e-9, help="s")
    ap.add_argument("--guard", type=float, default=60.0, help="RelaxWallClockTime, s")
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()

    text = {"major": major, "minor": minor, "astroid": astroid, "fmr": fmr}[args.protocol](args)
    if args.out:
        args.out.write_text(text, encoding="utf-8")
        print(f"wrote {args.out}")
        print("Now gate it:  mx3-authoring/scripts/vet.sh " + str(args.out))
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
