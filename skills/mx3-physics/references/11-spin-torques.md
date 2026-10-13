# Spin-transfer and spin–orbit torques

Use this chapter for current-driven magnetization dynamics in mumax3: the Zhang–Li torque (current in the film plane), the Slonczewski torque (current through a fixed layer), spin–orbit torques from a heavy-metal layer, current-driven walls and skyrmions, the Oersted and Joule-heating confounders, and the sign conventions that decide whether a simulated current means what you think.
Fields are B = µ0H in tesla unless written H (A/m); γ = `GammaLL` = 1.7595e11 rad/(s·T); e > 0 is the elementary charge. Domain-wall statics and field-driven motion are in the domain-wall chapters, skyrmion statics in the skyrmion chapter.

## 1. mumax3 inputs (read from the mumax3 3.12 source: engine/torque.go, cuda/zhangli2.cu, cuda/slonczewski2.cu)

| identifier | meaning | unit | default | used by |
|---|---|---|---|---|
| `J` | charge current density, conventional current (electrons flow along −J); an Excitation | A/m² | 0 | Zhang–Li: all components; Slonczewski: J_z only |
| `Pol` | spin polarization P | – | **1** | both |
| `xi` | non-adiabaticity β (called ξ in mumax3) | – | **0** | Zhang–Li |
| `FixedLayer` | polarizer direction p, normalised internally; the zero vector switches Slonczewski off | – | 0 | Slonczewski |
| `FixedLayerPosition` | `FIXEDLAYER_TOP` (fixed layer at larger z) or `FIXEDLAYER_BOTTOM` (reverses the torque sign) | – | TOP | Slonczewski |
| `Lambda` | asymmetry parameter Λ | – | 1 | Slonczewski |
| `EpsilonPrime` | secondary (field-like) coefficient ε′ | – | 0 | Slonczewski |
| `FreeLayerThickness` | free-layer thickness d; 0 means the whole mesh thickness Nz·cz | m | 0 | Slonczewski |
| `DisableZhangLiTorque`, `DisableSlonczewskiTorque` | switch one term off | bool | false | – |
| `STTorque` | spin-transfer torque/γ (output) | T | – | – |

- Zhang–Li acts whenever J ≠ 0; Slonczewski acts in addition when `FixedLayer` ≠ 0. Both read the same `J` and `Pol`.
- J ≠ 0 with `Pol` = 0 everywhere aborts the run ("spin polarization should not be 0"). Switch torques off with J = 0 or the Disable flags.
- `J` enters only these torques: it creates no Oersted field, no Joule heat and no current redistribution around holes or notches. It is uniform unless you shape it: `J.SetRegion(1, vector(0, 0, 1e11))`, `J.Add(LoadFile("j.ovf"), 1)`, or a time dependence such as `J = vector(J0*sin(2*pi*f*t), 0, 0)`.
- Neither term solves spin accumulation or spin diffusion. P, β, Λ, ε′ and θ_SH are phenomenological inputs.

## 2. Zhang–Li torque (current in the plane)

Gilbert form: ∂m/∂t = −γ m×B_eff + α m×∂m/∂t − (u·∇)m + β m×(u·∇)m, with u = P g µB J_e/(2e Ms) (m/s) pointing along the electron drift (J_e: electron-flow current density, |J_e| = |J|).

- mumax3 computes u = −µB·`Pol`·`J`/(e·`Msat`·(1 + `xi`²)): g = 2 is built in, u is antiparallel to `J`, and the factor 1/(1 + ξ²) of the original Zhang–Li paper is kept (< 1 % for ξ ≤ 0.1). If `GammaLL` is changed, u scales with `GammaLL`/1.7595e11, consistent with u ∝ g.
- Size: µB/e = 5.79e-5 m²/s, so u = 5.79e-5·P·J/Ms. Ms = 8e5 A/m, P = 1, J = 1e12 A/m² → u = 72 m/s (36 m/s at P = 0.5).
- The adiabatic term translates a texture along u. The β term acts like an effective field −(β/γ)(u·∇)m; on a wall of width Δ it is an easy-axis field βu/(γΔ).
- Typical values: P ≈ 0.4–0.7 (permalloy ≈ 0.5–0.7 from spin-wave Doppler measurements); β of order 0.01–0.1, comparable to α or a few times larger. Published β values scatter widely.
- Validity: adiabatic limit (texture lengths ≫ the ~1 nm spin-precession and spin-diffusion scales), smooth textures, a prescribed J(r).
- Discretisation: mumax3 takes central differences of m along J. Walls must span several cells (cell ≤ l_ex and ≪ Δ), or they pin on the grid.

