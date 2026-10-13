# Characteristic scales: lengths, energies, times

Use this chapter for estimating lengths, energies and times before a run, choosing the cell size, deciding the regime from dimensionless numbers, and checking whether a simulated width, energy or period is plausible.
It gives scales only. Walls, skyrmions, spin waves, reversal and thermal physics are treated in chapters 03–08; numerics in 09.

**Notation (SI):** Ms = `Msat` (A/m); A = `Aex` (J/m); Ku = `Ku1` (J/m³); D = `Dind`/`Dbulk` (J/m²); α = `alpha`; γ = `GammaLL` (rad/(s·T)); t = film thickness (m); Kd = µ0Ms²/2 (J/m³).
Fields are written as B = µ0H in T, as `B_ext` takes them.

## 1. Exchange length
l_ex = √(2A/(µ0Ms²)) = √(A/Kd) [m]
- **Meaning:** the length below which exchange beats magnetostatics. It sets vortex-core size, the cores of Néel walls in soft films, and the mesh for soft magnets.
- **Typical values:** 3–6 nm for 3d metals (Py 5.7, Co 4.9, Fe 3.4; table in `units-and-scales.md`); ≈17 nm for YIG; tens of nm for low-Ms ferrimagnets or near T_C.
- **Validity:** a scale, not a size. Real features are O(1)–O(few) × l_ex; vortex-core diameters in thin Py films are ~10–20 nm.
- **Common misuse:**
  - Conventions differ by √2. Some authors write √(A/(µ0Ms²)) (Abo et al. 2013); the CGS form √(A/2πMs²) equals the SI form above.
  - Using l_ex as the mesh criterion when Q > 1. Δ is then smaller and governs the mesh (§2, §12).

## 2. Wall-width parameter
Δ = √(A/K) [m]

- **Which K:** Ku for a bulk uniaxial magnet; K_eff = Ku − µ0Ms²/2 for an ultrathin PMA film (t ≪ Δ). No single Δ exists for in-plane Néel walls in soft films: their cores are a few l_ex wide with long tails (Hubert & Schäfer).
- Profile: θ(x) = 2 arctan(exp(x/Δ)), so m along the easy axis is cos θ = −tanh(x/Δ) and the transverse component is sech(x/Δ).
- Δ = l_ex/√Q.
- **Width conventions:** the Lilley width πΔ (tangent at the centre) is often quoted as "the wall width". Check which one a paper uses before comparing.
- **Typical values:** 1–2 nm in hard magnets (Nd₂Fe₁₄B ≈ 1.3 nm, FePt ≈ 1.2 nm); 5–15 nm in PMA thin films; ≈6–8 nm in bulk Co.
- **Validity:** 1D wall, uniaxial K. In thin films with demagnetisation and DMI the simulated Δ typically differs by ~10–20% from √(A/K_eff), depending on wall type and field.
- **Common misuse:** using Ku instead of K_eff for ultrathin films, which makes Δ too small by √(Ku/K_eff). Comparing Δ with a quoted πΔ.

## 3. Quality factor
Q = 2Ku/(µ0Ms²) = Ku/Kd [—]

- **Meaning:** Q ≪ 1 soft (demagnetisation dominates: flux closure, vortices); Q > 1 perpendicular magnetisation survives the thin-film shape anisotropy (K_eff > 0); Q ≫ 1 hard.
- **Typical values:** Py ~10⁻³; bulk Co ≈ 0.35; Pt/Co and CoFeB/MgO ultrathin films ≈ 1.1–2; BaFe₁₂O₁₉ ≈ 3.6; Nd₂Fe₁₄B ≈ 4.8; FePt ≈ 8.
- **Common misuse:** judging a film with bulk Ku when its PMA is interfacial. Include K_s/t (§4).

## 4. Thin-film shape anisotropy and K_eff
K_eff = K_v + K_s/t − µ0Ms²/2 [J/m³]

Symbols: K_v is the volume anisotropy (J/m³) and K_s the interface anisotropy (J/m²).
- K_eff > 0 gives a perpendicular easy axis.
- Reorientation thickness: t_c = K_s/(µ0Ms²/2 − K_v).
- Hard-axis saturation field of a PMA film: B_sat = 2K_eff/Ms (T).

