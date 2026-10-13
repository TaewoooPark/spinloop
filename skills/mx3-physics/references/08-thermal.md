# Thermal effects: the stochastic field, temperature-dependent parameters, thermal activation, statistics

Use this chapter for finite-temperature mumax3 runs (`Temp`, `ThermSeed`, time step, solver, cell-size dependence of the noise), for scaling Ms, A and K with temperature (Bloch, Callen–Callen), for thermally activated switching (Néel–Brown, Δ, retention, superparamagnetism, blocking, Sharrock), for wall creep, and for getting honest error bars from stochastic ensembles.
Fields are B = µ0H in tesla; k_B = 1.380649e-23 J/K, so k_B·300 K = 4.14e-21 J.

## 1. Thermal fluctuations in mumax3

**Stochastic field (Brown 1963; implemented as in Vansteenkiste et al. 2014).** B_therm is added to B_eff. It is Gaussian, white, and independent per cell, per Cartesian component and per time step:

σ_B = √(2·α·k_B·T / (γ·Ms·V·Δt))  [T, per component]

- α = `alpha`, T = `Temp`, γ = `GammaLL`, Ms = `Msat`, V = cell volume Δx·Δy·Δz, and Δt the time step.
- This is the fluctuation–dissipation result ⟨B_i(t)B_j(t′)⟩ = (2αk_BT/(γMsV))·δ_ij·δ(t − t′). It was verified against the upstream source (`engine/temperature.go`, kernel `settemperature2`).
- Size of the numbers: σ_B ≈ 0.3 T for Py with α = 0.01, a (4 nm)³ cell and Δt = 0.1 ps. It reaches ≈ 9 T for α = 0.1, a (2 nm)³ cell and Δt = 10 fs. These large per-step fields average out over time; they are not physical static fields.

| Implementation fact (upstream mumax3 3.10+) | Consequence |
|---|---|
| Amplitude ∝ √(α·T/(Ms·V·Δt)) per cell; `Temp` and `alpha` are region-wise | `alpha` = 0 gives **no noise** at any `Temp`; an α-ramp absorber is noisier; regions with `Temp` = 0 are noiseless |
| `Relax()` and `Minimize()` disable the noise | relax at T = 0, then set `Temp` and use `Run()` (pitfalls.md §4) |
| Noise is drawn once per accepted step and held fixed through all stages of that step; after a rejected step it is rescaled by √(dt_old/dt_new) | adaptive stepping at T > 0 is allowed (Leliaert et al. 2017); mumax3 cites it when `FixDt` = 0 |
| With `FixDt` set, Δt = `FixDt` fixes the noise amplitude | the conservative, recipe-consistent choice: "for finite `Temp`, a fixed step (`FixDt`) is usually required" (recipes.md) |
| `ThermSeed(n)` seeds the generator; the default seed is fixed (0) | identical scripts give identical noise, so every ensemble member needs its own seed |
| Upstream CUDA warns when the total cell count is odd (normal-variate generation) | use an even cell count at T > 0 |
| Outputs `B_therm`, `E_therm`, `Edens_therm` | E_therm = −V·Σ M·B_therm is a diagnostic, not a thermodynamic energy |
| mumax3-ultrafast: `SpeculativeStep` switches itself off at finite `Temp`; Philox instead of cuRAND | the same seed does **not** reproduce a CUDA trajectory; expect statistical agreement only (pitfalls.md §10) |

**Solver and time step.**
- The conservative choice is `SetSolver(2)` (Heun) with `FixDt`. Heun converges to the Stratonovich interpretation appropriate for the stochastic LLG.
- Choose `FixDt` so that the precession angle per step in the stiffest field is small: γ·B_max·Δt ≲ 0.02 rad, with B_max ≈ 2A/(MsΔx²) + |B_applied + B_anis| (order of).
  - For Py this gives Δt ≈ 10 fs at Δx = 2 nm (B_ex,cell ≈ 8 T) and ≈ 50 fs at 4 nm.
- Adaptive stepping (`FixDt` = 0) is accepted at T > 0 with any solver since mumax3 3.10; the engine then cites Leliaert et al. 2017 for the scheme. It can be much faster, but its error control acts on the deterministic part only, so validate it against a Heun + `FixDt` run for your observable.
- The convergence test is the same either way: halve Δt (or `MaxErr`) and confirm that the statistics do not change within error bars.

