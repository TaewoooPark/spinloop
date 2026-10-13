# Numerics of mumax3

Use this chapter before trusting any number from a run, when a result looks odd, and when choosing the mesh, solver, relaxation method, boundaries and output sampling. It is the "how a simulation measures it" chapter for the whole library.
Engine statements refer to upstream mumax3 3.10–3.12 (`engine/*.go`, `cuda/*.cu`). Fork-only knobs (`SpeculativeStep`, `DemagExtrapolation`, `MinimizeOnGPU`) are in `mx3-authoring/references/ultrafast-deltas.md`.

## 1. The finite-difference model
**Grid and geometry**
- Nx×Ny×Nz cuboid cells with one unit vector m per cell.
- Geometry is set per cell: a staircase, or fill fractions with `EdgeSmooth` (§5).

**Exchange**
- 6-neighbour, second-order stencil.
- A missing neighbour gives the free condition ∂m/∂n = 0, or the DMI condition (§5).
- Between regions the coupling is the harmonic mean of `Aex`. Override it with `ext_InterExchange` or `ext_ScaleExchange`; for DMI use `ext_InterDind` or `ext_ScaleDind`.

**Demagnetisation**
- FFT convolution with the exact kernel of uniformly magnetised cuboids. The kernel is integrated numerically (`DemagAccuracy`, default 6) and cached on disk.
- Open directions are zero-padded to 2N. Prefer grid sizes with small prime factors (powers of 2 are fastest).

**Error scaling**
- Smooth textures: O(Δx²).
- Curved or oblique edges (staircase): O(Δx), first order. This often dominates in patterned elements.
- Wall energies and depinning fields at Δx ≳ Δ: not polynomial at all, because of lattice pinning (§9).

**Cost**
- The stiffest exchange mode, B_max ≈ (2A/Ms)·4d/Δx² (d = number of finely resolved dimensions), limits explicit steps to dt ~ 1/(γB_max).
- Halving Δx in 2D therefore costs ≈ 4× cells × 4× steps = 16×; in 3D ≈ 32×.
- Typical dt for 2–5 nm metallic cells is 0.01–1 ps.

**Single layer (Nz = 1).** m is assumed uniform through the thickness; the demagnetising field is then exact. This is adequate when t ≲ l_ex, Δ (02-scales.md §13).

