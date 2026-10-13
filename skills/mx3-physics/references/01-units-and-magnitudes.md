# Units and magnitudes

Use this chapter for converting literature values into mumax3's SI inputs, choosing starting material parameters, judging whether a field, energy or frequency has the right order of magnitude, and diagnosing unit errors in simulation output.
Script-level unit rules (cell counts versus lengths, `Msat` conventions) are in `mx3-authoring/references/units-and-scales.md` and `pitfalls.md`. They are not repeated here.

## 1. CGS → SI conversions that go wrong

All factors are exact (with µ0 = 4π×10⁻⁷ T·m/A). Multiply the CGS value by the factor.

| Quantity | CGS unit | SI unit | Factor | Worked example |
|---|---|---|---|---|
| Field strength H | Oe | A/m | 10³/(4π) = 79.58 | 100 Oe = 7.96×10³ A/m |
| Field as µ0H (what `B_ext` wants) | Oe | T | 10⁻⁴ | 100 Oe → `10e-3` |
| Flux density B | G | T | 10⁻⁴ | 1 kG = 0.1 T |
| Magnetisation M | emu/cm³ | A/m | 10³ | 800 emu/cm³ → `Msat = 800e3` |
| 4πM (often quoted as "4πMs = 10.8 kG") | G | µ0M in T | 10⁻⁴ | 4πMs = 10 kG → µ0Ms = 1.0 T → Ms = 796e3 A/m |
| Mass magnetisation | emu/g | A·m²/kg | 1 | × density (g/cm³) → emu/cm³ → × 10³ → A/m |
| Magnetic moment | emu | A·m² | 10⁻³ | 1 µemu = 10⁻⁹ A·m² |
| Energy density K | erg/cm³ | J/m³ | 0.1 | 4.5×10⁶ erg/cm³ → `Ku1 = 4.5e5` |
| Exchange stiffness A | erg/cm | J/m | 10⁻⁵ | 1.3×10⁻⁶ erg/cm → `Aex = 13e-12` |
| Areal energy (wall energy σ, D, interface K_s, interlayer J) | erg/cm² | J/m² | 10⁻³ | 1.5 erg/cm² → `Dind = 1.5e-3` |
| Volume susceptibility χ | (emu) | — | 4π | χ_SI = 4π χ_CGS |
| Demagnetising factors N | sum to 4π | sum to 1 | 1/(4π) | thin film N_z: 4π → 1 |
| Gyromagnetic ratio γ/2π | MHz/Oe | GHz/T | 10 | 2.80 MHz/Oe = 28.0 GHz/T |
| Current density | A/cm² | A/m² | 10⁴ | 10⁸ A/cm² → `J` magnitude 1e12 |

**Same-looking formulas.** In CGS, H_K = 2K/Ms gives oersted. In SI, µ0H_K = 2K/Ms gives tesla. The algebra is identical; only the system tells you the unit.
- Shape anisotropy: CGS 2πMs², SI µ0Ms²/2.
- Exchange length: CGS √(A/2πMs²), SI √(2A/µ0Ms²). These are the same number.

**Interfacial quantities quoted per area.**
- D_s = D·t (pJ/m, i.e. D in mJ/m² times t in nm). Convert with `Dind = D_s/t`.
- K_s (mJ/m²) enters as a volume term K_s/t (see 02-scales.md §4).
- With t = 1 nm, 1 pJ/m of D_s gives 1 mJ/m² of D.

## 2. H versus µ0H — what mumax3 calls "B"

- SI constitutive relation: B = µ0(H + M).
- Every mumax3 field (`B_ext`, `B_eff`, `B_demag`, `B_exch`, `B_anis`, `B_therm`, `B_custom`, `B_mel`) is **µ0 × a field H**, in tesla. None of them is the induction µ0(H + M) inside the material.
  - Example: `B_demag` in a uniformly out-of-plane thin film is ≈ −µ0Ms ẑ, not 0.
- Papers write "H = 50 mT"; they mean µ0H = 50 mT. Enter `B_ext = vector(0, 0, 50e-3)`.
- A field given in A/m converts as µ0H: 1 kA/m → 1.257 mT; 1 MA/m → 1.257 T.
- Torque columns: `torque`, `LLtorque`, `maxTorque`, `STTorque` are torque/γ, in T. Multiply by `GammaLL` to get |dm/dt| in rad/s.

## 3. mumax3 parameter units