## 3. Current-driven walls: 1D model with spin-transfer torque (Thiaville et al. 2005)

q wall position, ψ wall-moment angle, Δ wall width, B_a applied easy-axis field (T), B_K = µ0H_K the wall's hard-axis (Bloch–Néel) anisotropy field (T). For one wall polarity:

    ψ̇ + α q̇/Δ = γB_a + βu/Δ
    q̇/Δ − α ψ̇ = (γB_K/2)·sin 2ψ + u/Δ

| case | result |
|---|---|
| below Walker, B_a = 0 | v = (β/α)u; steady tilt sin 2ψ = 2(β/α − 1)u/(γΔB_K) |
| below Walker, with field | v = (γΔ/α)B_a + (β/α)u: the current adds an equivalent field βu/(γΔ) |
| Walker current | u_W = αγΔB_K/(2·abs(β − α)); none for β = α (then v = u at every u) |
| far above Walker | ⟨v⟩ → (1 + αβ)u/(1 + α²) ≈ u |
| β = 0: intrinsic pinning | no steady motion below u_c = γΔB_K/2: the wall moves (Δ/2α)·arcsin(u/u_c), then stops; above u_c, ⟨v⟩ = √(u² − u_c²)/(1 + α²) |
| transient | ψ settles in τ ≈ (1 + α²)/(αγB_K): 5.7 ns for α = 0.02, B_K = 50 mT |

- Example: Δ = 20 nm, B_K = 50 mT → u_c = 88 m/s, i.e. J ≈ 1.2e12 A/m² at P = 1, Ms = 8e5 A/m. Without β, walls in such strips need very large currents.
- The model is quantitative for narrow strips and thin films with rigid walls. Wide strips show wall tilting and vortex or antivortex nucleation above Walker.

## 4. Slonczewski torque (current perpendicular to the plane)

With p = `FixedLayer`/|`FixedLayer`|, d = `FreeLayerThickness`, P = `Pol`, Λ = `Lambda`, ε′ = `EpsilonPrime`, and s = +1 for `FIXEDLAYER_TOP` or −1 for `FIXEDLAYER_BOTTOM`:

    β_J = s·ħJ_z/(e·Ms·d)   (T)          ε = P·Λ² / [(Λ² + 1) + (Λ² − 1)(m·p)]
    Gilbert form:   ∂m/∂t|ST = γβ_J [ε m×(p×m) + ε′ p×m]
    mumax3 adds the LL form:   [β_J(ε + αε′) m×(p×m) + β_J(ε′ − αε) p×m] / (1 + α²)

- Λ = 1: ε = P/2 at every angle. Damping-like field B_DL = ħPJ/(2e·Ms·d); field-like field B_FL = ħε′J/(e·Ms·d). Λ > 1 makes the torque Λ² times stronger at antiparallel than at parallel alignment.
- Sign: J_z > 0 with `FIXEDLAYER_TOP` means electrons flow along −z, from the fixed layer into the free layer, and pulls m toward p (parallel). J_z < 0 favours antiparallel. `FIXEDLAYER_BOTTOM` reverses both.
- Only J_z enters. An in-plane J with a `FixedLayer` gives no Slonczewski torque (only a Zhang–Li one).
- The torque is spread uniformly over d (thin free layer, d ≲ l_ex). Real spin-transfer torque is absorbed within ~1 nm of the interface. For a thick free layer resolved in several cells, put J only in the interface cell layer and set `FreeLayerThickness` to that layer's thickness.
- If the fixed layer or other magnetic layers are in the mesh, restrict J to the free layer (`J.SetRegion`) and set `FreeLayerThickness`. Cells with Msat = 0 receive no torque but count in the default thickness.
- Macrospin instability threshold (T = 0, Λ = 1): β_J·P/2 = α × (stiffness field).
  - Perpendicular free layer: J_c0 = 2αe·Ms·d·(B_K,eff + B_z)/(ħP), with B_K,eff = 2K_u/Ms − µ0Ms. α = 0.01, Ms = 1e6 A/m, d = 1.5 nm, B_K,eff = 0.2 T, P = 0.6 → 1.5e10 A/m².
  - In-plane free layer: J_c0 = 2αe·Ms·d·(B_x + B_K + µ0Ms/2)/(ħP). Ms = 8e5 A/m, d = 3 nm, P = 0.5, α = 0.01 → 7e10 A/m².
  - Nanosecond pulses need several J_c0; long pulses switch below J_c0 by thermal activation.