**Cell-size dependence.** The noise is uncorrelated between cells, so a mesh with spacing Δx carries thermal spin waves up to k_max = π/Δx.
- Finer meshes therefore show a larger thermal reduction of ⟨|m|⟩, larger neighbour angles, and different effective Ms, A and K. There is no Δx-independent answer: this is an ultraviolet cutoff (Grinstein and Koch 2003).
- The dimensionless control parameter is k_BT/(A·Δx), and the neighbour angle is θ_rms ~ √(k_BT/(AΔx)) (order of). For Py at 300 K, k_BT/(AΔx) = 0.32, 0.16 and 0.06 at Δx = 1, 2 and 5 nm.
  - Keep it ≪ 1, because the finite-difference exchange is a small-angle approximation. Monitor `spinAngle` and `MaxAngle`.
- **Practice**: choose Δx ≈ l_ex, or the scale the physics needs; keep it fixed across a study; and test the key result (a rate, a coercivity) at two Δx.
- **Double counting**: if `Msat`, `Aex` and `Ku1` are already measured values at temperature T, running with `Temp` = T adds the resolved fluctuations a second time. The error grows as Δx shrinks. State the choice in the script header.

**Validity.** Classical spins of fixed length per cell, T well below T_c (roughly T ≲ 0.5–0.7 T_c), and Δx ≳ the lattice constant. Near T_c the longitudinal fluctuations matter; that needs LLB or atomistic models, which are not in mumax3.

## 2. Temperature dependence of material parameters

mumax3 never rescales parameters with `Temp`. Set `Msat`, `Aex`, `Ku1`/`Kc1` and `Dind` to their values at the temperature of interest. Write m(T) = Ms(T)/Ms(0) and τ = T/T_c.

| Quantity | Approximate law | Regime and source |
|---|---|---|
| Ms(T) | m = 1 − b·T^{3/2} (Bloch) | low T, spin-wave regime; b is a material fit |
| Ms(T), full range | m = [1 − s·τ^{3/2} − (1 − s)·τ^{5/2}]^{1/3}, s a fitted shape parameter (≈ 0.1–0.6) | Kuz'min 2005; interpolates between Bloch and critical behaviour |
| Ms near T_c | m ∝ (1 − τ)^β, β ≈ 0.33–0.37 (3D Ising/Heisenberg), mean-field 0.5 | critical region |
| K, single-ion (Callen–Callen) | K_l(T)/K_l(0) = m^{l(l+1)/2}: uniaxial K1 (l = 2) ∝ m³; cubic K1 (l = 4) ∝ m^{10} | low to moderate T |
| K, two-ion (e.g. L1₀ FePt) | ∝ m^{≈2.1} | Okamoto et al. 2002 (measured); Mryasov et al. 2005 (model) |
| A(T) | A ∝ m^n, with n ≈ 2 (mean-field-like scaling) and n ≈ 1.7–1.8 from atomistic calculations (≈ 1.76 for FePt, Atxitia et al. 2010) | approximate; source-dependent |
| A from spin-wave stiffness | A = D_sw·Ms/(2gµ_B), with D_sw in J·m² (ħω = D_sw·k²) | uses neutron or BLS data for D_sw(T) |
| Interface anisotropy, DMI | no universal exponent; decrease with m | measure, or fit |

**Derived scalings** (taking K ∝ m³ and A ∝ m²): B_K = 2K/Ms ∝ m²; l_ex roughly constant; wall width δ = π√(A/K) ∝ m^{−1/2}; wall energy σ_w = 4√(AK) ∝ m^{5/2}; Δ = KV/(k_BT) falls faster than 1/T.

**Curie temperatures (bulk, approximate).** Fe 1043 K, Co ≈ 1390 K, Ni ≈ 630 K, Py ≈ 850–870 K, YIG ≈ 560 K, L1₀ FePt ≈ 750 K. Ultrathin films are lower (finite size).