| Identifier | Unit | Notes |
|---|---|---|
| `Msat` | A/m | per region; `m_full` = Msat·m, in A/m |
| `Aex` | J/m | inter-region value defaults to the harmonic mean; override with `ext_InterExchange` / `ext_ScaleExchange` |
| `Ku1`, `Ku2` | J/m³ | ε = −Ku1(u·m)² − Ku2(u·m)⁴; Ku1 > 0 is an easy axis along `anisU`, Ku1 < 0 an easy plane |
| `Kc1`, `Kc2`, `Kc3` | J/m³ | cubic, axes `anisC1`, `anisC2`; Kc1 > 0 gives Fe-like ⟨100⟩ easy axes, Kc1 < 0 gives Ni-like ⟨111⟩ |
| `Dind`, `Dbulk` | J/m² | not both at once (fatal error); `E_exch` and `Edens_exch` include the DMI energy |
| `alpha` | — | Gilbert damping, per region |
| `B_ext` | T | µ0H_ext; may depend on `t` |
| `J` | A/m² | current density vector |
| `GammaLL` | rad/(s·T) | **global** float, not per region; default 1.7595e11 |
| `Temp` | K | per region |
| `Pol`, `xi`, `Lambda`, `EpsilonPrime` | — | spin-torque parameters (see 11-spin-torques.md) |
| `FreeLayerThickness`, cell sizes, `MFMLift` | m | |
| `B1`, `B2` | J/m³ | magneto-elastic constants; strains `exx`… are dimensionless |
| `Run`, `FixDt`, `MinDt`, `MaxDt`, autosave periods | s | |
| `MaxErr` | — | max \|Δm\| per step (dimensionless) |
| `E_*` / `Edens_*` | J / J/m³ | total over the simulated box / per cell |

## 4. Typical material parameters (room temperature unless noted)

These are literature ranges for starting values, not values for your sample. Thin films can differ from bulk by tens of percent in Ms and by a factor of about 2 in A. The quoted A values spread widely between measurement methods.

| Material | Ms (MA/m) [µ0Ms, T] | A (pJ/m) | Anisotropy (J/m³) | α | D (mJ/m²) | Notes / source |
|---|---|---|---|---|---|---|
| Permalloy Ni₈₀Fe₂₀ | 0.70–0.86 [0.9–1.08] | 10–13 | ≈0 (induced Ku ≲ 10²–10³) | 0.006–0.01 | — | µMAG SP4 uses 0.8 / 13 |
| Co (hcp) | 1.40–1.45 [1.76–1.82] | 15–31 | Ku1 0.4–0.53 MJ/m³, c axis | ~0.005–0.02 | — | Coey; spread in A is large |
| Fe (bcc) | 1.71 [2.15] | 15–21 | Kc1 ≈ +48 kJ/m³ | ~(2–5)×10⁻³ | — | easy ⟨100⟩ |
| Ni (fcc) | 0.48–0.49 [0.61] | 3.4–9 | Kc1 ≈ −(4.5–5.7) kJ/m³ | ~0.02–0.05 | — | easy ⟨111⟩ |
| CoFeB, thick, in-plane | 0.9–1.4 [1.1–1.8] | 10–30 | small | 0.004–0.01 | — | depends on composition and anneal |
| Ta/CoFeB/MgO, t ≈ 0.8–1.3 nm | 0.8–1.2 | 10–20 | K_s ≈ 1–2 mJ/m²; K_eff ≈ +0.1–0.5 MJ/m³ | 0.01–0.03 | \|D\| ~ 0.1–0.5 | PMA from the CoFeB/MgO interface (Ikeda 2010) |
| Pt/Co/(AlOx, MgO, Ir), t ≈ 0.5–1 nm | 0.6–1.4 | 10–20 | Ku1 ≈ 0.8–1.5 MJ/m³ (K_eff ≈ 0.1–0.7) | ~0.05–0.3 | ≈1–2 measured | Sampaio 2013 model set: 0.58 / 15 / Ku 0.8 / D up to ~3, α 0.3 |
| YIG Y₃Fe₅O₁₂ | 0.14 [0.175–0.18] | 3.5–3.7 | Kc1 ≈ −0.6 kJ/m³ | 3×10⁻⁵–10⁻⁴ bulk; 10⁻⁴–10⁻³ thin film | — | lowest-damping standard |
| FeGe (B20) | 0.384 [0.48] | 8.8 | small | not well established | Dbulk ≈ 1.6 | Beg 2015 set; helix ≈ 70 nm; T_C ≈ 280 K |
| MnSi (B20) | ~0.15 (≈0.4 µB/Mn) | — | small | — | bulk | low-T only: T_C ≈ 29 K; helix ≈ 18 nm; saturation ≈ 0.6 T |
| Ferrimagnets (GdFeCo, TbCo) | net 0–0.5, tunable | few | Ku up to ~0.1–1 MJ/m³ (PMA) | effective value varies strongly | interface-dependent | sub-lattice physics: see below |
| Fe₃O₄ (magnetite) | 0.48 [0.60] | ~13 (rock-magnetism value) | Kc1 ≈ −(11–13) kJ/m³ | — | — | spinel ferrite |
| BaFe₁₂O₁₉ (M-type hexaferrite) | 0.38 [0.48] | — | Ku1 ≈ 0.33 MJ/m³ | — | — | µ0H_K ≈ 1.7 T |
| Soft spinel ferrites (MnZn, NiZn) | ~0.25–0.4 | — | small | — | — | |
| Nd₂Fe₁₄B (hard reference) | 1.28 [1.61] | ~8 | Ku1 ≈ 4.9 MJ/m³ | — | — | µ0H_K ≈ 7.6 T |
| L1₀ FePt (hard reference) | 1.14 [1.43] | ~10 | Ku1 ≈ 6.6 MJ/m³ | — | — | µ0H_K ≈ 11–12 T |