## 2. float32 precision on the GPU
- All field and state arithmetic is single precision (ε ≈ 1.2×10⁻⁷). m is renormalised every step.
- Table values are written as float32 (~7 significant digits); `t` is written as float64.
- Reductions (`m.Average()`, `Sum`, `Dot`, `E_*`) accumulate in float32 with atomic adds across thread blocks. Their order is not fixed, so the last digits can differ between identical runs. Max-reductions (`maxTorque` and the solver's error estimate) are order-independent.

**Noise floor**
- Total energies carry relative noise of order 10⁻⁷–10⁻⁶, growing with cell count.
  - `Relax()` phase 1 deliberately stops at this floor.
  - Energy differences below ~10⁻⁶·|E_total| are not meaningful.
- m components resolve ~10⁻⁷, so deviations such as 1 − m_z below that are invisible.
- `MaxErr` below ~10⁻⁷ adds cost without accuracy; per-step rounding is already that large.

**Reproducibility**
- Same GPU, driver, build and input: `Run()` trajectories are normally identical. The step loop uses only order-independent reductions, except post-step hooks (`ext_centerWall`) and `Relax()`'s energy/torque tests.
- Across GPU models, CUDA versions or the Metal port, expect agreement within tolerance, not bit-for-bit.
- Near a bifurcation (switching threshold, chaotic or thermal dynamics), last-bit differences grow into different outcomes.
  - Compare statistics, not trajectories.
  - An outcome that flips between repeated runs means you are at a threshold. Report a probability.
- Thermal noise: `ThermSeed(n)` fixes the sequence per backend. Metal and CUDA sequences differ (`pitfalls.md` §10).

## 3. Time integration
| `SetSolver` | Method | Order (embedded) | Use |
|---|---|---|---|
| 1 | Euler | 1 | Reference only. Without `FixDt`, dt = `MaxErr`/max torque, and steps are never rejected |
| 2 | Heun | 2 (1) | Robust low order; with `FixDt` for thermal runs |
| 3 | Bogacki–Shampine RK23 | 3 (2), FSAL | Used internally by `Relax()`; adaptive thermal runs |
| 4 | RK4 | 4 | Classical |
| 5 | Dormand–Prince RK45 | 5 (4), FSAL | **Default**; deterministic dynamics |
| 6 | Fehlberg RK45 | 5 (4) | Alternative |
| −1 | Backward Euler | 1, implicit | Requires `FixDt`; large steps at low accuracy |

**Adaptive step control** (`engine/run.go`)
- err = max over cells of |Δm| between the embedded solutions. This is an absolute, dimensionless error per step (column `LastErr`).
- A step is accepted if err < `MaxErr` (default 10⁻⁵).
- Next dt = dt·`Headroom`(0.8)·(MaxErr/err)^(1/p), with the exponent 1/(p+1) after a rejection. The change is clamped to [0.5, 2]× per step.
- `MinDt` and `MaxDt` clamp dt (default 0 = no limit). A step at dt ≤ `MinDt` is accepted **whatever its error**, so `MinDt` can silently admit inaccurate steps.
- `FixDt` ≠ 0 accepts every step. `LastErr` still reports the estimate: watch it.

**Interaction with output and excitations**
- Autosaves (`TableAutoSave`, `AutoSave`) fire at the first step after each multiple of the period: steps are not shortened to hit them (only the end of `Run()` is hit exactly, `engine/autosave.go`, `run.go`). Rows are therefore unevenly spaced in time; use the recorded `t`. Dense output does not change the dynamics.
- **Short pulses can be skipped.** In a quiet state dt doubles each step with no upper bound, so a ps-scale pulse written as a function of `t` can be stepped over.
  - Set `MaxDt` ≲ (pulse width or rise time)/10 while the excitation is on.
- Health columns: `TableAdd(dt)`, `TableAdd(LastErr)`, `TableAdd(NEval)`.
- For phase-sensitive long runs (many gyration or spin-wave periods), confirm that `MaxErr = 1e-6` gives the same answer.

**Thermal runs (`Temp` > 0)**
- B_therm = η·√(2αk_BT/(γ·Ms·V_cell·Δt)) (T), where η ~ N(0,1) per component, per cell and per step.
- The noise is held constant within a step and rescaled after a rejected step (Leliaert et al. 2017). Adaptive steps (`FixDt` = 0) have been allowed at T > 0 since mumax3 3.10, with any solver; the engine cites that paper when they are used (`engine/temperature.go`).
- `FixDt` with Heun is the conservative alternative. Either way, check that halving dt or `MaxErr` leaves the statistics unchanged.
- Noise grows as 1/√(V_cell·Δt): small cells force small steps.
- Results depend on cell size (UV cutoff): ⟨m⟩ and the effective Ms, K and A renormalise with Δx. Keep Δx fixed within a study and state it (08-thermal.md).
- Use ensembles over `ThermSeed`; error bars come from the seed-to-seed spread. `Relax()` and `Minimize()` ignore `Temp`.

## 4. Relax() versus Minimize() versus Run()
| | `Relax()` | `Minimize()` | `Run(T)`, `RunWhile(cond)`, `Steps(n)` |
|---|---|---|---|
| Equation | dm/dτ = −m×(m×B_eff), RK23; precession off, `alpha` **not used** | steepest descent with Barzilai–Borwein steps (Exl et al. 2014) on the same torque | full LLG: precession, `alpha`, `Temp`, `J`, time-dependent `B_ext` |
| `Temp` | ignored | ignored | used |
| Time `t` | not advanced; autosave never fires | not advanced | advances; autosaves fire |
| Stopping | Phase 1: step while E_total decreases (checked every 3 steps). Phase 2, default (`RelaxTorqueThreshold` = −1): divide `MaxErr` by √2 down to 10⁻⁹, stepping while the mean squared torque decreases. If the threshold is > 0: step until `maxTorque` < threshold, then refine | max \|Δm\| over the last `MinimizerSamples` (10) iterations < `MinimizerStop` (10⁻⁶) | elapsed time or condition |
| Returns | true if converged; `RelaxWallClockTime` guard | same; `MinimizeWallClockTime` | — |
| Strength | robust far from equilibrium | fastest near a minimum | physical path, thermal, driven states |
| Weakness | slow tail; may stop in a flat valley or on a saddle | can stall from random or high-energy states | you decide when it is equilibrated |

`Relax()` restores the solver, `MaxErr`, `FixDt` and `DoPrecess` afterwards. Because `alpha` is unused, `alpha = 1` before `Relax()` is harmless but unnecessary.

**Saddles and metastable states**
- All three methods descend locally and never cross barriers. The endpoint is the basin of the initial state, not necessarily the ground state.
- Exactly symmetric states have zero torque and stay on saddles. Examples: m exactly antiparallel to `B_ext`; uniform m along a hard axis; mirror-symmetric initial guesses.
- To break the symmetry, tilt the field by ~0.5–1°, or perturb: `m = CurrentMag().Add(0.01, RandomMagSeed(1))`.
- Precession-free descent does not follow the physical path. Low-α dynamics can overshoot into another basin during switching or nucleation.
  - Use `Run()` with the physical `alpha` to find which state a dynamic process reaches.
  - Use the relaxers only for quasi-static endpoints.
- Ground-state search: start from several states (`Uniform`, `Vortex`, `RandomMagSeed(n)`, `NeelSkyrmion`, `Helical`) and compare E_total.
- Verify equilibrium: `Print(maxTorque)` (T) should be ≪ the relevant fields. A short `Run()` at the physical `alpha` should not move ⟨m⟩.
- An alternative relaxation that keeps a dynamic path: `alpha = 0.5–1`, then `RunWhile(maxTorque > 1e-4)`, with the threshold scaled to your fields.

## 5. Boundary conditions
**Open (default)**
- A finite sample in vacuum: no images, free exchange edges.
- **DMI edges:** with `Dind` or `Dbulk` ≠ 0 and `OpenBC = false` (default), the missing neighbour is extrapolated from the chiral condition ∂m/∂n = (D/2A)(ẑ×n)×m (Rohart & Thiaville 2013; Mulkers et al. 2017).
  - The resulting edge canting is physical, with a tilt ≈ DΔ/(2A) rad (≈0.25 rad for D = 1.5 mJ/m², Δ = 5 nm, A = 15 pJ/m).
  - `OpenBC = true` drops the missing-neighbour terms entirely. That is not the physical edge, so use it only deliberately.
- `Aex` must be > 0 wherever D ≠ 0, because the edge extrapolation divides by A. `Dind` and `Dbulk` together are a fatal error.

**Periodic (`SetPBC(Px, Py, Pz)`, or `SetMesh`)**
- Exchange wraps around. The demagnetising kernel is an explicit, truncated image sum out to ~P box lengths on each side. Larger P costs kernel set-up time, not run time.
- Check convergence in P. For a PBC film in `Uniform(0,0,1)`, `B_demag` should approach −µ0Ms. Increase P until it stops changing at your tolerance.
- Residual end-charge fields of the finite image array fall off roughly as 1/P.
- **Commensurability:** helices, stripes and skyrmion lattices must fit the box. Otherwise the period strains and energies shift. Scan the box length and take the minimum energy density.
- **Self-interaction:** an isolated wall or skyrmion interacts with its images. Dipolar tails are long-range, so make the box much larger than the object.

**Staircase edges and `EdgeSmooth`**
- Curved or oblique edges discretise as stairs. This creates spurious pinning sites, shifts edge-mode frequencies and raises switching fields, at O(Δx) (Donahue & McMichael 2007).
- `EdgeSmooth = n` (0 = staircase, ~8 = very smooth) samples n³ points per cell to set the fill fraction `geom` ∈ [0, 1].
  - `geom` weights Ms in the demagnetising convolution and in averages. **Exchange still sees the staircase**, so only the magnetostatic error is reduced.
  - Set it before `SetGeom`.
- Where possible, align edges with the grid: rotate the field rather than the sample.

## 6. Moving frame and finite windows
**`ext_centerWall(c)`**
- After each step, if |⟨m_c⟩| > 4/Nx (the wall is ~2 cells off centre), `Shift(±1)` moves the content by one cell.
- `ShiftMagL` and `ShiftMagR` fill the inserted cells; they are auto-set from the left edge if unset. `ShiftM`, `ShiftGeom` and `ShiftRegions` choose what moves.
- Variants: `ext_centerWallInLayer` and `ext_centerWallInRegion`; `ext_centerBubble` for bubbles and skyrmions.

**Position and velocity**
- `TotalShift` and `ext_dwpos` are quantised to one cell.
- Refine with x_wall ≈ `ext_dwpos` + s·⟨m_c⟩·Lx/2, where `ext_dwpos` = −`TotalShift` and s is the sign of m_c in the left domain (two-domain approximation).
- `ext_dwspeed` differentiates a staircase and is noisy. Fit x_wall(t) linearly in steady state instead.

**Artefacts**
- In-plane wires: magnetic charges at the window ends push on the wall. Compensate with `ext_rmSurfaceCharge(region, mxLeft, mxRight)`.
- With the defaults (`ShiftGeom`, `ShiftRegions` true) `Shift` moves geometry and regions together with m, and newly exposed cells are taken from the shapes at their lab position, so notches, grains and roughness stay fixed in the lab while the window moves. Set them false only if the landscape should travel with the window.

**Finite windows**
- Spin waves reflect at edges, creating standing-wave patterns.
  - Absorb them with a damping ramp over ≥ 1–2 wavelengths up to α ≈ 0.5–1, built from graded regions.
  - Avoid abrupt α steps, which themselves reflect.
- Edges repel DMI textures. Keep skyrmions several diameters from edges, or use PBC.
- Domain periods larger than the box are suppressed.

## 7. Extracting observables robustly
**Time-domain basics**
- **Transients:** after any change, discard ≥ 3–5 damping times, τ ≈ 1/(α·2πf), shorter for in-plane films (02-scales.md §9). Average only over steady state and over an integer number of periods.
- **Sampling:** `TableAutoSave(Δt_s)`.
  - Nyquist: f_max = 1/(2Δt_s). Fits in the time domain need ≥ 4–10 samples per period.
  - Resolution: Δf = 1/T_window. Sample times are the first steps after each period, not exact multiples: interpolate onto a uniform grid (using the `t` column) before an FFT, or use `FixDt` dividing the period.
- **Spatial averages hide modes:** antisymmetric modes cancel in ⟨m⟩. Record local signals with `TableAdd(m.Region(n))`, `TableAdd(CropRegion(m, n))`, or cropped snapshots such as `AutoSave(CropY(m, j, j+1), Δt_s)`.
  - `m.Region(n)` averages over that region's cells only.
  - `Crop*` averages divide by every cell in the crop, including empty ones (m = 0), which dilutes the value.

**Spectra**
- Subtract the mean (and any drift), apply a Hann window, and zero-pad only to interpolate (padding adds no resolution).
- For an amplitude decay e^(−t/τ), the power spectrum is Lorentzian with HWHM = 1/(2πτ) in Hz.
- **Excitation:** a sinc pulse b₀·sinc(2πf_c(t − t₀)) drives all modes up to f_c roughly evenly.
- **Linearity:** halving b₀ must scale the spectrum linearly without shifting the peaks.

**Dispersion and spatial data**
- **Dispersion:** 2D FFT of m(x, t) along a line. Δk = 2π/L and k_max = π/Δx; sample in time above Nyquist too (Venkat et al. 2013).
- **Quasi-static loops:** `Relax()` writes no autosave rows, so call `TableSave()` after each field step with `TableAdd(B_ext)`. Refine the steps near switching.

**Events, topology and data volume**
- **Events:** interpolate switching times from zero crossings of ⟨m_z⟩; take wall velocities from linear fits of position against time.
- **Topology:**
  - `ext_topologicalcharge` is a finite-difference estimate. `ext_topologicalchargelattice` (Berg–Lüscher) is integer for resolved textures.
  - A non-integer value means under-resolution or a texture touching an edge.
- **Data volume:** an OVF2 binary snapshot is 12 bytes per cell (float32 × 3). Crop, or save sparsely.

## 8. Convergence-testing protocol
1. Fix 1–3 target observables and a tolerance for each. Run the actual protocol once as the baseline.
2. **Cell size:**
   - Halve Δx in the dimensions that resolve the texture, keeping sample sizes exact multiples of Δx.
   - With three levels Q₁, Q₂, Q₃, the observed order is p = log₂((Q₁ − Q₂)/(Q₂ − Q₃)). Expect ≈2 for smooth textures and ≈1 when staircase errors dominate.
   - Richardson estimate: Q∞ ≈ Q₃ + (Q₃ − Q₂)/(2^p − 1).
3. **Window:** double the box, the PBC images P, or the absorbing-layer length.
4. **Time step:** `MaxErr` ÷ 10 (adaptive), or `FixDt` ÷ 2 (fixed or thermal).
5. **Relaxation:** compare `Relax()` with `Minimize()` endpoints (E_total, `maxTorque`) and with other initial states.
6. **Thermal:** use ≥ 5–10 seeds, and test the cell-size dependence explicitly.
7. Report the levels, the changes and the chosen settings in the script header.

## 9. Common numerical artefacts
| Symptom | Likely cause | Remedy |
|---|---|---|
| Wall or vortex moves in steps, sticks below a finite drive that shrinks with Δx | lattice pinning, Δx ≳ Δ | refine (02-scales.md §13) |
| One-cell checkerboard or oscillation of m | Δx ≫ l_ex or Δ; A too small (unit error) | refine; check units (01 §7) |
| dt collapses, "time step too small" | huge fields (units), tiny cells with `Temp`, Bloch points | check `B_*` columns, units, mesh |
| NaN | `Aex` = 0 where D ≠ 0; `Msat` = 0 in magnetic cells; bad custom field | fix parameters per region |
| Switching exactly at the instability field, perfectly square loop | perfect symmetry, no symmetry breaking | tilt the field 0.5–1°, add noise |
| Coercivity changes with field step or relax tolerance | step jumps over reversal; not equilibrated | finer steps near switching; check `maxTorque` |
| Extra edge peaks; frequencies depend on Δx in curved samples | staircase | `EdgeSmooth`, finer cells |
| Standing waves in a propagation run | edge reflections | graded absorbing boundary |
| Peaks at wrong or mirrored frequencies | aliasing (Δt_s too long) | sample faster |
| Broad peaks with sidelobes | short record, no taper | longer run; Hann window |
| Helix period ≠ 4πA/D under PBC; texture interacts with itself | incommensurate or too small box | scan or enlarge the box |
| Skyrmion shrinks and its charge jumps 1 → 0 | collapse through an under-resolved core | refine; check the charge before collapse |
| Short pulse has no effect | dt larger than the pulse | `MaxDt` |
| `Relax()` returns at once with an obviously unequilibrated state | saddle or flat valley | perturb; `Minimize()`; check `maxTorque` |
| Identical inputs, last-digit differences / different outcome | float32 reduction order / bifurcation | expected / report statistics (§2) |
| Thermal results depend on Δx | UV cutoff of the noise | expected; fix Δx and report it |

## References
- A. Vansteenkiste et al., "The design and verification of MuMax3", AIP Advances 4, 107133 (2014).
- J. Leliaert, J. Mulkers, "Tomorrow's micromagnetic simulations", J. Appl. Phys. 125, 180901 (2019).
- C. Abert, "Micromagnetics and spintronics: models and numerical methods", Eur. Phys. J. B 92, 120 (2019).
- J. Leliaert et al., "Adaptively time stepping the stochastic Landau–Lifshitz–Gilbert equation at nonzero temperature: implementation and validation in MuMax3", AIP Advances 7, 125010 (2017).
- L. Exl et al., "LaBonte's method revisited: an effective steepest descent method for micromagnetic energy minimization", J. Appl. Phys. 115, 17D118 (2014).
- J. Mulkers, B. Van Waeyenberge, M. V. Milošević, "Effects of spatially engineered Dzyaloshinskii–Moriya interaction in ferromagnetic films", Phys. Rev. B 95, 144401 (2017).
- S. Rohart, A. Thiaville, Phys. Rev. B 88, 184422 (2013): DMI boundary condition and edge canting.
- M. J. Donahue, R. D. McMichael, "Micromagnetics on curved geometries using rectangular cells: error correction and analysis", IEEE Trans. Magn. 43, 2878 (2007).
- J. R. Dormand, P. J. Prince, "A family of embedded Runge–Kutta formulae", J. Comput. Appl. Math. 6, 19 (1980).
- P. Bogacki, L. F. Shampine, "A 3(2) pair of Runge–Kutta formulas", Appl. Math. Lett. 2, 321 (1989).
- E. Hairer, S. P. Nørsett, G. Wanner, *Solving Ordinary Differential Equations I*, Springer (1993).
- B. Berg, M. Lüscher, "Definition and statistical distributions of a topological number in the lattice O(3) σ-model", Nucl. Phys. B 190, 412 (1981).
- G. Venkat et al., "Proposal for a standard micromagnetic problem: spin wave dispersion in a magnonic waveguide", IEEE Trans. Magn. 49, 524 (2013).
- A. Baker et al., "Proposal of a micromagnetic standard problem for ferromagnetic resonance simulations", J. Magn. Magn. Mater. 421, 428 (2017).
- W. H. Press et al., *Numerical Recipes*, 3rd ed., Cambridge University Press (2007): FFT, windowing, Richardson extrapolation.