## 5. Spin–orbit torques (current in an adjacent heavy metal)

The spin Hall effect converts the charge current J_c in the heavy metal (HM) into a spin current, θ_SH = (2e/ħ)·j_s/j_c (an effective value that includes interface transparency). The spin polarization σ is perpendicular to J_c and to the interface normal n: σ = ±(n × Ĵ_c), e.g. ±ŷ for J_c ∥ x̂ and n ∥ ẑ.

- Damping-like: ∂m/∂t = γB_DL m×(σ×m), equivalent to the field B_DL(m×σ). B_DL = ħθ_SH·J_c/(2e·Ms·d) (T), d = thickness of the magnet.
- Field-like: −γB_FL m×σ, equivalent to a uniform field B_FL·σ. It is indistinguishable from an in-plane applied field ⊥ J_c, including the HM's own Oersted field (§7).
- Field per current density: B_DL/J_c = 3.29e-16·θ_SH/(Ms·d) T per A/m² (ħ/2e = 3.29e-16 T·m²) → 3.3 mT per 1e11 A/m² for θ_SH = 0.1, Ms = 1e6 A/m, d = 1 nm.
- θ_SH, effective, order of: Pt +0.05 to +0.1; β-Ta −0.12 to −0.15; β-W ≈ −0.3. It grows with HM thickness roughly as 1 − sech(t_HM/λ_sf). The ratio B_FL/B_DL is stack-dependent (from ≪ 1 to ≳ 1): take it, with its sign, from a measurement on the same stack (harmonic Hall, spin-torque FMR).
- Validity: thin magnet (≲ a few nm); the interfacial torque is treated as uniform over d.
- Deterministic switching of a perpendicular magnet needs a symmetry-breaking in-plane field along J_c; the polarity reverses with that field and with the sign of θ_SH.

mumax3 has no SOT keyword. Two equivalent representations, both shown for Ms = 1e6 A/m, d = 1 nm, J_c = 1e11 A/m², θ_SH = 0.1, B_FL/B_DL = 0.3:

```
// (a) Slonczewski term with the polarizer along sigma; J_z only carries the HM current density
DisableZhangLiTorque = true          // keep the fictitious J_z out of Zhang-Li
Pol          = 0.1                   // |theta_SH|
Lambda       = 1                     // angle-independent torque
EpsilonPrime = 0.015                 // (B_FL/B_DL)*Pol/2, sign included
FixedLayer   = vector(0, 1, 0)       // sigma; flip it (not Pol) to reverse the torque
FreeLayerThickness = 1e-9            // magnet thickness d (m)
J            = vector(0, 0, 1e11)    // |J_c| in A/m^2; J_z > 0 pulls m toward FixedLayer (FIXEDLAYER_TOP)

// (b) effective fields; J, Pol and xi stay free for Zhang-Li
BDL := 3.3e-3                                                    // T
AddFieldTerm(Mul(Const(BDL), Cross(m, ConstVector(0, 1, 0))))    // damping-like: BDL (m x sigma)
B_ext = vector(0, 1.0e-3, 0)                                     // field-like 0.3*BDL along sigma, plus any applied field
```

