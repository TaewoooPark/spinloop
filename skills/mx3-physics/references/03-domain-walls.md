# Static domain walls: profiles, widths, energies, chirality, pinning

Use this chapter for the structure of a wall at rest: which wall type to expect, its width under each common definition and how to convert between them, its energy, the effect of DMI, edges and applied fields, pinning strengths, and how to extract a width, energy or wall angle from mumax3 output.
Wall motion is in 04-wall-dynamics.md; scales and cell-size rules in 02-scales.md; edges, moving frames and convergence in 09-numerics.md.

**Notation (SI).** A = `Aex` (J/m); Ms = `Msat` (A/m); Ku = `Ku1` (J/m³) along `anisU`; K_eff = Ku − µ0Ms²/2 (ultrathin perpendicular film, local approximation); D = `Dind` (interfacial) or `Dbulk` (J/m²); t = film thickness, w = strip width (m); γ = `GammaLL` = 1.7595e11 rad/(s·T). Fields are B = µ0H in T, as `B_ext` takes them; H (A/m) only where written. θ = polar angle of m from the easy axis; φ = in-plane angle of the wall moment from the wall normal (φ = 0 or π: Néel; ±π/2: Bloch).
**mumax3 entry rule:** with demagnetisation on (default) keep `Ku1` = the material Ku; mumax3 adds the −µ0Ms²/2 itself (02-scales.md §4). Every K_eff below is a derived number, not an input.

## 1. The 1D wall profile
θ(x) = 2 arctan exp((x − q)/Δ), so m_∥ = −tanh((x − q)/Δ) along the easy axis and m_⊥ = sech((x − q)/Δ) in the wall; Δ = √(A/K) [m].
- **Which K:** Ku for a bulk uniaxial magnet (Bloch wall, no volume charges); K_eff for an ultrathin PMA film (t ≪ Δ). For walls in soft in-plane films and strips there is no √(A/K): their width is set by magnetostatics, l_ex and the strip width (§3, §5).
- **Assumptions:** 1D, infinite medium, uniaxial K, rigid in-wall angle φ, no long-range demagnetising field (or the local K_eff for ultrathin films). The profile follows from the first integral A θ′² = K sin²θ (exchange density = anisotropy density at every x).
- **Accuracy vs full micromagnetics:** exact for the 1D Bloch wall with `EnableDemag = false`. In ultrathin PMA films with demag the simulated Δ differs from √(A/K_eff) by ~5–20%. Néel walls (DMI) add slowly decaying m_x tails from their volume charges, so tail-sensitive widths (e.g. the Thiele width) grow as the wall turns Néel (Thiaville et al. 2012).
- **Common misuse:** Ku instead of K_eff for an ultrathin film (Δ too small by √(Ku/K_eff)); fitting a tanh to a soft-film Néel wall, whose logarithmic tails are not a tanh.

### Width definitions and conversions (1D profile)
| Name | Value | Definition | Used by |
|---|---|---|---|
| wall parameter | Δ | scale of tanh/sech; also the Thiele width of the rigid 1D wall | 1D models; mobility v = γΔB/α (04) |
| Lilley width | πΔ | tangent to θ(x) at the centre spans π; equals ∫ m_⊥ dx | the most common "wall width" in papers |
| integral (energy) width | 2Δ | ∫ (1 − m_∥²) dx = ∫ sin²θ dx | integral estimators; σ = 2K·2Δ |
| 10–90 % width | 2 ln3·Δ ≈ 2.20Δ | m_∥ from −0.8 to +0.8 | line profiles of imaging data |
| FWHM of m_⊥ | 2 arcosh2·Δ ≈ 2.63Δ | sech = ½ | images of the in-wall component (XMCD, SEMPA, DPC) |
| FWHM of sech² | 2 arcosh√2·Δ ≈ 1.76Δ | profile of ∂m_∥/∂x, of `Edens_exch` and `Edens_anis` | energy-density maps; charge density of a Néel wall |
| fit parameter w in tanh(2x/w) | w = 2Δ | | some papers |
| fit parameter δ in tanh(πx/δ) | δ = πΔ | | Lilley-style fits |
| Thiele width Δ_T | 2wt / ∫(∂_x m)² dV | = Δ for the 1D profile | mobility of real 2D/3D walls (04) |

