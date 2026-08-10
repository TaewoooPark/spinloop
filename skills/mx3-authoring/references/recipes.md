# Canonical script shapes

Six patterns that cover most of what people write. Each names what to change
and what to check. Working starting points live in `assets/templates/`; all
four pass `vet.sh` and `lint_mx3.py`.

The universal skeleton:

```
mesh (counts, then lengths) -> geometry/regions -> materials -> initial state
   -> what to record -> run -> save
```

Ordering matters: `m` cannot be assigned before the mesh exists (`R-MESH-ORDER`).

---

## 1. Static ground state

**Use when** you want the relaxed configuration and nothing else.
**Template** `minimal.mx3`

```go
SetGridSize(128, 128, 1)
SetCellSize(3.9e-9, 3.9e-9, 3.0e-9)
Msat = 800e3
Aex  = 13e-12
alpha = 1                 // high damping: only the endpoint matters
m = RandomMag()
Relax()
Save(m)
```

**Change** mesh, material, initial state.
**Check** `Relax()` finds *a* minimum, not necessarily the global one. Start
from several initial states (`Uniform`, `Vortex`, `RandomMag`) and compare
`E_total` if the ground state matters.

`Minimize()` is the faster alternative for a pure energy minimum;
`Relax()` follows damped dynamics and is more robust from a bad start.

---

## 2. Field-driven dynamics — standard problem 4

**Use when** you want a time-resolved trajectory.
**Template** `dynamics.mx3` (self-asserting against upstream reference values)

```go
alpha = 0.02              // physical damping now, not 1
m = Uniform(1, 0.1, 0)
Relax()                   // ground state first

TableAutoSave(10e-12)     // sample far finer than the feature you are resolving
AutoSave(m, 100e-12)
B_ext = vector(-24.6e-3, 4.3e-3, 0)
Run(1e-9)
```

**Change** field, damping, run time.
**Check** the sampling period resolves the precession you care about — a 36 ps
period sampled every 100 ps is aliased. And that `Run()` is long enough to
reach the regime of interest.

---

## 3. Hysteresis loop

**Use when** you want M(H).
**Template** `hysteresis.mx3`

```go
alpha = 1
TableAdd(B_ext)
for B := 50.0; B >= -50.0; B -= 2.0 {
	B_ext = vector(B*1e-3, 0, 0)
	Relax()
	TableSave()
}
// then the ascending branch, written out again
```

Both branches are written out in full: **mx3 has no user-defined functions**,
so there is nothing to factor the loop body into.

**Change** field range, step, direction.
**Check** the step brackets the switching field. A loop with vertical sides may
just mean the step jumped over the reversal — refine near the transition.
Quasi-static means `Relax()` at each point, so `alpha` here is a numerical
convenience, not physics.

---

## 4. Regions and multilayers

**Use when** the sample is not one material.

```go
SetGridSize(128, 128, 4)
SetCellSize(4e-9, 4e-9, 1e-9)

DefRegion(1, Layers(0, 2))          // bottom two layers
DefRegion(2, Layers(2, 4))          // top two

Msat.SetRegion(1, 800e3)
Msat.SetRegion(2, 1400e3)
Aex.SetRegion(1, 13e-12)
Aex.SetRegion(2, 30e-12)

ext_InterExchange(1, 2, 5e-12)      // coupling across the interface
```

**Check** every region you assign to was actually defined — assigning to an
undefined-but-in-range region is silent and applies to nothing (see
`pitfalls.md` §12). Region indices are 0–255; region 0 is everything
unassigned. Run `smoke_run.sh` on region scripts.

Geometry composes with boolean methods:

```go
SetGeom(Circle(200e-9).Sub(Circle(80e-9)))     // annulus
SetGeom(Rect(400e-9, 100e-9).RotZ(pi/4))       // rotated bar
```

Full method list under `Shape.*` in `api-index.md`.

---

## 5. DMI and skyrmions

**Use when** the system has interfacial DMI.

```go
SetGridSize(128, 128, 1)
SetCellSize(2e-9, 2e-9, 1e-9)       // DMI textures need a fine mesh

Msat  = 580e3
Aex   = 15e-12
Dind  = 3e-3                        // J/m2, interfacial
Ku1   = 0.8e6
anisU = vector(0, 0, 1)
alpha = 0.3

m = NeelSkyrmion(1, -1)             // charge, core polarisation

TableAdd(ext_topologicalcharge)
Relax()
Save(m)
```

**Check** the mesh resolves the skyrmion, not just the exchange length — the
skyrmion diameter must span many cells. Track `ext_topologicalcharge`: if it
drifts from its integer value the texture is under-resolved or has collapsed.
Use `Dbulk` instead of `Dind` for bulk DMI.

---

## 6. Parameter sweep — one file per point

**Use when** you are scanning a parameter.
**Template** `sweep.mx3`

Because there are no functions, the idiom is file generation plus batching —
and batching is where the fork's 2.53× lives:

```bash
for K in 0.3 0.4 0.5 0.6 0.7; do
  sed "s/^Ku1_value := .*/Ku1_value := ${K}e6/" sweep.mx3 > "sweep_${K}.mx3"
done
mumax3 -j 3 sweep_*.mx3        # 3 queued inputs per GPU
```

Always guard an unattended batch, or one bad parameter hangs the queue:

```go
RelaxWallClockTime = 300
```

**Check** the swept range brackets the transition. Record the swept value in
the table so the outputs are self-describing.

Note `smoke_run.sh` returns INCONCLUSIVE (exit 3) on loop-heavy scripts:
shrinking the grid does not reduce the iteration count. That is expected —
rely on vet and lint for those.

---

## Choosing a solver

| | |
|---|---|
| `SetSolver(1)` | Euler — fixed step only, needs `FixDt` |
| `SetSolver(2)` | Heun |
| `SetSolver(3)` | Bogacki-Shampine |
| `SetSolver(4)` | Runge-Kutta 4/5 |
| `SetSolver(5)` | Dormand-Prince — the default choice for dynamics |
| `SetSolver(6)` | Fehlberg |

`DemagExtrapolation` applies to 4/5/6 only and fails closed elsewhere.
For finite `Temp`, a fixed step (`FixDt`) is usually required.

## Self-checking scripts

When a reference value exists, assert it. The engine's own tests do:

```go
TOL := 1e-5
ExpectV("m relaxed", m.Average(), vector(0.9669684, 0.1252732, 0), TOL)
```

The assertion documents what the script is supposed to produce, and turns a
silent regression into a failure. Delete assertions when you change the
parameters they describe — do not loosen the tolerance until they pass.