- (a) and (b) give the same dynamics: the solver's LL conversion of (b) is exactly the LL form that (a) adds.
- (a) supports current pulses through J(t), but it ties `Pol` to θ_SH, so an in-plane Zhang–Li current in the same film would use P = θ_SH.
- (b) keeps `J`, `Pol` and `xi` for Zhang–Li. But `Const` is fixed when defined (remove the term with `RemoveCustomFields()`), and the non-conservative field makes `E_custom` and `E_total` meaningless.

## 6. Chiral walls and skyrmions under current

- Interfacial DMI (`Dind`) fixes Néel walls of one chirality. The damping-like SOT acts on such a wall as an easy-axis field (π/2)·B_DL·cos ψ (ψ: angle of the wall moment from the wall normal; cos ψ = ±1 for Néel, 0 for Bloch).
- Low current: v = (π/2)γΔ·B_DL·cos ψ/α. High current: the wall turns toward Bloch and v saturates near (π/2)γD/Ms when the DMI field dominates the wall's shape anisotropy (Thiaville et al. 2012). D = 1 mJ/m², Ms = 1e6 A/m → 280 m/s.
- Up–down and down–up walls of the same chirality move the same way, so domains translate rather than grow. The direction is set by the signs of θ_SH and D, not by the electron flow: Pt- and Ta-based stacks drive walls in opposite directions (Emori et al. 2013); in Pt/Co/Ni/Co walls move along the current, against the electron flow (Ryu et al. 2013).
- An in-plane field along the wall normal equal to −B_DMI, with B_DMI = D/(Ms·Δ) (D = 1 mJ/m², Ms = 1e6 A/m, Δ = 5 nm → 0.2 T), turns the wall into a Bloch wall and stops SOT-driven motion. This is the usual way to measure D.
- Skyrmions (rigid Thiele model; gyrocoupling G = 4πQ; dissipation 𝒟 ≈ 4π for compact skyrmions and ≈ 2πR/Δ for radius R ≫ Δ; both in units of Ms·d/γ):
  - Zhang–Li: v_∥ = u(G² + αβ𝒟²)/(G² + α²𝒟²) and |v_⊥| = |α − β|·|G|𝒟u/(G² + α²𝒟²), so v ≈ u, with no transverse motion when β = α.
  - SOT: v ∝ B_DL, at a skyrmion Hall angle tan θ_SkH = 4π|Q|/(α𝒟) from the driving force (tens of degrees in experiments). Skyrmions drift into edges: watch `ext_topologicalcharge` for annihilation.

## 7. Confounders: Oersted field and Joule heating

Oersted field. mumax3 never computes it: add it to `B_ext` (uniform, or `B_ext.Add(LoadFile("bOe.ovf"), 1)` from a Biot–Savart calculation, in tesla).
- Sheet estimate µ0·J·t/2 beside a conductor of thickness t, in-plane and ⊥ J, opposite on its two faces: 0.31 mT for 1e11 A/m² in a 5 nm HM; 6.3 mT at the faces of a 10 nm strip at 1e12 A/m².
- Near the edges of a strip of width w there is an out-of-plane component of order (µ0·J·t/2π)·ln(w/t), opposite at the two edges. It favours nucleation at one edge of a PMA strip.
- Pillar of radius r (CPP): circumferential field µ0·J·r/2 at the rim, 3.1 mT for 1e11 A/m² and r = 50 nm. It can stabilise vortex states in wide pillars.
- In HM/ferromagnet bilayers it points along ±σ and adds to the field-like torque: subtract it before quoting B_FL.

Joule heating. mumax3 has no heat equation: set `Msat`, `Aex`, `Ku1` (and `Temp` for thermal noise) for the estimated temperature yourself.
- Power density ρJ²: ρ = 20 µΩ·cm and J = 1e12 A/m² give 2e17 W/m³. The adiabatic rise ρJ²/C with C ≈ 3e6 J/(m³·K) is ~70 K/ns until conduction into the substrate balances it: tens to hundreds of K at 1e12 A/m². β-Ta and β-W (≈ 150–250 µΩ·cm) heat ~10 times more at the same J.
- Signatures: thresholds that scale as J² rather than J, dependence on pulse length, resistance rising during the pulse. Torques and Oersted fields are odd in J, heating is even: compare +J with −J.