Always state which definition a quoted width uses; a factor π between Δ and πΔ is the most frequent error in comparisons. The conversion factors are exact only for the tanh profile: walls with tails (Néel walls, soft films) change the ratios by tens of %, so convert only when a tanh fits the measured profile.

## 2. Wall energy
σ = 4√(AK) [J/m²]; per wall in a strip E = σ·w·t [J].
- Exchange and anisotropy each contribute 2√(AK) (equipartition, from A θ′² = K sin²θ). A converged 1D Bloch wall with demag off has E_exch(wall) ≈ E_anis(wall) − E_anis(uniform) to within about 1%; a larger mismatch means under-resolution or a box that squeezes the wall.
- With interfacial DMI, Néel wall of the favoured chirality (|D| ≥ D_N, §4): σ = 4√(AK_eff) + 2ΔK_D − π|D| ≈ 4√(AK_eff) − π|D|.
- **Typical:** 1–15 mJ/m² in PMA films (A = 15 pJ/m, K_eff = 0.3–1 MJ/m³ gives 8.5–15.5 mJ/m²); ~10–15 mJ/m² bulk Co.
- **Validity:** 1D, uniaxial, no in-plane field. **Accuracy:** in thin films the wall's own demagnetising energy raises the simulated value by a few % to ~20%.
- **Common misuse:** dividing an energy difference by the wrong area (t × wall length); quoting σ from runs with different mesh or box.

## 3. Thin-film shape anisotropy and the Bloch–Néel choice
**Soft in-plane films (Py-like, Q ≪ 1).** Thin films carry Néel walls (in-plane rotation, a core a few l_ex wide plus long logarithmic tails); thick films carry asymmetric, vortex-like Bloch walls; cross-tie walls appear in between (Hubert & Schäfer). For Py the transitions lie at film thicknesses of tens of nm. Nothing in §1 applies; simulate the actual thickness with several cells through t when t ≳ 2 l_ex.

**Perpendicular films and strips.** Without DMI the Bloch wall is favoured: the Néel wall carries volume charges ∂m_x/∂x. The penalty is a wall shape anisotropy
K_D = N_x µ0Ms²/2 [J/m³], with N_x ≈ t ln2/(πΔ) (Tarasenko et al. 1998; t ≪ Δ),
so σ_Néel − σ_Bloch = 2ΔK_D ≈ (ln2/π) µ0Ms² t [J/m²], and the wall's hard-axis field is B_K = 2K_D/Ms = N_x µ0Ms [T] (it sets the Walker field, 04 §3).
- **Example:** Ms = 1 MA/m, t = 1 nm, Δ = 6 nm: N_x ≈ 0.037, B_K ≈ 46 mT, σ_N − σ_B ≈ 0.28 mJ/m² (a few % of σ). Thiaville et al. 2012 derived N_x = 0.0224 from 1D numerics for t = 0.6 nm, Δ = 5.65 nm (formula: 0.023).
- **Validity:** t ≪ Δ, extended film. For t ≳ Δ, or narrow strips, measure it (§9).
- **Strips:** what matters is the difference of the wall-volume demagnetising factors along the strip (Néel moment) and across it (Bloch moment) (Mougin et al. 2007). In strips only a few Δ wide the Bloch moment's edge charges can make Néel competitive even without DMI.

## 4. Interfacial and bulk DMI: chirality, energy, critical values
**mumax3 conventions (read from the 3.12 kernels).**
- `Dind`: energy density ε = D[m_z ∇·m − (m·∇)m_z]; effective field B = (2D/Ms)(∂_x m_z, ∂_y m_z, −∂_x m_x − ∂_y m_y).
- `Dbulk`: ε = D m·(∇×m); B = −(2D/Ms)∇×m. Using both at once is a fatal error.