**Ferrimagnets in mumax3.** mumax3 is a single-sublattice model. A ferrimagnet near compensation enters as an effective ferromagnet with net Ms = M₁ − M₂ and with effective
- γ_eff = (M₁ − M₂)/(M₁/γ₁ − M₂/γ₂),
- α_eff = (α₁M₁/γ₁ + α₂M₂/γ₂)/(M₁/γ₁ − M₂/γ₂).

Here M₁ and M₂ are the sublattice magnetisations (A/m), γ₁ and γ₂ their gyromagnetic ratios and α₁, α₂ their damping constants.
- **mumax3 mapping:** `Msat` = M₁ − M₂; `GammaLL` = γ_eff; `alpha` = α_eff.
- **Validity:** collinear sublattices with strong antiparallel coupling, away from compensation.
- **Failure:** both quantities diverge at angular-momentum compensation (M₁/γ₁ = M₂/γ₂), and the single-sublattice model fails there.
- **Common misuse:** using the net Ms with the default `GammaLL`. Also, `GammaLL` is global, so γ_eff cannot differ between regions.

## 5. Field magnitudes (µ0H, in T)

| Source | µ0H |
|---|---|
| Earth's field | 25–65 µT |
| Oersted field of a strip line, µ0I/(2w) | 0.1–10 mT (I = 10–100 mA, w = 1–10 µm) |
| Oersted field of current in a heavy-metal layer, ≈ µ0·J·t/2 | ≈0.3 mT for J = 10¹¹ A/m², t = 5 nm |
| rf / pulse fields in FMR and spin-wave experiments | 0.01–1 mT (linear regime) |
| Lab electromagnet | up to ~1–2.5 T |
| Superconducting magnet | ~5–20 T |
| Surface of an NdFeB magnet | 0.3–0.5 T |
| Coercivity: Py film / patterned Py elements | 0.05–0.5 mT / ~1–50 mT (shape dominated) |
| Coercivity: CoFeB/MgO PMA film / Pt/Co/Pt | ~1–20 mT / ~10–100 mT |
| Coercivity: recording media / sintered NdFeB | ~0.3–1 T / ~1–3 T |
| Anisotropy field 2K/Ms: Py (induced) / Fe (cubic, 2Kc1/Ms) | ~0.3–1.5 mT / ≈56 mT |
| Anisotropy field 2K/Ms: Co / Nd₂Fe₁₄B / FePt | ≈0.6–0.75 / ≈7.6 / ≈11–12 T |
| Thin-film demagnetising field µ0Ms: YIG / Py / CoFeB / Co | 0.18 / 1.0 / 1.1–1.8 / 1.8 T |
| Exchange field in a wall, ~2A/(MsΔ²) | 0.1–a few T |

