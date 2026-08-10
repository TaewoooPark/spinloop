# Where mumax3 differs from the paper you are reading

A paper describes physics. A simulator implements a convention. When a
reproduction misses and the numerics look fine, the gap is usually here.

Everything below was verified against mumax3 3.12 (Metal build), not recalled.

## Boundary conditions — the one that cost 13 degrees

**`OpenBC` defaults to `false`, and it changes DMI edge physics.**

Continuum treatments of DMI derive a free-spin boundary condition: the
magnetisation tilts at a free surface with `dTheta/dn = D/(2A)`. Papers state
this as part of the model and rarely name a simulator setting for it.

mumax3's default is a closed boundary. Measured on the 1D standard problem
(arXiv:1803.11174, A = 13 pJ/m, D = 3 mJ/m², Ku = 0.4 MJ/m³), converged at
0.125 nm cells:

| | edge tilt |
|---|---|
| `OpenBC = false` (default) | 28.0° |
| `OpenBC = true` | 40.5° |
| analytic, `sin(Theta) = Delta/xi` | 41.1° |

Twelve degrees, from one boolean that the paper had no reason to mention.
The false answer was *stable and mesh-converged* — refining 8× moved it by less
than 3°, so convergence testing alone would not have caught it.

**Rule:** if the paper's model has a free surface with DMI, set
`OpenBC = true`. If it uses periodic boundaries, use `SetPBC` instead and do
not set `OpenBC`.

## Demagnetisation — often excluded in analytic work

Many DMI and domain-wall papers derive results from an energy functional with
no magnetostatic term, then simulate the same reduced model. If you include
demag and they did not, you are simulating a different problem.

```go
EnableDemag = false
```

Look for: "we neglect the demagnetising field", "in the effective anisotropy
approximation", or an energy functional (usually the paper's Eq. 1–5) with no
`-mu0/2 M.Hd` term. When a paper folds demag into an effective anisotropy
`Keff = Ku - mu0 Ms^2 / 2`, it has already accounted for it — including demag
as well double-counts.

## DMI: which one, and which sign

| paper says | mumax3 |
|---|---|
| interfacial, Néel, C_nv | `Dind` |
| bulk, Bloch, T symmetry, B20 | `Dbulk` |
| D2d, anti-skyrmion | not directly supported |

The sign sets the chirality. A paper reporting a left-handed wall reproduced as
right-handed usually means a sign flip, not a magnitude error — the tilt
magnitude will be right and only the direction wrong. Check that before
touching `|D|`.

## Anisotropy: bare Ku or effective Keff

Papers use both, often without saying which.

- `Ku1` in mumax3 is the **bare** uniaxial constant. mumax3 computes the
  demagnetising field separately.
- If the paper quotes `Keff` (shape anisotropy already subtracted) and you
  also have `EnableDemag = true`, you have subtracted it twice.

A quick test: `mu0*Ms^2/2` for the paper's Ms. If `Ku_paper` is close to that
value, the paper is likely quoting `Keff` for a film that is nearly balanced,
and the distinction matters.

`lib/mx3 physics --Ms ... --A ... --Ku1 ...` prints both.

## Units in the wild

`scripts/extract_paper.py` converts these, but check what it chose.

| quantity | commonly printed as | SI |
|---|---|---|
| exchange A | pJ/m, erg/cm | J/m |
| DMI D | mJ/m², erg/cm² | J/m² |
| Ms | MA/m, kA/m, emu/cm³, or as µ₀Ms in T | A/m |
| Ku | MJ/m³, kJ/m³, erg/cm³ | J/m³ |
| field | Oe, kOe, mT, or µ₀H in T | T |

The traps: `emu/cm³ → A/m` is ×10³, and a paper quoting "Ms = 1.0 T" means
µ₀Ms, so `Ms = 1.0/mu0 = 796 kA/m`, not 1.0.

## Thermal simulations do not reproduce CUDA trajectories

This port uses Philox where cuRAND used XORWOW. A seed reproduces on Metal but
will not reproduce a published CUDA run sample by sample. Compare statistics —
mean, distribution, switching rate — not individual trajectories, and say so.

## Discretisation of a cropped cell

`Crop(m, 0, 1, ...)` reports the cell **centre**, half a cell inside the
physical boundary. For an edge quantity decaying over a length `Delta`, the
reported value is low by roughly `exp(-cell/(2*Delta))` in `tan(Theta/2)`.

At 0.125 nm cells with `Delta = 5.7` nm this is 0.14°; at 2 nm cells it is over
2°, which is easily mistaken for a physics disagreement.

## Things mumax3 will not tell you

None of these produce a warning:

- `OpenBC` left at its default when the model needs free boundaries
- demag on when the paper's model excludes it
- `Ku1` fed an effective anisotropy that already includes shape
- a region parameter set on a region that was never defined (applies to
  nothing, silently — see mx3-authoring's `pitfalls.md`)

Which is why the reproduction protocol checks numerics *before* concluding
anything about the physics.