**Most common misuse.**
- Scaling only `Msat` with T and keeping room-temperature `Ku1` and `Aex`.
- Applying Callen–Callen m³ to interface PMA or two-ion systems without checking.

## 3. Thermal activation: Arrhenius / Néel–Brown

**Néel–Brown law.** τ = τ₀·exp(E_b/k_BT) = f₀⁻¹·e^Δ, where Δ = E_b/(k_BT) is the **thermal stability factor**.
- Barrier for a uniaxial macrospin (coherent rotation) with the field along the easy axis: E_b = K_eff·V·(1 − H/H_K)², for escape from the state antiparallel to H. K_eff includes shape anisotropy.
- General form: E_b = E₀(1 − H/H₀)^n with n ≈ 1.5–2 (see the reversal chapter).
- Above the coherent size, reversal goes through nucleation, and E_b saturates far below KV. For a wall-mediated barrier E_b is of order σ_w × (cross-section of the wall). Compute it rather than assume KV.

**Attempt frequency.** f₀ ≈ 1e9–1e12 Hz (τ₀ = 1 ps–1 ns). f₀ = 1 GHz is the usual device-literature default.
- Brown's high-barrier result for a uniaxial macrospin in zero field gives the escape rate from one well: Γ = f₀·e^{−Δ}, with f₀ = [α/(1 + α²)]·γ·B_K·√(Δ/π). It is valid for Δ ≳ 5.
- The relaxation time of ⟨m_z⟩ between two equal wells is 1/(2Γ).
- Examples (Δ = 40): α = 0.01 with B_K = 0.1 T gives f₀ ≈ 6e8 Hz; α = 0.1 with B_K = 1 T gives f₀ ≈ 6e10 Hz. f₀ is therefore not universal: it scales with α and B_K.

| Δ | 5 | 10 | 20 | 25 | 30 | 40 | 60 |
|---|---|---|---|---|---|---|---|
| τ at f₀ = 1 GHz (divide by 10 for 10 GHz) | 0.15 µs | 22 µs | 0.49 s | 72 s | 3.0 h | 7.5 yr | 3.6e9 yr |

**Retention targets** (f₀ = 1 GHz).
- Δ = ln(f₀·10 yr) = 40.3 gives a 10-year *mean* lifetime for a single bit.
- An array that needs failure probability P per bit over time t needs Δ ≈ ln(f₀·t/P). For example, P = 1e-9 over 10 yr needs Δ ≈ 61. This is why Δ ≈ 60–80 is quoted for large memories, with extra margin for the spread of Δ between bits.
- Stochastic or probabilistic devices deliberately use Δ ≲ 10.

**Superparamagnetism** (τ ≪ measurement time τ_m). In zero field the moment averages to zero, and M(B) is anhysteretic.
- Isotropic particle: M = Ms·L(x), with L the Langevin function and x = Ms·V·B/(k_BT) (B in T).
- Aligned easy axes, high barrier: M = Ms·tanh(x).

**Blocking temperature.** T_B = K_eff·V/(k_B·ln(f₀τ_m)).
- For τ_m = 100 s and f₀ = 1 GHz, ln(f₀τ_m) = 25.3, so K_eff·V ≈ 25·k_B·T_B.
- Fast probes (FMR, ns pulses) have a small ln(f₀τ_m), so the same particles look blocked at higher T.

**Size for Δ = 40 at 300 K** (sphere diameter, coherent rotation assumed):

| K_eff (MJ/m³) | 0.05 | 0.2 | 0.45 (hcp Co) | 6.6 (L1₀ FePt) |
|---|---|---|---|---|
| Diameter (nm) | 18.5 | 11.7 | 8.9 | 3.6 |

These are valid only if the diameter is below about 2·R_coh. Larger particles and elements reverse with E_b < KV.

**Validity.** Δ ≳ 5–10 (Kramers high-barrier regime), a single dominant barrier, weak interactions, parameters taken at T. The **most common misuse** is to take E_b = K·V for an element that reverses by nucleation, or to plug a room-temperature K into a high-T rate.

**Sweep-rate and measurement-time dependence of coercivity** (the Sharrock law) is covered in the reversal chapter, §5.

## 4. Thermally activated wall motion (creep), briefly

