#!/usr/bin/env python3
"""What is worth simulating for this material?

    plan.py --Ms 800e3 --A 13e-12 --thickness 20e-9 --width 200e-9
    plan.py --Ms 1050e3 --A 19e-12 --Ku 1.2e6 --D 1.5e-3 --thickness 1e-9

Takes the material parameters a researcher already has and answers the question
that comes before any script: which magnetic states this material can support,
where the boundaries between them sit, what mesh is required, and roughly what
a run will cost on this machine.

Everything is closed form, from lib/mx3lib/physics.py. Nothing is simulated,
so it returns instantly - the point is to decide what to spend simulation time
on, not to spend it.

Every estimate carries its assumption. Most of these formulas describe an
extended film; a 100 nm dot is not one, and the report says so rather than
quoting three digits it has not earned.
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

from mx3lib import physics, run  # noqa: E402

MU0 = physics.MU0


def bullets(title, items):
    if not items:
        return
    print(f"\n{title}")
    for it in items:
        print(f"  - {it}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--Ms", type=float, required=True, help="A/m")
    ap.add_argument("--A", type=float, required=True, help="J/m")
    ap.add_argument("--Ku", type=float, default=0.0, help="J/m3, bare uniaxial")
    ap.add_argument("--D", type=float, default=0.0, help="J/m2, interfacial DMI")
    ap.add_argument("--alpha", type=float, default=0.02)
    ap.add_argument("--thickness", type=float, help="m")
    ap.add_argument("--width", type=float, help="m, lateral size of the element")
    ap.add_argument("--json", type=Path)
    args = ap.parse_args()

    Ms, A, Ku, D, t, w = (args.Ms, args.A, args.Ku, args.D,
                          args.thickness, args.width)

    lex = physics.exchange_length(A, Ms)
    shape = MU0 * Ms * Ms / 2
    keff = Ku - shape if Ku else -shape

    print("Material")
    print(f"  Ms {Ms:.4g} A/m   A {A:.4g} J/m" + (f"   Ku {Ku:.4g} J/m3" if Ku else "")
          + (f"   D {D:.4g} J/m2" if D else ""))
    print(f"  exchange length      {lex*1e9:.2f} nm")
    print(f"  shape anisotropy     {shape:.4g} J/m3   (mu0*Ms^2/2)")
    if Ku:
        print(f"  effective anisotropy {keff:+.4g} J/m3   "
              f"({'PERPENDICULAR' if keff > 0 else 'IN-PLANE'} easy axis)")

    # ---- what states can exist -------------------------------------------
    states, why = [], []
    if Ku and keff > 0:
        delta = physics.wall_parameter(A, keff)
        width_wall = physics.wall_width(A, keff)
        print(f"  domain wall width    {width_wall*1e9:.2f} nm  (pi*sqrt(A/Keff))")
        states.append("uniform out-of-plane (single domain)")
        states.append("up/down stripe domains, if the element is much wider than the wall")
        if D:
            dc = physics.critical_dmi(A, keff)
            ratio = D / dc
            print(f"  critical DMI         {dc*1e3:.3f} mJ/m2   "
                  f"(you have D/Dc = {ratio:.2f})")
            if ratio >= 1:
                states.append("SPIRAL / labyrinth - D exceeds Dc, no uniform state")
                why.append("D/Dc >= 1: a uniform film is unstable. Skyrmions will "
                           "not be isolated; expect a labyrinth.")
            elif ratio > 0.5:
                states.append("isolated Neel skyrmions (D/Dc in the usual window)")
                why.append(f"D/Dc = {ratio:.2f} is in the range where isolated "
                           f"skyrmions are normally metastable.")
            else:
                states.append("skyrmions unlikely - D is well below Dc")
                why.append(f"D/Dc = {ratio:.2f}: DMI is too weak to hold a "
                           f"skyrmion against the anisotropy.")
        else:
            why.append("no DMI given, so no chiral textures - walls will be Bloch.")
    else:
        states.append("in-plane magnetised")
        if w:
            # vortex is favoured once the element is large compared with lex
            if w > 20 * lex:
                states.append("vortex (element is large compared with the exchange length)")
                why.append(f"width/l_ex = {w/lex:.0f}: large enough that flux "
                           f"closure usually beats a single domain.")
            elif w > 8 * lex:
                states.append("vortex or single domain - near the crossover")
                why.append(f"width/l_ex = {w/lex:.0f}: close to the single-domain "
                           f"to vortex boundary; both may be metastable.")
            else:
                states.append("single domain (element is small)")
                why.append(f"width/l_ex = {w/lex:.0f}: too small to support a "
                           f"vortex core.")
        if Ku:
            why.append("Keff < 0: the shape anisotropy wins, so the moment lies "
                       "in plane despite Ku. Feeding an ALREADY-EFFECTIVE Ku to "
                       "Ku1 with demag on is the usual cause - check the source.")

    bullets("States this material can support", states)
    bullets("Why", why)

    # ---- what mesh -------------------------------------------------------
    finest = lex
    if Ku and keff > 0:
        finest = min(finest, physics.wall_parameter(A, keff))
    if D and Ku and keff > 0:
        finest = min(finest, lex)
    cell = finest / 2
    print(f"\nMesh")
    print(f"  cell size            <= {finest*1e9:.2f} nm required, "
          f"{cell*1e9:.2f} nm comfortable")
    if w and t:
        nx = int(math.ceil(w / cell))
        nz = max(1, int(round(t / cell)))
        cells = nx * nx * nz
        print(f"  for {w*1e9:.0f} x {w*1e9:.0f} x {t*1e9:.0f} nm at "
              f"{cell*1e9:.2f} nm: {nx} x {nx} x {nz} = {cells:,} cells")
        print(f"  {run.sizing_advice(nx, nx, nz)}")

    # ---- what to run first ----------------------------------------------
    todo = []
    if Ku and keff > 0:
        todo.append("relax from Uniform(0,0,1) and from RandomMag(), compare "
                    "E_total - if they differ, the ground state is not what you assumed")
        if D:
            todo.append("relax from NeelSkyrmion(1,-1) and check "
                        "ext_topologicalcharge stays near +/-1 (mx3-run)")
            todo.append("sweep D and watch the skyrmion diameter (mx3-tune)")
        todo.append("hysteresis loop along z: coercivity and squareness (mx3-run loop)")
    else:
        todo.append("relax from Uniform(1,0,0) and from Vortex(1,1), compare "
                    "E_total - that decides which state your element prefers")
        todo.append("in-plane hysteresis loop: coercivity vs element size")
    todo.append("confirm the answer does not move under mesh refinement (mx3-check)")
    bullets("Worth running, in this order", todo)

    print("\nAssumptions")
    print("  These are closed-form estimates for an EXTENDED FILM. A patterned")
    print("  element has different demagnetising factors and will differ by")
    print("  several percent or more - use them to choose what to simulate, not")
    print("  as answers.")

    if args.json:
        args.json.write_text(json.dumps({
            "exchange_length": lex, "shape_anisotropy": shape,
            "k_eff": keff if Ku else None,
            "wall_width": physics.wall_width(A, keff) if (Ku and keff > 0) else None,
            "critical_dmi": physics.critical_dmi(A, keff) if (D and Ku and keff > 0) else None,
            "recommended_cell": cell, "states": states,
        }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