**mumax3 mapping.**
- With demagnetisation on (the default), mumax3 supplies the −µ0Ms²/2 itself. Enter `Ku1 = K_v + K_s/t`, or from a measured K_eff, `Ku1 = K_eff + µ0Ms²/2`.
- Enter `Ku1 = K_eff` only with `EnableDemag = false` (local thin-film approximation).
- **Validity:** exact for a uniform state of an infinite film. Patterned elements have N_z < 1, so the shape term is µ0Ms²(N_z − N_x)/2, smaller than in a film.
- **Check:** compare E_total/V of `Uniform(0,0,1)` and `Uniform(1,0,0)` with no relaxation. This gives the discretised K_eff including shape (see "How a simulation measures it").
- **Common misuse:** entering K_eff as `Ku1` with demag on. This double-counts the shape anisotropy and can flip the easy axis.

## 5. Wall energy
σ = 4√(AK) [J/m²], with K = Ku in bulk or K_eff in ultrathin films.
- **With interfacial DMI** (Néel wall of the favoured chirality): σ = 4√(AK_eff) − π|D|.
- **Bloch versus Néel in ultrathin films:** the wall's own shape anisotropy is K_D ≈ (t ln2/(πΔ))·µ0Ms²/2 (Tarasenko et al. 1998). The DMI that makes the wall fully Néel is D_N = (2 ln2/π²)·µ0Ms²·t. For Ms = 1.0 MA/m and t = 0.8 nm this is ≈0.14 mJ/m², so a few tenths of mJ/m² already fixes the chirality.
- **Typical values:** 1–10 mJ/m² in PMA films; ~10–15 mJ/m² in bulk Co; ≈25 mJ/m² in Nd₂Fe₁₄B.
- **Validity:** 1D, uniaxial, no in-plane field. Wall demagnetisation raises the simulated value by a few percent to ~20% in thin films.
- **Common misuse:** dividing a simulated energy difference by the wrong area (it is t × wall length). Forgetting that σ < 0 once D > D_c (§6).

## 6. Critical DMI (interfacial, thin film)
D_c = 4√(AK_eff)/π [J/m²], used with `Dind`.
- **Below D_c:** the uniform state is the ground state, and isolated skyrmions and chiral walls are metastable.
- **Above D_c:** a cycloid or labyrinth is the zero-field ground state (σ < 0). The dimensionless ratio is κ = D/D_c.
- **Typical value:** A = 15 pJ/m and K_eff = 0.4 MJ/m³ give D_c ≈ 3.1 mJ/m².
- **Validity:** 1D wall with the local K_eff. Long-range stray fields favour domains, so extended films can turn multidomain below D_c. Treat D_c as accurate to tens of percent.
- **Bulk DMI** (`Dbulk`, B20 compounds) has no threshold without anisotropy: the helix is always the ground state (§8).
- **Common misuse:** using Ku instead of K_eff; using D_c alone to predict skyrmion stability in finite elements or under field.

## 7. Single-domain and texture-type sizes
**Hard magnets (Q ≳ 1), sphere:** d_c ≈ 72√(AK)/(µ0Ms²).
- This is a Kittel-type balance of wall energy against the saved magnetostatic energy.
- It gives ≈200 nm for Nd₂Fe₁₄B, ~70–100 nm for Co and ~20 nm for Fe.
- Accurate to about a factor of 2. Do not use it for soft magnets.

**Soft magnets (Q ≪ 1):** coherent rotation holds only below a radius of a few l_ex.
- Brown/Aharoni nucleation analysis: R_coh ≈ 3.6 l_ex for a sphere and ≈ 2.6 l_ex for an infinite cylinder.
- Above that radius, curling or vortex states form.

**Thin elements:**
- Py disks with t ≈ 10–20 nm hold a vortex above a diameter of roughly 100–200 nm, with the boundary depending on thickness (Cowburn et al. 1999).
- Strips: transverse head-to-head walls for w·t ≲ ~61–64 l_ex², vortex walls above (McMichael & Donahue 1997 give t·w = 128A/(µ0Ms²) = 64 l_ex²; later refinements put the boundary near 61 l_ex²).
- Decide by comparing E_total of separately relaxed candidate states.

## 8. Spiral, skyrmion and bubble scales
**Helix/cycloid period:** L_D = 4πA/D, wave number q = D/(2A).
- Applies to bulk DMI, or to interfacial DMI with D > D_c and weak anisotropy.
- FeGe (A = 8.8 pJ/m, D = 1.58 mJ/m²): ≈70 nm.
- Validity: exact for the zero-field, zero-anisotropy 1D helix. Uniaxial anisotropy, applied field and demagnetisation lengthen and distort it.
- Common misuse: a periodic box that is not a multiple of L_D strains the spiral (09 §5).