**Chirality.** For a 1D wall the interfacial term integrates to σ_DMI = ±πD cos φ: the sign of D fixes the rotation sense. With mumax3's sign, **`Dind` > 0 makes the wall moment point toward the up (+z) domain**: an up|down wall along +x has m_x < 0 at its centre (↑←↓), a down|up wall m_x > 0 (↓→↑); `Dind` < 0 reverses both. Literature sign conventions differ, so compare wall-moment directions (or measured handedness), never bare signs of D. Chiral Néel walls in heavy-metal/ferromagnet stacks were established through their current-driven motion (Emori et al. 2013; Ryu et al. 2013). `Dbulk` fixes the helicity of Bloch walls instead, with the same 4√(AK) − π|D| energy.

**Wall moment angle (1D q–φ statics, Thiaville et al. 2012).** cos φ0 = πD/(4ΔK_D) for |D| < D_N; pure Néel for |D| ≥ D_N, with
D_N = 4ΔK_D/π ≈ (2 ln2/π²) µ0Ms² t ≈ 0.14 µ0Ms² t [J/m²].
- For Thiaville et al.'s Pt/Co/AlOx film (t = 0.6 nm) this gives ≈0.13 mJ/m², as their 1D numerics do. So a few tenths of mJ/m² already make the walls of a ~1 nm film fully Néel; D_N grows ∝ Ms²t.
- **Naming clash:** Thiaville et al. call D_N "D_c". The spiral threshold is a different number (next item).

**Spiral threshold.** D_c = 4√(AK_eff)/π [J/m²]: there σ = 0 and the uniform state gives way to cycloids or a labyrinth (02-scales.md §6). Treat it as accurate to tens of percent: stray fields favour domains below it.

**Effective DMI field on the wall moment.** B_DMI = D/(MsΔ) [T] (H_DMI = D/(µ0MsΔ) in A/m), acting along the wall normal. It enters the wall energy like an in-plane field B_x (Zeeman −πΔMs B_x cos φ = −πD cos φ for B_x = B_DMI).
- Typical 10–300 mT; D = 1 mJ/m², Ms = 1 MA/m, Δ = 5 nm gives 0.2 T.
- **Misuse:** Thiaville et al. define H_D = πD/(2µ0MsΔ) = (π/2)H_DMI. Check which one a paper quotes before comparing.

**Edge canting.** At a free edge the DMI boundary condition 2A ∂m/∂n = D(ẑ × n) × m (Rohart & Thiaville 2013) tilts m even in a uniform state. mumax3 applies it automatically at geometry edges with `OpenBC = false` (default; implementation in Mulkers et al. 2017).
- 1D result for a perpendicular domain at an edge: sin θ_e = DΔ/(2A) = (2/π)·D/D_c, decaying inward as tan(θ/2) = tan(θ_e/2)·e^(−x/Δ).
- D = 1.5 mJ/m², Δ = 5 nm, A = 15 pJ/m gives θ_e ≈ 0.25 rad. The canting follows the DMI chirality, like half a Néel wall.
- **Consequences:** edges repel chiral walls and skyrmions; wall moments rotate near strip edges; table averages ⟨m_x⟩, ⟨m_y⟩ contain edge contributions (§9).
- **Validity:** local K_eff, smooth edge. The stray field is weaker near an edge, which raises the local K_eff, so the simulated tilt is typically at or somewhat below this estimate. Staircase edges at oblique angles distort it.