**Oersted estimates.** I is the current (A), w the strip width (m), J the current density (A/m²) and t the layer thickness (m).
- µ0I/(2w) and µ0Jt/2 are infinite-sheet limits. They hold at distances small compared with w and fall off as µ0I/(2πr) far away. Expect errors of ~10–30% near strip edges.
- **mumax3 does not compute Oersted fields from `J`.** `J` enters only the spin-transfer torques. Add the field yourself through `B_ext`, or a region- or mask-dependent `B_ext.Add(...)`.
- **Common misuse:** applying the sheet value across a whole multilayer. The field reverses sign between the two sides of the current sheet.

## 6. Gyromagnetic ratio

γ = g·µB/ħ (rad/(s·T)). The mumax3 parameter is `GammaLL`.
- g = 2 gives γ = 1.7588×10¹¹ and γ/2π = 27.99 GHz/T. The mumax3 default 1.7595×10¹¹ gives 28.00 GHz/T. The free-electron g = 2.0023 gives 28.02 GHz/T.
- Measured g is ≈2.0 for YIG and ≈2.05–2.2 for the 3d metals. For Py g ≈ 2.1 (γ/2π ≈ 29.4 GHz/T).
  - Using g = 2 then biases a fitted Ms_eff or Kittel field by several percent.
  - To model another g, set `GammaLL = g * 8.794e10`.
- Precession frequency f = (γ/2π)·B_eff. At 1 T the period is 35.7 ps; at 10 mT it is 3.6 ns.
- mumax3 integrates dm/dt = −γ/(1+α²)·[m×B + α m×(m×B)]. This is exactly the Gilbert equation with γ, so no α-correction to γ is needed when comparing to Kittel formulas.
- **Common misuse:** setting `GammaLL = 28e9`. That is in Hz/T, not rad/(s·T), and makes every frequency 2π too low.

## 7. Signs of a unit error

| Symptom in output | Likely cause | Check |
|---|---|---|
| Everything saturates along `B_ext`, `dt` falls to ~fs, spectra at THz | field in mT or Oe typed as tesla, e.g. `vector(0,0,50)` | `B_extx/y/z` columns; f ≈ 28 GHz/T × \|B\| |
| Absurd fields (10⁴–10⁶ T), "time step too small" | field in A/m typed into `B_ext` | multiply by µ0 |
| `B_exch` and `B_anis` ~10³× too large; sample stays uniform; Stoner–Wohlfarth-like square loops with coercivity ≈ 10³ × 2K/µ0Ms; tiny `dt` | `Msat = 800` (emu/cm³ read as A/m) | demag ∝ Ms² is 10⁶× too weak; l_ex is 10³× too large |
| Same, but ~10⁶× | `Msat = 1.0` meant as µ0Ms = 1 T | Ms = 1/µ0 × µ0Ms |
| PMA film turns in-plane; exchange length 4π (12.6×) shorter than expected | 4πMs (G) read as Ms (emu/cm³), i.e. Ms 4π× too big | shape term µ0Ms²/2 is 158× too large |
| Walls ~3× narrower than expected, under-resolved, jerky motion | `Aex` one decade low (1.3e-12 instead of 13e-12) | Δ ∝ √A; check `MaxAngle` |
| Walls ~30× wider, nothing non-uniform fits in the box | `Aex` 10³ high (13e-9) | l_ex ∝ √A |
| Extremely stiff exchange, `dt` ~10⁻¹⁷ s | A in erg/cm used raw (1.3e-6) | 10⁵× too large |
| Cell-scale noise, `MaxAngle` ≈ π, huge negative `E_exch`, `ext_topologicalcharge` large and non-integer | D in mJ/m² entered as J/m² (`Dind = 1.5`) | spiral period 4πA/D falls below one cell |
| Coercivity 10× and Δ √10× too small/large | K in erg/cm³ used as J/m³ (×10) | µ0H_K = 2K/Ms vs table §5 |
| Out-of-plane where in-plane is expected, or the reverse | K_eff entered as `Ku1` with demag on (shape counted twice), or Ku entered with `EnableDemag = false` | see 02-scales.md §4 |
| Current has no effect | J in A/cm² entered as A/m² (10⁴× too small) | spin-drift velocity u = PµB·J/(eMs), below |
| Run never ends | time in ns written as seconds (`Run(10)`) | `Run(10e-9)` |
| Frequencies 2π off | `GammaLL` in Hz/T, or rad/s confused with Hz in the analysis | f = ω/2π |