**Saturation field of a bulk chiral magnet** (cone → field-polarised, internal field): B_D = D²/(2A·Ms) [T].
- FeGe: ≈0.37 T.
- Add µ0N·Ms to compare with the applied field of a sample with demagnetising factor N.
- Validity: bulk, no anisotropy. Thin B20 films deviate through surface twists and induced anisotropy.
- Common misuse: comparing B_D directly with an applied field.

**DMI length:** 2A/D = 1/q. The cell must be ≪ 2A/D.

**Isolated interfacial skyrmion radius:**
- Much smaller than Δ for D ≪ D_c: R ≈ Δ·D/D_c at zero field (Wang et al. 2018; compact, and it needs field or anisotropy to exist).
- Grows and diverges as D → D_c in zero field; field shrinks it. Typically 5–100 nm.
- No universal closed form; see 05-skyrmions-vortices.md.

**Belavin–Polyakov energy:** 8πAt [J], the exchange energy of an ideal skyrmion in a film of thickness t.
- A = 15 pJ/m, t = 1 nm gives 3.8×10⁻¹⁹ J ≈ 90 kBT at 300 K.
- Collapse barriers are fractions of this.

**Dipolar (bubble) length:** l_c = σ/(µ0Ms²) [m].
- Bubble and stripe sizes in films scale with l_c (Thiele theory). This holds for Q > 1 films and is order-of-magnitude only.
- In ultrathin films the stripe period grows like t·exp(π·l_c/(2t)) (Kaplan & Gehring 1993). Small changes in σ (hence in D or K) change the domain size by orders of magnitude, up to µm–mm.
- Common misuse: a box smaller than the domain period forces an artificial state.

## 9. Times
- **Precession:** f = (γ/2π)·B_eff, at 28 GHz/T.
- **Kittel, in-plane film:** f = (γ/2π)√(B(B + µ0M_eff)), with µ0M_eff = µ0Ms − 2Ku/Ms (more in 06-spin-waves-fmr.md).
  - Validity: uniform mode, extended film, small amplitude, B along an in-plane easy direction. Typically good to a few percent in mumax3 with PBC.
  - Common misuse: using Ms instead of M_eff for films with perpendicular anisotropy.
- **Intrinsic time:** t₀ = 1/(γµ0Ms). Py ≈ 5.7 ps; YIG ≈ 32 ps.
- **Damping time** (amplitude e-folding) for circular precession: τ = (1 + α²)/(αω) ≈ 1/(αω).
  - For the uniform mode of an in-plane film: 1/τ = αγ(B + µ0M_eff/2).
  - Example: Py, α = 0.01, B = 50 mT gives τ ≈ 1.0 ns. The circular formula at the same f (≈6.4 GHz) would give 2.5 ns: ellipticity matters.
  - Ring-down takes ~3–5 τ.
- **Stiffest grid mode:** B_max ≈ (2A/Ms)·4d/Δx², where d is the number of finely discretised dimensions.
  - This field limits the explicit time step to ~1/(γB_max).
  - Py, Δx = 4 nm, 2D: B_max ≈ 16 T, so 1/(γB_max) ≈ 0.35 ps.
  - Halving Δx makes the step ~4× smaller (09 §2).
- **Thermal activation:** τ = τ₀·exp(E_b/kBT), with τ₀ conventionally ~0.1–1 ns.
  - Direct simulation (≲ 1 µs) only sees barriers of ≲ 5–10 kBT.
  - Larger barriers need rate theory or path methods (08-thermal.md).

## 10. Spin-wave length scales
- **Exchange–dipolar crossover:** (2A/Ms)k² = µ0Ms at k = 1/l_ex, i.e. λ = 2πl_ex. That is ≈36 nm in Py and ≈108 nm in YIG. Exchange dominates at shorter wavelengths.
- **Herring–Kittel (bulk):**
  - ω² = ω_k(ω_k + ω_M sin²θ_k), with ω_k = γ(B_i + (2A/Ms)k²), ω_M = γµ0Ms, and θ_k the angle between k and m.
  - Validity: unbounded medium. Common misuse: applying it to films, which need Kalinikos–Slavin, because dipolar terms ∝ kt matter for kt ≲ 1.