## 5. Walls in strips and nanowires
**Soft in-plane strips (head-to-head / tail-to-tail).**
- Wall types: transverse (TW, triangular, moment across the strip), asymmetric transverse (ATW) at intermediate sizes, and vortex walls (VW).
- Energy crossover TW → VW at t·w ≈ 128 A/(µ0Ms²) = 64 l_ex² (McMichael & Donahue 1997, written there as t·w = 128 δ² with δ² = A/(µ0Ms²)). For Py this is ≈2×10³ nm², e.g. t = 10 nm → w ≈ 200 nm. Nakatani et al. 2005 refine the diagram and add the ATW.
- **Validity:** T = 0 energy comparison. Both types are metastable over a wide range, so the initial state decides which one a simulation shows: relax both and compare `E_total`.
- **Width:** the TW width scales with w, not with √(A/K). Compute Δ_T from the relaxed state (§9) when a mobility is needed.
- **Charge:** a head-to-head wall carries net magnetic charge 2Ms·w·t (A·m). It is pulled by strip-end charges and stray fields. `ext_rmSurfaceCharge(region, mxLeft, mxRight)` adds a static field to `B_ext` that cancels the end charges (mimics an infinite wire; mx values ±1, computed for the current mesh and `Msat`).
- **mumax3 starting states:** `TwoDomain(1,0,0, 0,1,0, -1,0,0)` (TW, +y moment, 2-cell Gaussian wall at the box centre); `VortexWall(1, -1, circ, pol)` (a vortex in a square of side = box height). Both are crude guesses: relax them.

**Cylindrical wires:** transverse walls in thin wires; Bloch-point walls in thicker ones. A Bloch point is a singularity that finite differences cannot resolve, so its energy and dynamics are mesh-dependent; state the cell size.

**Perpendicular strips:** Bloch wall across the strip (w ≫ Δ, |D| < D_N), Néel of fixed chirality for |D| ≥ D_N, intermediate φ0 in between (§4). Energy per wall σ·w·t; `TwoDomain(0,0,1, 0,1,0, 0,0,-1)` starts a Bloch wall. The Néel walls favoured by `Dind` > 0 (moment toward the up domain, §4) start from `TwoDomain(0,0,1, -1,0,0, 0,0,-1)` for up|down and `TwoDomain(0,0,-1, 1,0,0, 0,0,1)` for down|up; `Dind` < 0 needs the opposite middle vectors.

**Edge effects:** DMI canting (§4); staircase edges create pinning sites and raise depinning fields (09 §5, `EdgeSmooth`); in in-plane strips edge charges pin wall ends and nucleate antivortices under drive (04).

## 6. Applied fields on static walls
- **Field along the domains** (B_z for PMA walls, B_x for head-to-head walls): pressure p = 2MsB [J/m³ = N/m²]. A 1D wall has no static solution under it. A wall that stays put under field is held by pinning, a geometric trap, finite-strip magnetostatics or the box ends.
- **In-plane field along the wall normal** (B_x for a PMA wall along y): acts like extra DMI. σ(φ) = σ_B + 2ΔK_D cos²φ − πΔMs(B_x + B_DMI)cos φ (sign of B_DMI per wall type), giving
  - cos φ = πMs(B_x + B_DMI)/(4K_D) and σ = σ_B − π²ΔMs²(B_x + B_DMI)²/(8K_D) while |B_x + B_DMI| < 4K_D/(πMs) = (2/π)B_K;
  - σ = σ_B + 2ΔK_D − πΔMs|B_x + B_DMI| (pure Néel) above that.
  - Up|down and down|up walls respond oppositely: the basis of asymmetric bubble expansion (Je et al. 2013), where the creep velocity is slowest near B_x = −B_DMI. Measured curves are often asymmetric (chiral damping, field-dependent pinning), so the minimum is an estimate of B_DMI, not a definition.
  - B_x also tilts the domains: sin θ_0 = B_x/B_K,eff with B_K,eff = 2K_eff/Ms (Stoner–Wohlfarth hard axis). Δ grows, and the wall vanishes at B_x = B_K,eff.
  - **Validity:** 1D q–φ model with fixed Δ; it neglects the domain tilt and the growth of Δ, which matter once B_x is a sizeable fraction of B_K,eff. **Misuse:** reading B_DMI from a field fit that ignores the tilt; applying it to soft in-plane walls.