## 8. Typical current densities (1e8 A/cm² = 1e12 A/m²)

| process | J (A/m²), order of |
|---|---|
| CPP spin-transfer switching of a perpendicular MTJ | 1e10–1e11 |
| CPP switching or oscillation of an in-plane spin valve | 1e11–1e12 |
| SOT switching (current density in the HM) | 1e11–1e12 |
| SOT-driven chiral walls at 100–500 m/s | 1e11–1e12 |
| Zhang–Li wall motion in permalloy strips (u ≈ 30–100 m/s) | ≈ 1e12 |

## 9. How a simulation measures it

- Sign tests before any production run (minutes each):
  1. Slonczewski or SOT: one cubic cell (no shape anisotropy), `Msat` set, `alpha = 0.01`, `m = Uniform(1, 0, 0)`, `FixedLayer = vector(0, 0, 1)`, `J = vector(0, 0, 1e11)`, `Run(1e-10)`. m_z must become positive (pulled toward `FixedLayer`, default `FIXEDLAYER_TOP`).
  2. Zhang–Li: a relaxed wall in a strip, `xi` = `alpha`, `J = vector(1e12, 0, 0)`. The wall moves toward −x at ≈ u.
  3. A full SOT model: reproduce one known experimental sign (the wall direction for a known sign of D, or the switching polarity for a given in-plane field) and keep that convention.
- Wall position and velocity: `ext_centerWall(c)` keeps the wall in the window. For a full rectangular strip, position = `ext_dwpos` + s·(L/2)·⟨m_c⟩, where `ext_dwpos` = −`TotalShift` is the window position, L the window length and s the sign of m_c in the left domain.
  - `ext_dwxpos` is this formula with c = x and s = +1 only: wrong for ±z (perpendicular) walls.
  - `ext_dwspeed` is a cell-quantised difference: fit q(t) linearly after the transient instead.
  - Remove the end charges of in-plane walls with `ext_rmSurfaceCharge`.
- Skyrmions and bubbles: `ext_bubblepos` uses layer 0 only and tracks the region where m_z = `ext_BubbleMz` (default +1; set −1 for a core-down skyrmion). `ext_centerBubble` moves the window. Fit position against time for velocity and Hall angle; `ext_bubblespeed` is a path-length rate (≥ 0, inflated by noise).
- Switching: final m·p against J and pulse length; bisect J for the threshold; at T > 0, the switching probability over many `ThermSeed` values.
- Torque size: `TableAdd(STTorque)` (average, T) or `Save(STTorque)`. At m ⟂ p and ε′ = 0 its magnitude is B_DL/√(1 + α²).
- Validate on a narrow strip against closed forms: v = βu/α below Walker and v = u at β = α; u_W; J_c0 of a macrospin. The spin-wave Doppler shift Δf = k·u/(2π) (Vlaminck & Bailleul 2008) checks u and its sign.
- Relax at J = 0, then switch on the current and `Run()`. `Relax()` still applies the spin torques (with precession switched off); never `Minimize()` with a current or a damping-like `AddFieldTerm`.

## Sanity checks

| quantity | formula | example |
|---|---|---|
| Zhang–Li velocity u | 5.79e-5·P·J/Ms (m/s) | 72 m/s: J = 1e12 A/m², P = 1, Ms = 8e5 A/m |
| CPP damping-like field, Λ = 1 | 3.29e-16·P·J/(Ms·d) (T) | 8.2 mT: 1e11 A/m², P = 0.5, Ms = 1e6 A/m, d = 2 nm |
| SOT damping-like field | 3.29e-16·θ_SH·J/(Ms·d) (T) | 3.3 mT: 1e11 A/m², θ_SH = 0.1, Ms = 1e6 A/m, d = 1 nm |
| intrinsic pinning (β = 0) | u_c = γΔB_K/2 | 88 m/s: Δ = 20 nm, B_K = 50 mT |
| DMI-wall saturation speed | (π/2)γD/Ms | 280 m/s: D = 1 mJ/m², Ms = 1e6 A/m |
| perpendicular macrospin J_c0 | 2αe·Ms·d·B_K,eff/(ħP) | 1.5e10 A/m² for the values in §4 |
| Oersted sheet field | µ0·J·t/2 | 0.63 mT per 1e11 A/m² and 10 nm |

