# Scripts that compile and are still wrong

`mumax3 -vet` proves a script parses, resolves every name, and has the right
argument counts. It proves nothing about meaning. This is the catalogue of what
gets through — each entry paired with the lint rule that catches it, where one
exists.

The severity order that matters: a script that **dies** is cheap. A script that
**completes and is wrong** is expensive, because it produces a figure.

---

## 1. Float where a cell count belongs — `R-GRID-INT`

```go
SetGridSize(128e-9, 32, 1)
```

Verified against the real binary: `-vet` prints `OK`. At runtime `128e-9` is
truncated to int `0`, the mesh has zero cells, and the engine panics during
world construction.

**Why it slips through:** the script layer's `typeConv` converts float to int
silently; there is no narrowing check.

**Tell:** any `e-` or decimal point inside `SetGridSize` or the first three
arguments of `SetMesh`.

---

## 2. Cell coarser than the exchange length — `R-LEX`

```go
Msat = 800e3            // l_ex = 5.7 nm
Aex  = 13e-12
SetCellSize(20e-9, 20e-9, 20e-9)
```

Nothing complains. The run converges. Domain walls are simply not resolved, so
wall widths, coercive fields, and switching times are all wrong — in a way that
looks like a physical result rather than a numerical artefact.

**Rule of thumb:** cell ≤ $\sqrt{2A/\mu_0 M_s^2}$. See `units-and-scales.md`
for the per-material table.

**The honest exception:** a deliberate convergence study sweeps cell size
precisely to show the effect. Say so in the header; the linter will still warn
and that is correct.

---

## 3. Msat in the wrong convention — `R-MSAT`

```go
Msat = 800           // meant 800 emu/cm3, wrote A/m
```

Three orders of magnitude low. Demag becomes negligible, the sample behaves
like a paramagnet with exchange, and nothing errors. `800 emu/cm³` is `800e3`
A/m.

Equally: `Msat = 1.0` intending 1 tesla. µ₀Ms in tesla divided by µ₀ is
`796e3`.

---

## 4. Relax() and Minimize() silently disable thermal noise — `R-RELAX-TEMP`

```go
Temp = 300
Relax()          // this relaxation is at T = 0, not 300 K
```

`engine/minimizer.go` sets `relaxing = true // disable temperature noise`. The
relaxation is deterministic regardless of `Temp`.

**What you probably wanted:** relax at zero temperature first, then set `Temp`
and use `Run()` for the finite-temperature dynamics.

```go
Relax()
Temp = 300
ThermSeed(1)
Run(10e-9)
```

---

## 5. A run that saves nothing — `R-NO-OUTPUT`

```go
Relax()
Run(1e-9)
// ... and nothing else
```

Compiles, runs, consumes GPU time, writes an empty output directory. Add at
minimum:

```go
TableAutoSave(10e-12)     // scalars over time
AutoSave(m, 100e-12)      // full field snapshots
Save(m)                   // final state
```

`TableAdd(...)` before the run to choose the columns.

---

## 6. Setting state before the mesh exists — `R-MESH-ORDER`

```go
m = Uniform(1, 0, 0)      // no mesh yet
SetGridSize(128, 32, 1)
```

`m` needs the mesh to allocate against. Order is always: grid → cell size →
geometry/regions → material parameters → initial state → run.

---

## 7. alpha = 0 with a relaxer — `R-ALPHA`

```go
alpha = 0
Relax()
```

Undamped precession conserves energy, so the relaxation has nothing to descend.
`Relax()` cannot converge and either runs to its wall-clock guard or spins.

Use `alpha = 1` for fast relaxation, then set the physical `alpha` before the
dynamics run.

---

## 8. Fork knobs that are silently inert — `R-FORK-SPEC`, `R-FORK-DEMAG`

```go
FixDt = 1e-13
SpeculativeStep = true        // no-op: closes itself under FixDt
```

```go
SetSolver(2)
DemagExtrapolation = true     // no-op: fails closed on solver 2
```

Neither errors. Neither speeds anything up. You conclude the knob does not
help, when in fact it never ran. See `ultrafast-deltas.md` for the full
closure conditions.

---

## 9. SpeculativeStep changes the trajectory

Not a mistake, but a fact that must reach the header. `MaxErr` is still
enforced, but rejection lands one step late, so the step sequence differs from
the exact controller and the trajectory **diverges at the ~1% level after a few
thousand steps**.

Fine for a survey. Not fine for a published trajectory unless A/B'd against a
default run. `R-FORK-ACC` requires you to say so in the header.

---

## 10. Thermal seeds do not reproduce CUDA

```go
ThermSeed(42)
```

Reproducible on Metal. Will **not** reproduce a CUDA run's sample-by-sample
trajectory — this port uses Philox where cuRAND used XORWOW. Statistical
behaviour was validated; the sample sequence was not preserved.

---

## 11. Case-insensitivity hides typos in review

```go
SetGridsize(128, 32, 1)      // compiles - identical to SetGridSize
setcellsize(4e-9, 4e-9, 4e-9)
```

Both correct. It means a human reviewer cannot use casing as a signal, and it
means "the name looks slightly off" is not evidence of a bug. Check against
`api-index.md` instead.

---

## 12. Region mistakes: one is silent, one is fatal, neither is caught by vet

Setting a region that was never defined is **not** an error — verified:

```go
DefRegion(1, Circle(100e-9))
Msat.SetRegion(7, 500e3)      // vet OK, runs fine, applies to zero cells
```

The assignment lands on an empty region and simply does nothing. No warning,
no failure, and your material parameter is silently absent from the model.
This one gets through vet, lint and smoke run alike; only reading the script
catches it.

Exceeding the region range **is** fatal, and only at runtime:

```go
Msat.SetRegion(300, 5e5)
// vet: OK
// runtime: panic: index out of range [300] with length 256
```

Region indices run 0–255 (`NREGION = 256`); region 0 is everything not
otherwise assigned. `smoke_run.sh` catches the fatal case.

---

## 13. A geometry that clips everything away

```go
SetGridSize(64, 64, 1)
SetCellSize(4e-9, 4e-9, 4e-9)     // 256 nm across
SetGeom(Circle(500e-9))           // larger than the box
```

Not an error — but combined with a `Transl` or a mis-scaled shape it is easy to
end up with an empty geometry and a run that does nothing. `smoke_run.sh`
catches the empty case.

---

## 14. Below 128² nothing you do in the script makes it faster — `R-SIZE`

A fixed 172–187 µs per-evaluation overhead dominates at small meshes on the
measured M4. Tuning the solver or enabling knobs will not move it. Batch the
sweep instead:

```bash
mumax3 -j 3 sweep_*.mx3
```

---

## Checklist before handing a script over

- [ ] `vet.sh` passes
- [ ] `lint_mx3.py` has no ERROR, and every WARN is explained in the header
- [ ] cell size ≤ exchange length, or the deviation is justified
- [ ] `Msat`, `Aex` in SI, from a stated source
- [ ] something is saved
- [ ] if `Temp` is used, no relaxer is silently discarding it
- [ ] if a fork knob is on, the header says it is an approximation
- [ ] the `Unverified` line names what the physicist must still check
