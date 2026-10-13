# Magnetisation reversal and hysteresis: Stoner–Wohlfarth, demag factors, reversal modes, loops

Use this chapter for switching and coercive fields (Stoner–Wohlfarth, nucleation fields, Brown's paradox), demagnetising factors and shape anisotropy, the reversal mode to expect at a given size, sweep-rate and thermal reduction of coercivity (Sharrock), and for setting up and checking mumax3 hysteresis loops, including exchange-coupled multilayers and SAFs.
Fields are given as B = µ0H in tesla (`B_ext`), or as H in A/m where written H.

## 0. Symbols

| Symbol | Meaning | Unit | mumax3 |
|---|---|---|---|
| Ms | saturation magnetisation | A/m | `Msat` |
| Ku | uniaxial anisotropy constant (axis `anisU`) | J/m³ | `Ku1` (`Ku2` 2nd order) |
| K_eff | effective uniaxial constant, magnetocrystalline + shape | J/m³ | derived |
| H_K, B_K | anisotropy field: H_K = 2K_eff/(µ0Ms), B_K = µ0H_K = 2K_eff/Ms | A/m, T | derived |
| N_x, N_y, N_z | magnetometric demagnetising factors, N_x + N_y + N_z = 1 (SI) | – | measured from `B_demag` or `E_demag` |
| l_ex | exchange length √(2A/(µ0Ms²)) | m | from `Aex`, `Msat` |
| h = H/H_K | reduced field | – | – |

Py has l_ex ≈ 5.7 nm. Note that some texts define l_ex = √(A/(µ0Ms²)), which is smaller by √2; check which one a quoted critical size uses.

## 1. Stoner–Wohlfarth (SW) coherent rotation

**Energy density** for a field at angle ψ from the easy axis, with M at angle θ:

e(θ) = K_eff sin²θ − µ0MsH cos(θ − ψ)  [J/m³]   (µ0H is the applied field B in T)

- The shape contribution in K_eff is K_eff = Ku + (µ0/2)(N_hard − N_easy)Ms².
- **Switching (irreversible jump) field**: h_sw(ψ) = (cos^{2/3}ψ + sin^{2/3}ψ)^{−3/2}.
- **Astroid**: h_∥^{2/3} + h_⊥^{2/3} = 1. Inside the astroid there are two minima; crossing it destroys one of them.
- **Coercive field** (where M·ĥ = 0): h_c = h_sw for ψ ≤ 45° and h_c = ½ sin 2ψ for ψ ≥ 45°. For ψ ≥ 45°, M passes through zero reversibly before the jump.

| ψ | 0° | 0.1° | 1° | 5° | 15° | 30° | 45° | 60° | 75° | 90° |
|---|---|---|---|---|---|---|---|---|---|---|
| h_sw | 1 | 0.979 | 0.907 | 0.766 | 0.615 | 0.524 | 0.500 | 0.524 | 0.615 | 1 (reversible) |
| h_c | 1 | 0.979 | 0.907 | 0.766 | 0.615 | 0.524 | 0.500 | 0.433 | 0.250 | 0 |

- **Hard-axis loop** (ψ = 90°): M_∥ = Ms·H/H_K up to H_K, with no hysteresis. This is the standard way to read B_K from a simulation or an experiment.
- **Non-interacting ensemble with 3D-random easy axes**: remanence Mr = Ms/2 and coercivity ≈ 0.48 H_K.

**Validity.** Single-domain particle below the coherence size (§2), uniform rotation, T = 0, quasi-static field; exact in micromagnetics only for ellipsoids with R < R_coh.
**Accuracy.** In prisms and thin elements the demag field is non-uniform, so end and flower states nucleate reversal early and SW with K_shape overestimates the switching field, increasingly so as the element grows. Near ψ = 0 a 1° misalignment already lowers h_sw by 9 %.

**Most common misuse.** Predicting the coercivity of an extended film or bulk magnet as H_K, ignoring Brown's paradox (§2).

## 2. Nucleation fields, Brown's paradox, reversal modes

**Nucleation field** H_N is the field at which the saturated state becomes unstable. For an ellipsoid with the field along the easy (long) axis: coherent H_N = H_K + (N_⊥ − N_∥)Ms; curling H_N = H_K − N_∥Ms + q²(l_ex/R)²Ms, with q = 1.841 (infinite cylinder) or 2.082 (sphere) (Frei, Shtrikman and Treves 1957).
They are equal at the coherence radius R_coh = q·l_ex/√N_⊥: sphere ≈ 3.61 l_ex (≈ 21 nm for Py); infinite cylinder ≈ 2.60 l_ex (≈ 15 nm for Py).

**Brown's paradox.** For a defect-free ellipsoid, Brown's theorem gives H_c ≥ H_N. Measured coercivities are nevertheless usually far below H_K, often 10–40 % of it.
The deficit comes from defects with reduced K, rough or oxidised surfaces, corners and edges (non-uniform demag field), misaligned grains, and thermal activation. Kronmüller's phenomenological form: H_c = α_K·H_K − N_eff·Ms, with microstructural parameters α_K < 1 and N_eff.

**Consequence for simulation.** A perfect, T = 0, fast-swept simulated particle or film gives an **upper bound** on H_c.
- To approach experiment, add disorder: grains (`ext_makegrains`, `ext_make3dgrains`) with region-wise `Ku1`/`anisU` spread, rough edges, reduced-K surface regions, or reduced inter-grain exchange (`ext_ScaleExchange`); add temperature and a slower effective sweep (§5).
- If `Ku1` is lowered to fit H_c instead, say so: the fitted value then absorbs microstructure.

| Mode | Where it occurs | Signature in a mumax3 run |
|---|---|---|
| Coherent rotation | R ≲ R_coh; small ellipsoids and short pillars | \|⟨m⟩\| ≈ 1 throughout the reversal |
| Curling | R ≳ R_coh in wires, spheres and elongated particles | flux-closing circulation about the axis; \|⟨m⟩\| < 1 during the reversal |
| Buckling | narrow size range near R_coh in elongated particles | transverse sinusoidal modulation |
| Nucleation + propagation | elements ≫ l_ex, films, granular media | nucleation at an edge, corner or defect, then wall motion; H_c set by nucleation or by depinning |
| Vortex nucleation/annihilation | soft disks and squares above the single-domain size | "pinched" loop: low remanence, jumps at the vortex nucleation and annihilation fields |
| C- and S-state switching | soft rectangles with end domains | which state forms depends on the field tilt and the history |

## 3. Demagnetising factors

For uniform M: E_d = (µ0/2)·N·Ms²·V and B_d = −µ0N·Ms·m (uniform only for ellipsoids). Only aspect ratios matter, not absolute size.

**Spheroids (Osborn 1945).** The long or short axis is c, the others a = b, and N_a = N_b = (1 − N_c)/2.
- Prolate (m = c/a > 1): N_c = [m/√(m²−1)·ln(m + √(m²−1)) − 1]/(m² − 1). For long needles N_c → (ln 2m − 1)/m².
- Oblate (m = a/c > 1): N_c = m²/(m²−1)·[1 − arcsin(√(m²−1)/m)/√(m²−1)]. For thin disks N_c → 1 − π/(2m).

| m | 1 | 2 | 5 | 10 | 100 |
|---|---|---|---|---|---|
| Prolate N_long | 1/3 | 0.174 | 0.056 | 0.020 | 0.0004 |
| Oblate N_short | 1/3 | 0.527 | 0.751 | 0.861 | 0.985 |

**Rectangular prism 2a × 2b × 2c (Aharoni 1998).** Here r = √(a²+b²+c²). D_x and D_y follow by cyclic permutation. Checks: a cube gives 1/3, and D_x + D_y + D_z = 1.

```
π·D_z = (b²−c²)/(2bc)·ln[(r−a)/(r+a)] + (a²−c²)/(2ac)·ln[(r−b)/(r+b)]
      + b/(2c)·ln[(√(a²+b²)+a)/(√(a²+b²)−a)] + a/(2c)·ln[(√(a²+b²)+b)/(√(a²+b²)−b)]
      + c/(2a)·ln[(√(b²+c²)−b)/(√(b²+c²)+b)] + c/(2b)·ln[(√(a²+c²)−a)/(√(a²+c²)+a)]
      + 2·atan[ab/(c·r)] + (a³+b³−2c³)/(3abc) + (a²+b²−2c²)·r/(3abc)
      + (c/(ab))·(√(a²+c²)+√(b²+c²)) − [(a²+b²)^{3/2}+(b²+c²)^{3/2}+(c²+a²)^{3/2}]/(3abc)
```

| Prism L × W × T | N_L | N_W | N_T | µ0(N_W − N_L)Ms for Py (µ0Ms = 1.0 T) |
|---|---|---|---|---|
| 2 : 1 : 1 | 0.198 | 0.401 | 0.401 | 0.20 T |
| 10 : 1 : 1 | 0.046 | 0.477 | 0.477 | 0.43 T |
| 100 × 50 × 2 nm | 0.027 | 0.055 | 0.919 | 28 mT |
| 200 × 100 × 5 nm | 0.032 | 0.065 | 0.904 | 33 mT |
| 500 × 100 × 5 nm | 0.013 | 0.069 | 0.918 | 56 mT |
| 1000 × 250 × 10 nm | 0.014 | 0.057 | 0.929 | 43 mT |
| 100 × 100 × 5 nm | 0.060 | 0.060 | 0.881 | 0 (in-plane) |

**Thin films and strips.**
- Infinite film: N_⊥ = 1 and N_∥ = 0. Infinitely long strip of width w and thickness t, with p = w/t: N_t = [2·atan p − ln(1+p²)/(2p) + (p/2)·ln(1 + 1/p²)]/π and N_w = 1 − N_t.
- For w ≫ t, N_w ≈ (t/(πw))·[ln(w/t) + 3/2]. For example, w/t = 20 gives N_w ≈ 0.072.

**Measuring N in mumax3** (any shape, including the discretised staircase): set `m = Uniform(1,0,0)` without relaxing; then N_x = −⟨B_demag,x⟩/(µ0Ms) from `B_demag.Average()` (averaged over the magnet), or N_x = 2·E_demag/(µ0Ms²V) with V = `geom.Average()` × box volume. Repeat for y and z and check that the sum is 1. `EdgeSmooth` reduces the staircase error on curved edges.

## 4. Shape anisotropy, thin elements, flux closure

**Shape anisotropy** (uniform M): K_shape = (µ0/2)(N_hard − N_easy)Ms² in J/m³, i.e. B_K,shape = µ0(N_hard − N_easy)Ms in T.
- Thin film: K_eff,⊥ = Ku1 − µ0Ms²/2. If this is positive the film has a perpendicular easy axis (PMA), equivalently M_eff < 0 in the FMR chapter.
- In-plane elements: the last column of the table above gives the uniform-rotation estimate of the in-plane anisotropy field.

**Validity.** Strictly valid only for uniform M (ellipsoids, elements a few l_ex in size). Larger elements form flower, C, S or end-domain states and switch below µ0ΔN·Ms: use it as a scale and an upper bound, not a prediction.

**Flux closure and vortices.**
- Soft elements (Py, CoFeB with weak Ku) much larger than l_ex lower their demag energy by forming vortex, Landau or diamond closure states. Thin and small elements stay single-domain (flower or leaf states).
- For Py disks the crossover lies at diameters of order 100 nm for thicknesses of order 10 nm (Cowburn et al. 1999); compute it rather than quote it. Vortex loops show nucleation and annihilation jumps; the annihilation field grows with thickness/radius.
- **How to compute the ground state**: relax from `Uniform(...)`, `Vortex(c, p)` and `RandomMagSeed(n)`, and compare `E_total`. Relaxers find a local minimum only.

## 5. Sweep rate and thermal activation (Sharrock)

**Barrier.** E_b(H) = E₀(1 − H/H₀)^n, with n = 2 for a field along the easy axis (SW) and n ≈ 1.5 for misaligned fields (Victora 1989). E₀ = K_eff·V for a coherently rotating particle; in films and large grains a smaller activation volume sets E₀.

**Sharrock law.** H_c(t) = H₀·{1 − [(k_BT/E₀)·ln(f₀t/ln 2)]^{1/n}}.
- t is the measurement time scale (time for half of an ensemble to switch at constant field); f₀ ≈ 1e9–1e12 Hz (see the thermal chapter).
- For a linear sweep at rate R = dB/dt, switching happens where E_b(H_sw) ≈ k_BT·ln(f₀·t_eff), with t_eff = k_BT/(R·|∂E_b/∂B|) evaluated at H_sw. The dependence is logarithmically weak, so iterate once.

| H_c/H₀ (n = 2, f₀ = 1e9 Hz) | t = 1 ns | t = 1 µs | t = 1 s |
|---|---|---|---|
| Δ₀ = E₀/k_BT = 40 | 0.90 | 0.57 | 0.27 |
| Δ₀ = 60 | 0.92 | 0.65 | 0.41 |
| Δ₀ = 100 | 0.94 | 0.73 | 0.54 |

**Consequences.**
- T = 0 simulations, and sweeps of 1e6–1e10 T/s (t_eff ~ ns), give H_c near H₀. Laboratory loops (t ~ 1–100 s) give much lower values. Compare at matched time scales, or extrapolate with Sharrock.
- Even at T = 0, a dynamic sweep with physical α lags behind the field. The relaxation time is τ_r ≈ 1/(αγB_eff), e.g. 2.8 ns for α = 0.02 and B_eff = 0.1 T. A sweep is quasi-static only if R·τ_r is much smaller than the field resolution wanted; for 1 mT that means R ≪ 3.5e5 T/s.

**Validity.** Δ₀ ≳ 10–20, a single barrier, non-interacting particles. A distribution of barriers in real media broadens and shifts the result.

## 6. How a simulation measures it: hysteresis loops

**Quasi-static loop.** At each field: set `B_ext`, call `Relax()` or `Minimize()`, then `TableSave()`. Record `B_ext`, `m` (normalised, averaged over the magnet) or `m_full` (A/m; use it when `Msat` differs between regions, since the measured moment is ∝ Σ Ms_i·m_i·V_i), plus `E_total` and `maxTorque`.
- Relaxers ignore `alpha` and `Temp` (pitfalls.md §4, §7), so such loops are T = 0 loops.

**Relax() vs Minimize().**
- `Minimize()` is faster close to equilibrium (small steps along a branch); `Relax()` is more robust after large changes. Both descend to the nearest local minimum, so at an instability the state they reach need not be the one the dynamics would select.
- If the post-jump state matters (domain pattern, vortex chirality), redo that step with `Run()` at the physical `alpha` until `maxTorque` is small, then continue relaxing.

**Branch tracking.** Never re-initialise `m` between steps; start each branch from saturation; save states near jumps with `SaveAs(m, "...")` to restart or bisect with `m.LoadFile("...")` (minor loops and metastable branches also start from saved states).

**Symmetry breaking.** A field exactly along a symmetry axis of a symmetric sample leaves the reversed state as a zero-torque equilibrium past its instability, so switching is late or never happens.
- Tilt the field by 0.1–1° and report the tilt (it lowers the SW h_sw by 2–9 %), or add a small perturbation: `m = CurrentMag().Add(0.01, RandomMagSeed(i))`.

**Field step.** Coarse far from switching (a few % of H_c), fine near it (≤ 0.5–1 % of H_c), or bisect between the last two fields. Report H_sw as the bracket [B_i, B_i+1]; a vertical jump between two points does not resolve H_sw.

**Convergence.** Halve the step near switching; tighten `RelaxTorqueThreshold` (`Relax`) or `MinimizerStop` (`Minimize`) and check `maxTorque` at each point; keep the cell ≤ l_ex and compare H_sw at two cell sizes (corner nucleation is mesh-sensitive).

**Dynamic sweep.** `B_ext = vector(B0 + R*t, 0, 0)` with the physical `alpha`, then `Run(T)` with `TableAutoSave`. H_c rises with R, so always report R.

## 7. Exchange-coupled multilayers and SAFs

**Interlayer coupling.** E/area = −J₁·m₁·m₂. With this sign, J₁ < 0 is antiferromagnetic; some papers flip the sign.
- |J₁| is typically 0.1–1 mJ/m² for Ru- or Ir-mediated coupling, up to a few mJ/m² at the first AF peak of thin Ru (order of magnitude). Biquadratic coupling −J₂(m₁·m₂)² has no built-in term.

**SAF saturation** (macrospin layers, in-plane field, no anisotropy): B_sat = −J₁·[1/(Ms₁t₁) + 1/(Ms₂t₂)] in T.
- Symmetric SAF: B_sat = 2|J₁|/(Ms·t), with the layers canted at cosθ = B/B_sat below saturation. Example: J₁ = −1 mJ/m², Ms = 1 MA/m and t = 2 nm give 1 T.
- With uniaxial anisotropy along the field, a spin-flop transition appears; that case is not covered here.

**Exchange bias** (Meiklejohn–Bean picture): a fixed unidirectional field B_EB = J_EB/(Ms·t_F) acting on the pinned layer only. Set it with `B_ext.SetRegion(r, vector(Bx + B_EB, 0, 0))`; `SetRegion` replaces the uniform value, so include the applied field.

**mumax3 implementation.**
- Put the two magnetic layers in adjacent cell layers (regions r1, r2). `ext_InterExchange(r1, r2, A12)` replaces the default inter-region exchange (harmonic mean of `Aex`) with A12 in J/m. The exchange field is (2A12/(Ms·Δz²))·m_neighbour, so J₁ = 2·A12/Δz, i.e. A12 = J₁·Δz/2 (negative for AF coupling).
- `ext_ScaleExchange(r1, r2, s)` multiplies the harmonic mean by s. s = 0 decouples the regions and 0 < s < 1 weakens the coupling, e.g. at grain boundaries.
- Exchange couples nearest-neighbour cells only, so with non-magnetic spacer cells (`Msat` = 0) between the layers `ext_InterExchange` does nothing. Either leave the spacer out of the mesh (it then only changes the dipolar coupling), or build a custom RKKY field with `AddFieldTerm`, `Shifted` and `Masked` plus the matching `AddEdensTerm`, and validate it.
- There is one Δz for the whole stack, so every layer thickness must be a multiple of Δz. A12 depends on Δz: rescale it whenever Δz changes.
- **Check**: with `EnableDemag = false`, E_total(parallel) − E_total(antiparallel) = −2J₁ × interface area. Also check B_sat from the loop.

## Sanity checks

| Check | Expected |
|---|---|
| Hard-axis loop of a single-domain particle | linear, saturating at B_K = 2Ku1/Msat + µ0ΔN·Ms |
| Easy-axis loop of a small ellipsoid (R < R_coh) | square, switching at B_K + µ0(N_⊥ − N_∥)Ms, reduced by the tilt factor of §1 |
| Symmetric sample | H_c+ = −H_c−; asymmetry means unresolved steps, unconverged relaxation, or a bias |
| Measured demag factors | N_x + N_y + N_z = 1; a cube gives 1/3 |
| Adding disorder or temperature | H_c decreases and never exceeds the ideal nucleation field |
| Energy along a branch | `E_total` continuous, dropping at each jump |
| SAF | antiparallel at B = 0; saturation at 2\|J₁\|/(Ms·t) |

## Common mistakes

- Equating a simulated H_c with a measured one without accounting for Brown's paradox, sweep rate and temperature.
- A field exactly along a symmetry axis: switching never happens, or happens far too late.
- A field step coarser than the feature: square-looking loops with an unresolved H_sw.
- Re-initialising `m` at each step, which destroys the hysteresis.
- Trusting the relaxer's path through an instability.
- Unit slips: mT vs T in `B_ext` (use `B*1e-3`), and Oe vs mT (1 mT = 10 Oe).
- Using K_eff (which already contains shape anisotropy) as `Ku1` while demag is on.
- Reporting M/Ms from `m` in a stack where Ms differs between layers (use `m_full`).
- Applying `ext_InterExchange` across empty spacer cells, or not rescaling A12 after changing Δz.
- Using the SW astroid for elements that reverse through end domains or vortices.

## References

- E. C. Stoner and E. P. Wohlfarth, "A mechanism of magnetic hysteresis in heterogeneous alloys", Phil. Trans. R. Soc. Lond. A 240, 599 (1948).
- W. F. Brown Jr., *Micromagnetics* (Interscience, 1963).
- A. Aharoni, *Introduction to the Theory of Ferromagnetism* (Oxford Univ. Press, 2nd ed. 2000).
- J. A. Osborn, "Demagnetizing factors of the general ellipsoid", Phys. Rev. 67, 351 (1945).
- A. Aharoni, "Demagnetizing factors for rectangular ferromagnetic prisms", J. Appl. Phys. 83, 3432 (1998).
- E. H. Frei, S. Shtrikman and D. Treves, "Critical size and nucleation field of ideal ferromagnetic particles", Phys. Rev. 106, 446 (1957).
- H. Kronmüller and M. Fähnle, *Micromagnetism and the Microstructure of Ferromagnetic Solids* (Cambridge Univ. Press, 2003).
- M. P. Sharrock, "Time dependence of switching fields in magnetic recording media", J. Appl. Phys. 76, 6413 (1994).
- R. H. Victora, "Predicted time dependence of the switching field for magnetic materials", Phys. Rev. Lett. 63, 457 (1989).
- R. P. Cowburn et al., "Single-domain circular nanomagnets", Phys. Rev. Lett. 83, 1042 (1999).
- S. S. P. Parkin, N. More and K. P. Roche, "Oscillations in exchange coupling and magnetoresistance in metallic superlattice structures: Co/Ru, Co/Cr, and Fe/Cr", Phys. Rev. Lett. 64, 2304 (1990).
- A. Vansteenkiste et al., "The design and verification of MuMax3", AIP Advances 4, 107133 (2014).