- **Damon–Eshbach group velocity** at small k: v_g ≈ ω_M²t/(4ω). For Py with t = 20 nm at 10 GHz, ≈2.5 km/s.
- **Attenuation length:** L = v_g·τ. Typically µm in metals and mm in YIG.
- **Grid dispersion:** the finite-difference Laplacian has relative error ≈ (kΔx)²/12.
  - Use ≥ 10–20 cells per wavelength.
  - The grid cutoff is k_max = π/Δx.

## 11. Energy densities and how to compare energies
**Scales (J/m³):**
- Demagnetisation, Kd = µ0Ms²/2: Py 0.40 M; Co 1.3 M; Fe 1.84 M; YIG 0.012 M.
- Exchange in a texture of size L: ≈ A/L² (Py, L = 10 nm: 1.3×10⁵).
- DMI: ≈ D/L.
- Zeeman: Ms·B (Py at 10 mT: 8×10³).
- Thermal energy per cell: kBT/V_cell (300 K, (4 nm)³: 6.5×10⁴), comparable to Kd. Small cells fluctuate strongly.

**Comparing energies:**
- `E_*` is J over the simulated box, or per periodic box with PBC. `Edens_*` is J/m³ per cell.
- **Per volume:** divide by the magnetic volume (magnetic cells × cell volume), not the box volume.
- **Per area (walls, interfaces):** (E_state − E_ref)/(t × wall length).
- **Per object (skyrmion, vortex):** E_state − E_ref in J, quoted in kBT or 8πAt.
- Always difference two states on the **same mesh and box**, so discretisation errors cancel.
- Differences below ~10⁻⁶ × |E_total| are at the float32 noise floor (09 §2). Shrink the box around the object, or integrate `Edens_total` over a crop.

## 12. Dimensionless numbers that decide the regime
| Number | Definition | Regime |
|---|---|---|
| Q | 2Ku/(µ0Ms²) | ≪1 soft; >1 PMA film possible; ≫1 hard |
| κ | D/D_c = πD/(4√(AK_eff)) | <1 isolated textures metastable; >1 spirals or labyrinths |
| t/l_ex, t/Δ | thickness / length | ≲1: m uniform through t (one cell layer may do); ≫1: 3D textures, surface twists |
| L/l_ex, L/Δ | lateral size / length | small: single-domain, coherent; large: walls, vortices, domains |
| h | Ms·B/(2K) = B/B_K | Stoner–Wohlfarth switching at h = 1 (easy axis), 0.5 (at 45°) |
| α | damping | ≪1: precession, ringing, Walker breakdown; ≳0.5: overdamped |
| ξ/α | non-adiabatic / damping | sets current-driven wall velocity relative to u (11) |
| E_b/kBT | barrier / thermal | ≥40–60: long-term stable; ≲5–10: switches within a simulation |
| kΔx; k·l_ex | grid / exchange | ≪1 needed; ≶1 separates dipolar and exchange spin waves |

## 13. Cell-size requirements
| Situation | Requirement | Note |
|---|---|---|
| Soft, demagnetisation dominated | Δx ≤ l_ex | linter `R-LEX`: WARN > l_ex, ERROR > 2 l_ex |
| Walls, Q ≳ 1 | Δx ≤ Δ minimum; ≲ Δ/2 for wall energies, velocities, depinning | coarser grids pin walls to the lattice |
| DMI textures | Δx ≪ 2A/D; ≥ 10 cells per spiral period 4πA/D | |
| Skyrmions | ≥ ~10 cells across the diameter | topological charge must stay integer |
| Vortex cores | ≥ 3–5 cells across the core | |
| Spin waves | ≥ 10–20 cells per shortest λ | error ≈ (kΔx)²/12 |
| Thickness | one cell if t ≲ l_ex, Δ and no through-thickness texture | otherwise resolve t like a lateral length |
| Any texture | `MaxAngle` ≲ 0.3–0.5 rad (rule of thumb) | refine where it is exceeded |

The convergence test (09 §8) is the arbiter, not these rules.

## Sanity checks
- Δ = l_ex/√Q. If simulated walls are much narrower than Δ, suspect the units of A or K, or a cell coarser than Δ.
- If K_eff < 0 from §4 yet the simulated film is perpendicular (or the reverse), check how `Ku1` was entered with demagnetisation on.
- σ − 4√(AK_eff) + π|D| should be small compared with σ. If D > D_c, expect spirals, not a single wall.
- f ≈ 28 GHz/T × B_eff; uniform-mode ring-down time ≈ 1/(α·2πf), shorter for in-plane films.
- Simulated feature sizes should be O(1–10) × l_ex or Δ. A texture one cell wide is a numerical artefact.