**Spin-drift velocity**, u = P·µB·J/(e·Ms), in m/s.
- Symbols: P is the spin polarisation (`Pol`), J the current density in A/m² (`J`), Ms the saturation magnetisation (`Msat`).
- Scale: u ≈ 36 m/s at J = 10¹² A/m², P = 0.5, Ms = 800 kA/m. Treat it as a scale for Zhang–Li torques in continuous films.
- Prefactor conventions (g/2, factors of 1 + ξ²) differ between papers and codes by up to tens of percent; see 11-spin-torques.md.
- **Common misuse:** comparing u directly with a wall velocity. The two are equal only for ξ = α, below Walker breakdown.

## Sanity checks
- µ0Ms in T is about 1 for Py, 1.8 for Co, 2.15 for Fe and 0.18 for YIG. If `Msat`·µ0 gives 10⁻³ or 10³, the unit is wrong.
- l_ex = √(2A/µ0Ms²) should be 3–10 nm for 3d metals and ~17 nm for YIG. Values in µm or Å signal a unit error in A or Ms.
- 2K/Ms (T) should match the anisotropy fields in §5, and Ms·|B_ext| (J/m³) should be comparable to K and µ0Ms²/2 when the field matters.
- Precession: 28 GHz/T × B_eff. A 10 GHz mode needs B_eff ≈ 0.36 T, or Kittel enhancement from µ0Ms.
- D/(√(AK)) should be below about 4/π for an isolated-texture regime. A ratio ≫ 1 signals a D unit slip (02-scales.md §6).

## How a simulation measures it
- Table columns carry units in the header, e.g. `# t (s)  mx ()  my ()  mz ()  B_extx (T)`. Values are written in float32 (about 7 significant digits); `t` is written in full precision.
- `m.Average()` and table averages are taken over magnetic cells only, weighted by the `geom` fill fraction. Multiply by Ms (or use `m_full`) to get A/m. The average Ms·V needs the magnetic volume, not the box volume.
- Check inputs at runtime: `Print(Msat.GetRegion(1))` and `TableAdd(B_ext)`. A single `Print(B_anis.Average())` or `Print(maxTorque)` right after setup exposes a 10³ error before a long run.
- Energies: `E_*` in J over the box; `Edens_*` in J/m³ per cell. Divide by the magnetic volume or the wall area before comparing with literature J/m³ or J/m² (02-scales.md §9).
- Frequencies from an FFT of table data are in Hz when the time axis is in s. Report f, not ω.

## Common mistakes
- Reading "4πMs" or "µ0Ms" as Ms; reading "Ms in emu/g" as emu/cm³ (forgetting density).
- Converting Oe to A/m and then entering A/m into `B_ext`. `B_ext` wants µ0H in T, so Oe × 10⁻⁴.
- Treating "D_s" (pJ/m) or "K_s" (mJ/m²) as volume quantities without dividing by the thickness.
- Using bulk Ms and A for ultrathin films. Interface and dead-layer effects reduce both, so state the assumption.
- Comparing a mumax3 `B_demag` with a measured induction B (they are different quantities).
- Setting `GammaLL` in Hz/T; assuming `GammaLL` can differ per region.

## References
- J. M. D. Coey, *Magnetism and Magnetic Materials*, Cambridge University Press (2010): unit conventions, material tables.
- A. Hubert, R. Schäfer, *Magnetic Domains*, Springer (1998): material parameters, CGS/SI.
- A. Aharoni, *Introduction to the Theory of Ferromagnetism*, 2nd ed., Oxford University Press (2000).
- A. Vansteenkiste et al., "The design and verification of MuMax3", AIP Advances 4, 107133 (2014).
- µMAG Standard Problem #4, NIST Center for Theoretical and Computational Materials Science (permalloy reference parameters).
- S. Ikeda et al., "A perpendicular-anisotropy CoFeB–MgO magnetic tunnel junction", Nature Materials 9, 721 (2010).
- J. Sampaio, V. Cros, S. Rohart, A. Thiaville, A. Fert, "Nucleation, stability and current-induced motion of isolated magnetic skyrmions in nanostructures", Nature Nanotechnology 8, 839 (2013).
- M. Beg et al., "Ground state search, hysteretic behaviour, and reversal mechanism of skyrmionic textures in confined helimagnetic nanostructures", Scientific Reports 5, 17137 (2015): FeGe parameters.
- K.-J. Kim et al., "Fast domain wall motion in the vicinity of the angular momentum compensation temperature of ferrimagnets", Nature Materials 16, 1187 (2017).