- A Zhang–Li wall with β = α must move at u along −J. Anything else is a resolution, geometry or sign problem.
- Speeds above ~1 km/s in a ferromagnet, or J of several 1e12 A/m², are at or beyond the edge of experiments (heating, electromigration): confirm that the regime is intended.

## Common mistakes

- A/cm² entered as A/m² (×1e4): 1e8 A/cm² = 1e12 A/m².
- Reading `J` as electron flow. It is conventional current, and Zhang–Li walls move along −J.
- Forgetting the defaults `Pol` = 1 (u too large by 1/P) and `xi` = 0 (intrinsic pinning; in a short run the transient displacement of a stalled wall looks like motion).
- An in-plane `J` with a `FixedLayer`, expecting a Slonczewski torque (it reads J_z only); or a CPP run with Nz > 1, where Zhang–Li also acts on z-gradients.
- `FreeLayerThickness` left at 0 with other layers or vacuum in the mesh; J not restricted to the free layer.
- SOT through the Slonczewski term without `DisableZhangLiTorque`, or with `Pol` also meant as the Zhang–Li polarization.
- Copying an SOT formula from a paper with a different convention (spin versus moment, current versus electron flow, HM below versus above) without a sign test.
- `Relax()` or `Minimize()` with the current on.
- Comparing T = 0, disorder-free, uniform-current simulations with experiments at 1e11–1e12 A/m² without the Oersted field, heating, current crowding at notches, or pinning (creep regime).
- Measuring a velocity inside the nanosecond transient, from `ext_dwspeed`, from `ext_dwxpos` for a perpendicular wall, or from `ext_bubblepos` with the wrong `ext_BubbleMz`.

## References

- S. Zhang, Z. Li, Phys. Rev. Lett. 93, 127204 (2004) — Zhang–Li torque and the non-adiabatic term.
- A. Thiaville, Y. Nakatani, J. Miltat, Y. Suzuki, Europhys. Lett. 69, 990 (2005) — current-driven walls, 1D model and micromagnetics.
- G. Tatara, H. Kohno, Phys. Rev. Lett. 92, 086601 (2004) — intrinsic pinning.
- J. C. Slonczewski, J. Magn. Magn. Mater. 159, L1 (1996); L. Berger, Phys. Rev. B 54, 9353 (1996).
- J. Z. Sun, Phys. Rev. B 62, 570 (2000) — macrospin critical current.
- I. M. Miron et al., Nature 476, 189 (2011); L. Liu et al., Science 336, 555 (2012) — SOT switching.
- L. Liu, T. Moriyama, D. C. Ralph, R. A. Buhrman, Phys. Rev. Lett. 106, 036601 (2011) — spin Hall torque in Pt (spin-torque FMR).
- C.-F. Pai et al., Appl. Phys. Lett. 101, 122404 (2012) — β-W.
- A. Thiaville et al., Europhys. Lett. 100, 57002 (2012) — dynamics of Dzyaloshinskii walls.
- S. Emori et al., Nature Mater. 12, 611 (2013); K.-S. Ryu et al., Nature Nanotech. 8, 527 (2013) — chiral walls driven by SOT.
- A. A. Thiele, Phys. Rev. Lett. 30, 230 (1973); J. Iwasaki, M. Mochizuki, N. Nagaosa, Nature Commun. 4, 1463 (2013); J. Sampaio et al., Nature Nanotech. 8, 839 (2013) — current-driven skyrmions.
- W. Jiang et al., Nature Phys. 13, 162 (2017); K. Litzius et al., Nature Phys. 13, 170 (2017) — skyrmion Hall effect.
- V. Vlaminck, M. Bailleul, Science 322, 410 (2008) — current-induced spin-wave Doppler shift.
- A. Manchon et al., Rev. Mod. Phys. 91, 035004 (2019) — review of spin–orbit torques.
- A. Vansteenkiste et al., AIP Advances 4, 107133 (2014) — mumax3, including its spin-transfer torque terms.
