---
name: mx3-plan
description: >-
  Decide what is worth simulating before writing any script. From the material
  parameters a researcher already has, works out which magnetic states the
  material can support, where the boundaries between them lie, what mesh is
  required, and what a run will cost. Use for "what should I simulate", "will
  this material host skyrmions", "is this film in-plane or perpendicular",
  "what cell size do I need", "will a vortex form in this dot", "how long will
  this take", "where do I start".
---

# What is worth simulating

Every other skill assumes the user already knows what to run. Often they do
not: they have a sample, or a set of parameters, and the question is what can
be seen at all.

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/mx3-plan/scripts/plan.py \
  --Ms 1050e3 --A 19e-12 --Ku 1.2e6 --D 1.5e-3 --thickness 1e-9 --width 200e-9
```

Everything is closed form and instant. Nothing is simulated — the point is to
decide what to spend simulation time on.

## What it tells you

**Which states exist.** Perpendicular or in-plane (from the sign of
`Keff = Ku1 - mu0*Ms^2/2`), single domain or vortex (from width against the
exchange length), skyrmions or a labyrinth (from `D/Dc`).

**Where the boundaries are.** Exchange length, domain wall width, critical
DMI. These are the numbers that decide whether an experiment is even in the
right regime.

**What mesh.** Cell size must be below the exchange length, and below the wall
parameter when there is anisotropy. The report gives both the requirement and
a comfortable value, then the cell count and what that costs.

**What to run first**, in order — usually: compare candidate ground states by
energy, then the observable of interest, then a convergence check.

## Reading the output

The important line is often `effective anisotropy`:

```
effective anisotropy +5.073e+05 J/m3   (PERPENDICULAR easy axis)
```

A negative `Keff` on a material the user believes is perpendicular means one
of two things, and both matter: either the film really is in-plane, or `Ku`
was quoted as an *effective* value that already has shape anisotropy removed.
Feeding that to `Ku1` with demag on subtracts it twice. `mx3-authoring`'s
`R-KEFF` rule catches this later, but it is cheaper to catch it here.

`D/Dc` sets the skyrmion question:

| D/Dc | What to expect |
|---|---|
| < 0.5 | DMI too weak — skyrmions will not hold |
| 0.5 – 1 | the usual window for isolated skyrmions |
| ≥ 1 | no uniform state; a labyrinth, not isolated skyrmions |

Confinement changes this: a hard frame or a small element can hold a skyrmion
below the free-film threshold. Treat `D/Dc` as the free-film answer.

## Honesty about the estimates

Every formula here describes an **extended film**. A 100 nm dot has different
demagnetising factors and will differ by several percent or more. Say that
when reporting — these choose what to simulate, they are not results.

## Related skills

- **mx3-authoring** — write the script this plan calls for
- **mx3-check** — the same closed forms, used to judge a finished result
- **mx3-lab** — if the goal is to mirror a measurement rather than explore
