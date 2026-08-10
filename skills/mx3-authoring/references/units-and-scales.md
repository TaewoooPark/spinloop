# Units and scales

mumax3 takes **bare SI**. There are no unit suffixes, no nm, no emu. Every
number is metres, amperes per metre, joules per metre, tesla, seconds. Nothing
in the language will stop you writing the wrong one.

## The table

| Quantity | Unit | Typical value | Written as |
|---|---|---|---|
| `SetCellSize` | m | 4 nm | `4e-9` |
| `SetGridSize` | **count** (int) | 128 cells | `128` |
| `Msat` | A/m | permalloy | `800e3` |
| `Aex` | J/m | permalloy | `13e-12` |
| `alpha` | — | dynamics / relaxation | `0.02` / `1` |
| `Ku1`, `Ku2` | J/m³ | Co PMA | `0.5e6` |
| `Kc1`..`Kc3` | J/m³ | cubic | `48e3` |
| `Dind`, `Dbulk` | J/m² | interfacial DMI | `1.5e-3` |
| `B_ext` | T | 10 mT | `vector(0,0,10e-3)` |
| `J` | A/m² | current density | `vector(1e12,0,0)` |
| `Temp` | K | room temperature | `300` |
| `Run`, `FixDt`, `MaxDt` | s | 1 ns | `1e-9` |
| `Pol` | — | polarisation | `0.5` |
| `xi` | — | non-adiabaticity | `0.1` |
| `anisU`, `anisC1` | unit vector | out of plane | `vector(0,0,1)` |

## Cell counts are counts

The single most dangerous conversion error, because **vet accepts it**:

```go
SetGridSize(128e-9, 32, 1)     // vet: OK.  Runtime: 0 cells, panic.
```

mx3 converts float to int silently. `128e-9` becomes `0`. The length belongs in
`SetCellSize`; the count belongs in `SetGridSize`.

```go
SetGridSize(128, 32, 1)                       // counts
SetCellSize(500e-9/128, 125e-9/32, 3e-9)      // metres
```

Dividing a physical extent by the cell count, as above, is the idiomatic way to
keep both readable and consistent.

## Msat: A/m, not emu/cm³, not tesla

Three conventions circulate in the literature. mumax3 wants A/m.

| Source form | Convert | Example |
|---|---|---|
| emu/cm³ (cgs) | × 10³ | 800 emu/cm³ → `800e3` |
| µ₀Ms in tesla | ÷ µ₀ = ÷ 1.2566e-6 | 1.0 T → `796e3` |
| kA/m | × 10³ | 800 kA/m → `800e3` |

Common materials:

| Material | Msat (A/m) | Aex (J/m) | notes |
|---|---|---|---|
| Permalloy (Ni₈₀Fe₂₀) | `800e3` | `13e-12` | the default test material |
| Cobalt (hcp) | `1400e3` | `30e-12` | `Ku1 = 0.5e6`, `anisU = (0,0,1)` |
| Iron (bcc) | `1700e3` | `21e-12` | cubic anisotropy |
| CoFeB | `1050e3` | `19e-12` | PMA when thin |
| YIG | `140e3` | `3.65e-12` | low damping |

These are starting points from the literature, not values for your sample.
Put the real ones in, and record the source in the header.

## Exchange length — the number that sets your mesh

$$l_{ex} = \sqrt{\frac{2 A_{ex}}{\mu_0 M_s^2}}$$

A cell coarser than $l_{ex}$ cannot resolve a domain wall. The simulation still
runs, still converges, still produces a plausible picture — and the physics is
wrong. Nothing in mumax3 warns you.

| Material | l_ex |
|---|---|
| Permalloy (800e3, 13e-12) | **5.7 nm** |
| Cobalt (1400e3, 30e-12) | 4.9 nm |
| Iron (1700e3, 21e-12) | 3.4 nm |
| CoFeB (1050e3, 19e-12) | 5.2 nm |
| YIG (140e3, 3.65e-12) | 17.2 nm |

Rule of thumb: **cell ≤ l_ex**. `lint_mx3.py` computes this from your own
`Msat` and `Aex` and reports `R-LEX` — WARN above `l_ex`, ERROR above `2·l_ex`.

For strong perpendicular anisotropy, the relevant scale is instead the Bloch
parameter $\sqrt{A/K_u}$, which can be smaller; check both.

The out-of-plane cell may legitimately exceed l_ex when a thin film is modelled
as a single layer. The linter judges only the in-plane cells for that reason.

## Standard problem 4 as a calibration

The canonical reference, useful for checking your setup against a known answer:

```go
SetGridSize(128, 32, 1)
SetCellSize(500e-9/128, 125e-9/32, 3e-9)   // 3.91 x 3.91 x 3.0 nm
Msat  = 800e3
Aex   = 13e-12
alpha = 0.02
```

Cell 3.91 nm against l_ex 5.7 nm — resolved, with margin. After `Relax()` the
average magnetisation is `(0.9669684, 0.1252732, 0)` to 1e-5; the engine's own
test asserts exactly that.

## Time scales

| Process | Order |
|---|---|
| Precession period at 1 T | ~36 ps |
| Domain wall transit, 100 nm at 100 m/s | ~1 ns |
| FMR ringdown, alpha = 0.01 | ~10 ns |
| Thermal switching | µs–ms (usually out of reach) |

`Run(1e-9)` is a nanosecond. Adaptive stepping means wall-clock cost is not
proportional to simulated time — a fast-relaxing system covers 1 ns cheaply, a
precessing one does not.

## Fields

`B_ext` is tesla. Converting from the field units used in papers:

| Source | Convert | Example |
|---|---|---|
| oersted (Oe) | × 1e-4 | 100 Oe → `10e-3` T |
| A/m | × µ₀ | 79577 A/m → `0.1` T |
| mT | × 1e-3 | 25 mT → `25e-3` T |

## Sanity ranges the linter enforces

| Parameter | Plausible | Rule |
|---|---|---|
| `Msat` | 1e3 .. 1e7 A/m | `R-MSAT` (WARN) |
| `Aex` | 1e-13 .. 1e-10 J/m | `R-AEX` (WARN) |
| cell size | ≤ 1e-6 m | `R-CELL-SI` |
| grid dims | integer ≥ 1 | `R-GRID-INT` (ERROR) |
| `alpha` | 0 < α ≤ 1 | `R-ALPHA` (WARN) |

These are plausibility bounds, not physics. Exotic systems can fall outside
them — in which case explain it in the header rather than suppressing the
warning.