**Regimes** for a wall in weak disorder:
- **Creep** (H ≪ H_dep): v = v₀·exp[−(U_c/k_BT)·(H_dep/H)^µ], with µ = 1/4 for a 1D elastic wall in 2D random disorder (Lemerle et al. 1998).
- **Depinning** (H ≈ H_dep).
- **Flow** (H ≫ H_dep): see the wall-dynamics chapter.

Creep velocities are nm/s–mm/s. A micromagnetic window of µs at most resolves only ≳ cm/s (10 nm per µs), so direct simulation reaches the depinning and thermally assisted flow regimes near H_dep, not deep creep.

**Setup.**
- Build the disorder with grains (`ext_makegrains`, plus region-wise `Ku1`, `Msat` or `anisU` spread, or `ext_ScaleExchange` at grain boundaries).
- Run at `Temp` > 0, and follow the wall with `ext_centerWall` and `ext_dwpos`.
- Check creep in measured or extrapolated data by plotting ln v against H^{−1/4}, which should be linear.

## 5. How a simulation measures it: seeds, ensembles, error bars

**Single-run protocol.**
1. `Relax()` at T = 0.
2. Set `Temp` and `ThermSeed(seed)`.
3. Run with `FixDt` (or a validated adaptive step), with `TableAutoSave` at the sampling you need.
4. For an event time, use `RunWhile(m.Comp(2).Average() > 0 && t < tmax)`, which stops at the event and also bounds the run.

**Ensembles.**
- Write one input file per seed (sed-generated, recipes.md §6), and run them as a batch (`mx3 batch`, or `mumax3 a.mx3 b.mx3 …`, which upstream mumax3 runs as a queue, one after another per GPU; only the mumax3-ultrafast fork has `-j N` to run several at once on one GPU).
- Put the seed in the file name and the header.
- Every member can start from the same relaxed state; the noise decorrelates them. Members with the **same** seed are identical, not independent.

| Quantity | Estimator and error bar | N for a target precision |
|---|---|---|
| Mean of independent samples | x̄ ± s/√N | – |
| Switching probability p from N trials | p̂ = k/N, SE = √(p̂(1−p̂)/N); use a Wilson interval near 0 or 1 | ±0.05 at p ≈ 0.5: N ≈ 100; ±0.016: N ≈ 1000 |
| Zero events in N trials | 95 % upper bound ≈ 3/N (rule of three) | to bound p < 1e-3 you need N ≈ 3000 |
| Waiting time τ (exponential, Poisson) | τ̂ = (total observed time, including unswitched runs censored at t_max) / (number of switches); relative SE ≈ 1/√(number of switches) | 10 % precision needs ≈ 100 events |
| Time average of a correlated signal | N_eff ≈ T_run/(2τ_c), with τ_c the autocorrelation time; discard a burn-in of several τ_c; use batch means for the error bar | – |

**Arrhenius extraction.**
- Measure τ at several T (or H), with all parameters held fixed. The slope of ln τ against 1/T is E_b/k_B, and the intercept is −ln f₀.
- If `Msat` and `Ku1` change with T, the slope is not E_b: either refit with the T dependence included, or vary H at fixed T and fit ln τ = −ln f₀ + Δ₀(1 − H/H₀)^n.

**Barriers too high to sample** (Δ ≳ 10–15; with f₀ ≈ 1e9–1e10 Hz, τ already exceeds µs at Δ ≈ 10–15).
- Raise T, or lower the barrier with a field, and extrapolate along a fitted law.
- Or compute E_b directly as the difference between the minimum and the saddle-point energy. Use a minimum-energy-path (string/NEB) method outside mumax3, or a constrained-energy scan, and plug the result into Néel–Brown.

## Sanity checks