- **In-plane field in the wall plane** (B_y): favours a Bloch moment along B_y, competing with the DMI. In DMI strips it tilts the wall in the film plane (Boulle et al. 2013 propose the tilt vs B_y as a measure of D; mumax3: `ext_dwtilt`, §9).
- **Head-to-head walls under a transverse field:** a field along the TW moment stabilises the TW, can convert a VW into a TW, and changes depinning and breakdown fields. Simulate rather than estimate.

## 7. Pinning
Depinning when the Zeeman force on the wall exceeds the maximum restoring force of the pinning energy E_p(q) (J per wall):
B_dep = max|dE_p/dq| / (2Ms·w·t) [T]; for an energy per area σ(q): B_dep = max|dσ/dq|/(2Ms).
- **Material step** (Ku, A, Ms or D changing at x0 over a length ℓ): σ goes from σ1 to σ2 (σ = 4√(AK_eff) − π|D|), so B_dep ~ |σ2 − σ1|/(2Ms·ℓ_eff) with ℓ_eff ≈ max(ℓ, ~2Δ). This is a rigid-profile, order-of-magnitude estimate. The barrier is met when moving into the higher-σ side.
  - Example: A = 15 pJ/m, K_eff 0.5 → 0.6 MJ/m³ (σ 11.0 → 12.0 mJ/m²), Ms = 1 MA/m, ℓ_eff = 12 nm: B_dep ~ 40 mT.
- **Constriction or notch** (width w → w − δw): the wall energy σtw is lower inside, depth ≈ σ·t·δw. B_dep ~ σ·δw/(2Ms·w·ℓ_notch) (order of). In in-plane strips notch pinning is magnetostatic (charges), so simulate it.
- **Disorder:** `ext_makegrains(grainsize, nregions, seed)` plus a per-region spread of `Ku1` (or `Aex`, `Msat`, `Dind`) of a few to ~10% gives finite depinning fields, typically strongest when the grain size is comparable to the wall width. Each seed is one realisation: average ≥ 5–10 seeds and report the spread.
- **Numerical pinning:** a cell ≳ Δ pins walls to the grid (motion in steps, a spurious depinning field that shrinks as the cell is refined); staircase edges; abrupt region interfaces. A perfect simulated strip at T = 0 has zero intrinsic pinning apart from these.
- **Typical experimental scales:** depinning fields of ~1–50 mT in sputtered PMA films and of mT order at notches in Py strips. Thermal creep below B_dep is in 04 §7 and 08-thermal.md.
- **Misuse:** comparing a T = 0 depinning field with a room-temperature coercivity (thermal activation lowers it, and the measured value depends on the field sweep rate); taking one designed defect for the whole film's disorder.

## 8. Measuring a wall width in experiments
PMA wall widths (Δ ≈ 3–10 nm) lie below most imaging resolutions, so Δ is usually inferred: Δ = √(A/K_eff) from measured A (spin waves, T_C scaling) and K_eff (hard-axis loop: B_K,eff = 2K_eff/Ms), or from a model fit of a stray-field or mobility measurement.

| Technique | Sees | Lateral resolution (order) | Wall information |
|---|---|---|---|
| Kerr microscopy | m_z or in-plane m | 0.3–1 µm | positions, velocities; never widths |
| MFM | stray-field gradient | 20–50 nm | positions; the tip can move or distort walls |
| Lorentz TEM (Fresnel, DPC) | in-plane induction through the thickness | few nm | Bloch walls visible; Néel walls in PMA films invisible without sample tilt |
| XMCD-PEEM, STXM | m along the beam | 20–50 nm | chirality by rotating the sample |
| SEMPA, SPLEEM | surface m vector | 10–20 nm | direct chirality |
| SP-STM | atomic spin contrast | atomic | full profiles in ultrathin epitaxial films |
| scanning NV magnetometry | stray field | tens of nm (stand-off) | Bloch vs Néel from the field profile (Tetienne et al. 2015) |