## How a simulation measures it
- **Δ:** relax a `TwoDomain` state. Save a line cut, e.g. `SaveAs(CropY(m, j, j+1), "cut")` with j the middle row index (declare it yourself, e.g. `j := 16`), and fit m_z = tanh((x − x₀)/Δ) away from the edges. Report Δ and whether you mean Δ or πΔ.
- **σ:** (E_total with wall − E_total uniform)/(t·w). Both states use the same mesh and box, and are relaxed with `Minimize()` or `Relax()`.
- **K_eff:** E_total/V of `Uniform(1,0,0)` minus that of `Uniform(0,0,1)`, with no relaxation. Alternatively, the hard-axis loop gives B_sat = 2K_eff/Ms.
- **D_c:** sweep `Dind` and watch for σ → 0, or for walls multiplying spontaneously in a strip.
- **Domain or spiral period:** 2D FFT of an m_z snapshot. The box must hold several periods; with PBC, scan the box length (09 §5).
- **Frequencies and damping times:** FFT of table data after a small kick, or a fit of an exponential envelope. Sampling rules are in 09 §7.

## Common mistakes
- Mixing Δ, πΔ and other width definitions; mixing the √2 conventions of l_ex.
- Using Ku where K_eff belongs (Δ, σ, D_c), or entering K_eff as `Ku1` with demagnetisation on.
- Quoting σ or skyrmion energies from boxes of different size or cell size.
- Treating closed forms as accurate below ~10–20% in real geometries with edges and stray fields.
- Choosing the cell from l_ex alone in a PMA or DMI system, where Δ and 2A/D are smaller.

## References
- A. Hubert, R. Schäfer, *Magnetic Domains*, Springer (1998).
- A. Aharoni, *Introduction to the Theory of Ferromagnetism*, 2nd ed., Oxford University Press (2000).
- J. M. D. Coey, *Magnetism and Magnetic Materials*, Cambridge University Press (2010).
- W. F. Brown Jr., *Micromagnetics*, Interscience (1963).
- C. Kittel, "Physical theory of ferromagnetic domains", Rev. Mod. Phys. 21, 541 (1949).
- G. S. Abo et al., "Definition of magnetic exchange length", IEEE Trans. Magn. 49, 4937 (2013).
- A. Thiaville, S. Rohart, É. Jué, V. Cros, A. Fert, "Dynamics of Dzyaloshinskii domain walls in ultrathin magnetic films", EPL 100, 57002 (2012).
- S. Rohart, A. Thiaville, "Skyrmion confinement in ultrathin film nanostructures in the presence of Dzyaloshinskii–Moriya interaction", Phys. Rev. B 88, 184422 (2013).
- S. V. Tarasenko, A. Stankiewicz, V. V. Tarasenko, J. Ferré, "Bloch wall dynamics in ultrathin ferromagnetic films", J. Magn. Magn. Mater. 189, 19 (1998).
- A. N. Bogdanov, A. Hubert, "Thermodynamically stable magnetic vortex states in magnetic crystals", J. Magn. Magn. Mater. 138, 255 (1994).
- A. A. Belavin, A. M. Polyakov, "Metastable states of two-dimensional isotropic ferromagnets", JETP Lett. 22, 245 (1975).
- B. Kaplan, G. A. Gehring, "The domain structure in ultrathin magnetic films", J. Magn. Magn. Mater. 128, 111 (1993).
- R. D. McMichael, M. J. Donahue, "Head to head domain wall structures in thin magnetic strips", IEEE Trans. Magn. 33, 4167 (1997).
- R. P. Cowburn et al., "Single-domain circular nanomagnets", Phys. Rev. Lett. 83, 1042 (1999).
- C. Herring, C. Kittel, "On the theory of spin waves in ferromagnetic media", Phys. Rev. 81, 869 (1951).
- B. A. Kalinikos, A. N. Slavin, "Theory of dipole-exchange spin wave spectrum for ferromagnetic films with mixed exchange boundary conditions", J. Phys. C 19, 7013 (1986).
- D. D. Stancil, A. Prabhakar, *Spin Waves: Theory and Applications*, Springer (2009).