| Check | Expected | If not |
|---|---|---|
| One cubic cell (isotropic demag) in a uniaxial well, `Ku1` with `anisU` ∥ z and B ∥ z | equipartition: ⟨m_x²⟩ = ⟨m_y²⟩ = k_BT/(2K_eff·V), with K_eff = Ku1 + Ms·B/2 and V the cell volume | wrong `FixDt`, `GammaLL` or units; `alpha` = 0; a relaxer in use |
| `Temp` = 0 | reproduces the deterministic run | stray noise source |
| Halve `FixDt` | averages and rates unchanged within error bars | step too large |
| Change `alpha` at fixed T | equilibrium averages unchanged, only rates change (fluctuation–dissipation) | noise or damping mis-set |
| Different seeds | different trajectories, statistically equal | identical seeds |
| Arrhenius plot | ln τ linear in 1/T; slope ≈ the computed barrier; f₀ within 1e9–1e12 Hz | multiple barriers, T-dependent parameters, too few events |
| Two cell sizes | rates and coercivities agree within the stated tolerance | UV-cutoff sensitivity: report it |
| Superparamagnetic particle | M(B) anhysteretic and matching the Langevin (or tanh) function | measurement window shorter than τ |

## Common mistakes

- `Temp` set before `Relax()` or `Minimize()`, expecting a thermal equilibrium: the noise is off during relaxation.
- `alpha` = 0, or a tiny α "to reduce noise". The noise amplitude ∝ √α, so α = 0 means no thermal field. α sets rates; it is not a noise knob.
- Every ensemble member using the default (fixed) seed, or the same `ThermSeed`.
- No time-step or cell-size convergence test, or comparing thermal results obtained with different Δx or Δt.
- Measured Ms(T), A(T), K(T) combined with `Temp` = T without acknowledging the double counting.
- Trying to observe Δ ≈ 40 switching directly. That takes years: extrapolate, or compute the barrier.
- Reading `E_therm` as physical energy; drawing statistics from a single trajectory; using T near T_c with fixed-length spins.
- Expecting the same seed to reproduce a CUDA trajectory on the Metal fork, or leaving `SpeculativeStep` on as if it were active at T > 0.
- Ignoring that an α-ramp absorber at T > 0 injects extra noise near the edges.

## References

- W. F. Brown Jr., "Thermal fluctuations of a single-domain particle", Phys. Rev. 130, 1677 (1963).
- L. Néel, "Théorie du traînage magnétique des ferromagnétiques en grains fins avec applications aux terres cuites", Ann. Géophys. 5, 99 (1949).
- J. L. García-Palacios and F. J. Lázaro, "Langevin-dynamics study of the dynamical properties of small magnetic particles", Phys. Rev. B 58, 14937 (1998).
- W. T. Coffey and Y. P. Kalmykov, "Thermal fluctuations of magnetic nanoparticles: Fifty years after Brown", J. Appl. Phys. 112, 121301 (2012).
- J. Leliaert et al., "Adaptively time stepping the stochastic Landau-Lifshitz-Gilbert equation at nonzero temperature: implementation and validation in MuMax3", AIP Advances 7, 125010 (2017).
- G. Grinstein and R. H. Koch, "Coarse graining in micromagnetics", Phys. Rev. Lett. 90, 207201 (2003).
- H. B. Callen and E. Callen, "The present status of the temperature dependence of magnetocrystalline anisotropy, and the l(l+1)/2 power law", J. Phys. Chem. Solids 27, 1271 (1966).
- M. D. Kuz'min, "Shape of temperature dependence of spontaneous magnetization of ferromagnets: quantitative analysis", Phys. Rev. Lett. 94, 107204 (2005).
- U. Atxitia et al., "Multiscale modeling of magnetic materials: temperature dependence of the exchange stiffness", Phys. Rev. B 82, 134440 (2010).
- S. Okamoto et al., "Chemical-order-dependent magnetic anisotropy and exchange stiffness constant of FePt (001) epitaxial films", Phys. Rev. B 66, 024413 (2002).
- O. N. Mryasov, U. Nowak, K. Y. Guslienko and R. W. Chantrell, "Temperature-dependent magnetic properties of FePt: effective spin Hamiltonian model", Europhys. Lett. 69, 805 (2005).
- S. Lemerle et al., "Domain wall creep in an Ising ultrathin magnetic film", Phys. Rev. Lett. 80, 849 (1998).
- M. P. Sharrock, "Time dependence of switching fields in magnetic recording media", J. Appl. Phys. 76, 6413 (1994).
- A. Vansteenkiste et al., "The design and verification of MuMax3", AIP Advances 4, 107133 (2014).