A measured profile is the true profile convolved with the instrument response: fit model ⊗ PSF, never quote a raw FWHM as Δ.

## 9. How a simulation measures it
- **Δ from a line cut:** relax a `TwoDomain` state, save a cut across the wall (`SaveAs(CropY(m, j, j+1), "cut")`, 02-scales.md), fit m_∥ = tanh((x − q)/Δ) over ±(5–10)Δ around the centre, away from edges and box ends. Report Δ and the definition (§1 table).
- **Δ from the table (time-resolved):** `TableAdd(Mul(m.Comp(2), m.Comp(2)))` gives ⟨m_z²⟩ over the magnet. For one straight wall across a strip of magnetic length L along the wall normal, Δ ≈ (L/2)(1 − ⟨m_z²⟩). Subtract the same quantity from a wall-free run with identical geometry to remove DMI edge canting. It breathes with the wall in dynamics.
- **πΔ and φ from ⟨m⟩:** ∫ m_⊥ dx = πΔ, so for a PMA wall L·|(⟨m_x⟩, ⟨m_y⟩)| ≈ πΔ and φ = atan2(⟨m_y⟩, ⟨m_x⟩). With DMI the strip ends and edges add canting to ⟨m_x⟩ and ⟨m_y⟩: average over a crop around the wall (`TableAdd(CropX(m, i1, i2))`, integers you declare) or subtract a wall-free reference. Snapshots of `ext_phi` and `ext_theta` give the local angles.
- **Thiele width:** from an OVF snapshot, Δ_T = 2wt/Σ_cells(∂_x m)²ΔV with finite differences of m (wall normal along x). It is the width that enters v = γΔ_T B/α (04).
- **Energy:** σ = (E_total(wall) − E_total(uniform))/(t·w), both relaxed (`Minimize()` or `Relax()`, which ignore `alpha`) on the same mesh and box. In a finite PMA strip the difference also contains the domains' changed stray-field energy, so use a strip ≫ w or integrate `Edens_total` minus its far-domain value over a crop around the wall. `E_exch` and `Edens_exch` include the DMI energy, so the exchange-only energy (2A/Δ per area for a 1D wall) is readable from them only with `Dind` = `Dbulk` = 0.
- **K_D (Bloch–Néel penalty):** E_total of a relaxed Néel wall minus that of a Bloch wall, with D = 0, divided by t·w. The Néel wall is a saddle kept only by symmetry, so check that φ stayed 0. Alternatively, measure the B_x that makes the wall fully Néel: 4K_D/(πMs) (§6).
- **Wall tilt:** `ext_dwtilt` locates the m_z sign change in rows 4 and Ny−5 of layer 0 and returns atan(Δx_index/Δy_index). It works in cell indices (correct only for square cells), has one-cell resolution, and assumes a single PMA wall. Otherwise fit the m_z = 0 contour of a snapshot.
- **Initial states:** `TwoDomain` starts with a 2-cell Gaussian wall at x = 0 (box centre), not the physical Δ. Choose the wall moment (Bloch, Néel, chirality) explicitly. Exactly symmetric states sit on saddles: perturb with `CurrentMag().Add(0.01, RandomMagSeed(1))` when the true minimum is wanted.
- **Discretisation:** cell ≤ Δ/2 for widths and energies (02-scales.md §13). The finite-difference error scales as (cell/Δ)²; halve the cell once to check. With DMI also cell ≪ 2A/D.

## Sanity checks
- Δ = √(A/K_eff): A = 15 pJ/m and K_eff = 0.3–1 MJ/m³ give 4–7 nm. Soft in-plane (Py-like) walls are wider: cores of a few l_ex plus much wider tails.
- Equipartition: excess exchange ≈ excess anisotropy energy of a 1D Bloch wall (D = 0).
- σ − 4√(AK_eff) + π|D| should be small compared with σ. If D > D_c (σ < 0), walls multiply into stripes rather than staying single.
- D_N ≈ 0.14 µ0Ms²t ≈ 0.1–0.2 mJ/m² at t ≈ 1 nm; B_DMI = D/(MsΔ) ≈ 0.1–0.3 T for D ≈ 1 mJ/m².
- Edge tilt: sin θ_e = DΔ/(2A) = (2/π)D/D_c, so θ_e < 0.69 rad for any D < D_c; a larger tilt suggests D > D_c or wrong units.
- Pressure: Ms = 1 MA/m in B = 10 mT pushes with 2×10⁴ N/m².
- A simulated wall narrower than ~2 cells, or one that moves in one-cell jumps, is under-resolved.

## Common mistakes
- Comparing Δ with a quoted πΔ (or 2Δ, or a FWHM) without converting.
- Ku in place of K_eff in Δ, σ, D_c; or entering K_eff as `Ku1` with demag on (double counting).
- Reading chirality from the sign of D across codes and papers; mixing D_N (Thiaville's "D_c") with the spiral threshold D_c; mixing H_D = (π/2)H_DMI with H_DMI.
- Setting `Dind` uniformly through a thick multilayer: interfacial DMI belongs to the interface layer (or an effective D_s/t for a thin film), not to every cell.
- Expecting a static wall in a field along the domains of a perfect strip.
- Including edge canting, end domains or a second wall in averages used for width or angle.
- Using `ext_dwtilt` with non-square cells; using `E_exch` as pure exchange with DMI on.
- Trusting the type of a relaxed head-to-head wall without comparing TW and VW energies.

## References
- A. Hubert, R. Schäfer, *Magnetic Domains*, Springer (1998).
- A. P. Malozemoff, J. C. Slonczewski, *Magnetic Domain Walls in Bubble Materials*, Academic Press (1979).
- B. A. Lilley, "Energies and widths of domain boundaries in ferromagnetics", Phil. Mag. 41, 792 (1950).
- S. V. Tarasenko, A. Stankiewicz, V. V. Tarasenko, J. Ferré, J. Magn. Magn. Mater. 189, 19 (1998).
- A. Thiaville, S. Rohart, É. Jué, V. Cros, A. Fert, EPL 100, 57002 (2012).
- S. Rohart, A. Thiaville, Phys. Rev. B 88, 184422 (2013).
- O. Boulle et al., "Domain wall tilting in the presence of the Dzyaloshinskii-Moriya interaction in out-of-plane magnetized magnetic nanotracks", Phys. Rev. Lett. 111, 217203 (2013).
- S.-G. Je et al., "Asymmetric magnetic domain-wall motion by the Dzyaloshinskii-Moriya interaction", Phys. Rev. B 88, 214401 (2013).
- S. Emori, U. Bauer, S.-M. Ahn, E. Martinez, G. S. D. Beach, Nature Mater. 12, 611 (2013).
- K.-S. Ryu, L. Thomas, S.-H. Yang, S. Parkin, Nature Nanotech. 8, 527 (2013).
- A. Mougin et al., "Domain wall mobility, stability and Walker breakdown in magnetic nanowires", EPL 78, 57007 (2007).
- R. D. McMichael, M. J. Donahue, IEEE Trans. Magn. 33, 4167 (1997).
- Y. Nakatani, A. Thiaville, J. Miltat, J. Magn. Magn. Mater. 290–291, 750 (2005).
- J. Mulkers, B. Van Waeyenberge, M. V. Milošević, Phys. Rev. B 95, 144401 (2017).
- J.-P. Tetienne et al., "The nature of domain walls in ultrathin ferromagnets revealed by scanning nanomagnetometry", Nature Commun. 6, 6733 (2015).
- A. Vansteenkiste et al., "The design and verification of MuMax3", AIP Advances 4, 107133 (2014).
