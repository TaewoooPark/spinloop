# Skyrmions, bubbles and vortices: size, stability, topology, Thiele dynamics

Use this chapter for magnetic skyrmions (Néel and Bloch), skyrmion bubbles and vortices in disks: what stabilises them, closed forms for skyrmion radius and energy, topological charge, annihilation routes, the Thiele equation and skyrmion Hall angle, vortex core size, gyrotropic frequency and core switching, and how to measure each of these in mumax3.
Chiral wall energetics are in 03-domain-walls.md; current-driven skyrmions in 11-spin-torques.md §6; thermal lifetimes in 08-thermal.md; mesh rules in 02-scales.md §13.

**Notation (SI).** A = `Aex`; Ms = `Msat`; K = K_eff = Ku − µ0Ms²/2 (`Ku1` stays the material Ku with demag on); D = `Dind` or `Dbulk` (J/m²); t = film thickness; Δ = √(A/K); D_c = 4√(AK)/π and d = D/D_c; α = `alpha`; γ = `GammaLL` = 1.7595e11 rad/(s·T). R = skyrmion radius (m_z = 0 contour), w = its wall width; p = core m_z (±1); Q = topological charge. Vortex disks: radius R_d, thickness L. B = applied field in T (`B_ext`).

## 1. Types and what stabilises them
| Type | Stabilised by | In-plane structure | Size | mumax3 |
|---|---|---|---|---|
| Néel (hedgehog) skyrmion | interfacial DMI (heavy-metal/FM interfaces) against exchange, K_eff and a field along the background | radial, sense fixed by the sign of D | ~1–100 nm (§3) | `Dind`, `NeelSkyrmion(c, p)` |
| Bloch skyrmion | bulk DMI (B20: MnSi, FeGe, Cu₂OSeO₃) plus field | azimuthal, sense fixed by the sign of D | ~ helix period 4πA/D (FeGe ≈ 70 nm) | `Dbulk`, `BlochSkyrmion(c, p)` |
| dipolar skyrmion / bubble | stray-field energy vs wall energy, bias field; DMI optional | both Bloch senses degenerate without DMI; Néel caps or hybrids through thick films | ~0.1–10 µm, scale l_c = σ/(µ0Ms²) | demag on, large box |
| antiskyrmion | anisotropic DMI (D_2d crystals) | vorticity −1 | | no built-in term (custom field) |

- Exchange, anisotropy and a field parallel to the background shrink a skyrmion. DMI expands it (wall energy reduced by π|D| per area), and so does the stray field of the reversed core (dominant in multilayers). Edges repel it (DMI canting, 03 §4).
- **mumax3 sign rule** (from the 3.12 DMI kernels and config code):
  - `NeelSkyrmion(c, p)`: core m_z = p, in-plane component c·r̂. `Dind` > 0 favours c = −p (e.g. `NeelSkyrmion(1, -1)`, the mx3-authoring recipe); `Dind` < 0 favours c = p.
  - `BlochSkyrmion(c, p)`: in-plane component c·φ̂ (c = +1 counterclockwise seen from +z). `Dbulk` > 0 favours c = −p.
  - Verify by relaxing both senses and comparing `E_total`: the wrong one reverses its in-plane component or collapses.
  - The argument c is a sense of rotation, not the topological charge (that is p, §2).
- **Initial size:** both configs are Gaussians of width 8 cells (m_z = 0 at ≈ 6.7 cells), whatever the physics. Rescale with `.Scale(s, s, 1)`, or start from a reversed disk, `m = Uniform(0,0,1)` then `m.SetInShape(Circle(2*R0), Uniform(0,0,-1))`, and let the DMI set the chirality while relaxing.

## 2. Topological charge
Q = (1/4π)∫ m·(∂_x m × ∂_y m) dx dy (dimensionless; per layer). For a rotationally symmetric texture with vorticity W: Q = (W/2)[cos θ(0) − cos θ(∞)].
- **Values:** skyrmion with core p in a −p background, Q = p (helicity irrelevant), so `NeelSkyrmion(1, -1)` has Q = −1. Antiskyrmion: −p. Vortex or meron: Q = pW/2 = ±1/2 per core. A bubble with a simple wall: ±1; Bloch lines in its wall change Q ("hard" bubbles).
- **mumax3:**
  - `ext_topologicalcharge`: finite-difference density m·(∂_x m × ∂_y m), summed × cx·cy/4π and averaged over layers.
  - `ext_topologicalchargelattice`: Berg–Lüscher solid angles; integer for a resolved texture with a uniform boundary.
  - Maps: `ext_topologicalchargedensity`, `ext_topologicalchargedensitylattice`.
- **Validity:** 2D, a uniform background at the box edges (or PBC). Open edges with DMI canting, or textures touching edges, give non-integer values.
- **Accuracy:** the finite-difference Q drifts from an integer as cell/w grows; use the drift as a resolution indicator. The lattice Q stays integer until the topology actually changes.
- **Misuse:** reading a non-integer finite-difference Q as physics. Treating the jump 1 → 0 as a physical barrier crossing: in a continuum code it is a lattice-scale event at an unresolved Bloch point. Comparing signs across papers (some define Q or the "skyrmion number" with the opposite sign).

## 3. Radius and energy of an isolated skyrmion (interfacial DMI, thin film)
Profile (Wang, Yuan & Wang 2018): a 360° wall, Θ(r) = 2 arctan[sinh(R/w)/sinh(r/w)].
**Zero field, R ≫ w:**
R = πD√(A/(16AK² − π²D²K)) = Δ·d/√(1 − d²), w = πD/(4K) = Δ·d.
**With a field B along the background** (B > 0 shrinks the skyrmion), solve numerically:

    A(1/w − w/R²) − (π/2)D + Kw + Ms·B·R = 0
    A(1/R − R/w²) + KR + (π²/12)·Ms·B·w = 0

These minimise E = 4πt[A(R/w + w/R) − (π/2)DR + KwR + MsB(R²/2 + π²w²/24)].
- **Example** (Wang et al.): A = 15 pJ/m, Ms = 580 kA/m, Ku = 0.8 MJ/m³ (K = 0.59 MJ/m³), D = 3.7 mJ/m², so d = 0.98. The formula gives R = 24 nm, w = 4.9 nm; their mumax3 run gave 25.8 nm and 4.94 nm.
- **Thin-wall limit (d → 1):** E(R) = 2πt(σR + 2AΔ/R) with σ = 4√(AK)(1 − d). It gives R ≈ Δ/√(2(1 − d)) (the same limit as above) and E_sk ≈ 8πAt·√(2(1 − d)) above the uniform state.
- **Validity:** ultrathin film with m uniform through t; demagnetisation only as the local K_eff (no long-range dipolar term); isolated skyrmion (box ≫ R); T = 0; d < 1. At d ≥ 1 no isolated skyrmion exists in zero field (stripes or labyrinth, 03 §4).
- **Accuracy:** ~10% for R ≳ 3w (d ≳ 0.94); the example is −7%. Qualitative for R ~ w.
- **Misuse:**
  - Ku in place of K_eff, which makes the skyrmion far too small.
  - Applying the formula to multilayers or thicker films, where dipolar energy enlarges skyrmions: simulate with full demag.
  - Expecting a mesh to hold tiny skyrmions. For d ≲ 0.5 the formula gives R ≲ 0.6Δ (a few nm); on 1 nm cells Wang et al. found no stable skyrmion below d ≈ 0.3.
- **Bulk DMI:** the size is set by L_D = 4πA/D and the field scale by B_D = D²/(2AMs) (02-scales.md §8): skyrmion lattices form at intermediate fields below it, isolated skyrmions survive as metastable objects in the field-polarised state. No closed form of comparable reliability; simulate with demag and the real thickness.

## 4. Stability and annihilation
- **Metastability:** for d < 1 an isolated skyrmion is a metastable excitation, 0 < E_sk < 8πAt (the energy falls from the Belavin–Polyakov value as R grows from 0, so any minimum lies below it). For d > 1 the uniform state is no longer the ground state but stays metastable: interfacial DMI adds no quadratic term around a perpendicular uniform state, so the spin-wave gap 2γK/Ms remains. Cycloids and labyrinths then grow from edges (canting), existing walls or skyrmions, or noise; a perfect uniform film with PBC can stay uniform under `Relax()`.
- **Routes out:**
  1. collapse: R → 0 and Q changes through a Bloch-point-like event;
  2. escape through an edge: no singularity needed, so the barrier can be lower than for collapse;
  3. strip-out into a stripe or worm (elliptic instability) as σ → 0, i.e. d → 1 or a low or reversed field;
  4. merging with other textures.
- **Energy scale:** the Belavin–Polyakov energy 8πAt (A = 15 pJ/m, t = 1 nm: 3.8×10⁻¹⁹ J ≈ 90 k_BT at 300 K) is the continuum energy at collapse. The continuum barrier is therefore ≲ 8πAt − E_sk; atomistic and finite-difference lattices lower it.
- **Thermal lifetime:** τ = τ0·exp(ΔE/k_BT). Years need ~40–60 k_BT, and τ0 is not universal: entropy can shift it by orders of magnitude (Wild et al. 2017; 08-thermal.md).
- **In mumax3:**
  - There is no barrier (path) method, and `Relax()`/`Minimize()` cannot cross barriers.
  - Field-driven collapse happens when R reaches ~1–2 cells, so the collapse field depends on the mesh. The minimum stable D is mesh-dependent too: report both with a cell-size check.
- **Confinement:** in dots and tracks the DMI edge repulsion keeps skyrmions off edges. A dot can hold a skyrmion as a metastable or even ground state at zero field (Rohart & Thiaville 2013), so free-film d windows do not transfer to small elements.

## 5. Thiele equation and skyrmion Hall angle
Rigid texture m(r − X(t)) in a film of thickness t (Thiele 1973):

    G × Ẋ − α𝒟·Ẋ + F = 0

- G = 4πQ·(Ms·t/γ)·ẑ (the sign depends on convention).
- 𝒟_ij = (Ms·t/γ)∫∂_i m·∂_j m d²r.
- F = −∂E/∂X [N]: field gradients, edges, pinning, spin-torque forces (11 §6).
- For an isotropic texture 𝒟 = 𝒟_0·Ms·t/γ with 𝒟_0 = ∫(∂_x m)² d²r ≈ 2π(R/w + w/R) for the 360° profile, and 𝒟_0 ≥ 4π|Q| (Belavin–Polyakov bound).

Response to a force F: v_∥ = α𝒟F/(G² + α²𝒟²), v_⊥ = GF/(G² + α²𝒟²).
**Skyrmion Hall angle:** tan θ_SkH = G/(α𝒟) = 4πQ/(α𝒟_0) ≈ 2Qw/(αR) for R ≫ w, and |tan θ_SkH| ≤ 1/α.
- **Example:** α = 0.3, R = 10w gives 𝒟_0 ≈ 63 and θ_SkH ≈ 33°; R = 5w gives ≈ 52°.
- **Validity:** rigid, isolated, steady motion, no pinning, T = 0, force-like drive (gradients, damping-like SOT, edge forces). For Zhang–Li STT the transverse velocity ∝ (α − β) and vanishes at β = α (11 §6).
- **Accuracy:** good for small drives. Breathing and elongation at large drive change 𝒟. Measured angles in room-temperature multilayers are ~10°–35° and grow with drive because of pinning (Jiang et al. 2017; Litzius et al. 2017).
- **Misuse:** taking the 1D wall Δ or the radius instead of the skyrmion's own w in 𝒟_0; dropping the sign of Q (opposite charges deflect oppositely); measuring θ_SkH near edges or during the transient.
- **Vortices:** the same equation with Q = p/2, i.e. G = 2πp·Ms·L/γ, gives gyrotropic motion (§7).

## 6. Bubbles versus skyrmions
| | DMI skyrmion | dipolar skyrmion / magnetic bubble |
|---|---|---|
| Energy balance | DMI vs exchange, K_eff, Zeeman | wall energy σ vs stray-field energy and bias field (Malozemoff & Slonczewski 1979) |
| Length scale | Δ·d/√(1 − d²) (§3) | l_c = σ/(µ0Ms²); classic bubble-film design: thickness ≈ 4l_c, diameter ≈ 8l_c |
| Chirality | fixed by the sign of D | none without DMI; Bloch lines possible ("hard" bubbles with Q ≠ ±1 and large deflection) |
| Q | ±1 | ±1 for a simple wall |
| Dynamics | Thiele, Hall angle §5 | the same equation; skew deflection depends on Q |
| mumax3 needs | cell ≤ w/2; local K_eff acceptable in ultrathin single layers | demag essential; box of many l_c; cells ≤ Δ/2 in the wall |

Many room-temperature "skyrmions" in multilayers are hybrids: DMI fixes the chirality and dipolar energy sets the size (Büttner, Lemesh & Beach 2018). Check which term dominates by switching `Dind` off, or demag off, in a test run.

## 7. Vortices in disks
- **Ground state:** in soft disks larger than a few l_ex the moment curls in-plane (circulation c = ±1) around a core of polarity p = ±1, giving four degenerate states at zero field. Py holds a vortex above 2R_d ≈ 100–200 nm at L ≈ 10–20 nm (02-scales.md §7; Cowburn et al. 1999). `Vortex(c, p)` uses c = +1 for counterclockwise curl seen from +z; its initial core is about one cell wide, so relax.
- **Core:** m_z peaks at the centre with FWHM ≈ 10–20 nm in thin Py (≈ 2–3 l_ex), surrounded by a shallow dip of opposite sign. It widens with thickness (barrel shape through thick disks) and with B_z ∥ p, and narrows with B_z antiparallel to p. Resolve it with ≥ 3–5 cells.

**Gyrotropic mode.** From Thiele, ω_G = κ/|G| (κ: stiffness of the magnetostatic restoring force). Thin-disk two-vortex, side-charge-free model (Guslienko et al. 2002): ω_G = (20/9)γMs·L/R_d in CGS, i.e. in SI
f_G = (5/(18π²))·γµ0Ms·(L/R_d) ≈ 5.0 GHz × L/R_d for Py (µ0Ms = 1.0 T).
- **Example:** 2R_d = 500 nm, L = 20 nm gives f_G ≈ 0.40 GHz. The sense of gyration is set by p, not by c, so a circularly polarised drive excites only one polarity.
- **Validity:** L/R_d ≪ 1, R_d ≫ l_ex, small orbit, no bias field, soft material, m uniform through L.
- **Accuracy:** the linear form overestimates. The model's full magnetostatic integral is 0.96, 0.92, 0.84 and 0.73 of the linear form at L/R_d = 0.05, 0.1, 0.2 and 0.4; an exchange term lowers f further in small disks (R_d ≲ 20 l_ex). The full model is typically within ~10–20% of micromagnetics.
- **Misuse:** the rigid-vortex (side-charged) model, which is ~2× too high; a diameter in place of R_d.
- **Damping:** the orbit amplitude decays at Γ = α_v·ω_G with α_v = α[1 + ½ ln(R_d/r_c)] (from 𝒟/|G| of the vortex; r_c ≈ core radius), so α_v ≈ 2–4 α. The spectral half-width (HWHM) is ≈ α_v·f_G.
- **Bias field:** a perpendicular B_z splits the two polarities: f_p ≈ f_G(1 + p·B_z/B_s), with B_s the disk's perpendicular saturation field (≲ µ0Ms) (Pigeau et al. 2010).

**Core polarity switching.**
- **Dynamic:** the core reverses when its speed reaches v_c ≈ (1/3)γµ0Ms·l_ex = (√2/3)γ√(µ0A), ≈ 330 m/s for Py. This is the SI form of 1.66γ√A (CGS) of Lee et al. 2008; v_c is independent of disk size.
  - Mechanism: core deformation, creation of a vortex–antivortex pair, annihilation through a Bloch point (Van Waeyenberge et al. 2006).
  - Resonant rotating fields of ~1 mT at f_G suffice in Py disks (R_d = 150–300 nm, L = 20 nm).
  - Orbit radius at switching ≈ v_c/(2πf_G); if it exceeds R_d minus the core size, the core is expelled before it switches.
- **Static:** a B_z antiparallel to p of ≳ 0.2–0.5 T switches Py dots experimentally (Okuno et al. 2002). T = 0 micromagnetics gives higher, mesh-dependent values (Bloch-point injection; Thiaville et al. 2003).
- **Misuse:** quoting switching thresholds from one coarse mesh; a finite-difference code does not resolve the Bloch point.

## 8. How a simulation measures it
**Skyrmions.**
- **Charge:** `TableAdd(ext_topologicalcharge)` and `TableAdd(ext_topologicalchargelattice)`. Check integrality; a time-resolved jump marks the annihilation time.
- **Radius**, three ways:
  1. the m_z = 0 contour of a snapshot, interpolated between cells;
  2. the area integral πR_eff² = ∫(1 − s·m_z)/2 dS, s = background sign. From the table it is A_mag(1 − s⟨m_z⟩)/2 minus the same quantity of a skyrmion-free run on the same mesh (removes edge canting), with A_mag the magnetic area. For the 360° profile R_eff² ≈ R² + π²w²/12;
  3. a fit of Θ(r) = 2 arctan[sinh(R/w)/sinh(r/w)] to the radial profile, which gives R and w.
- **Position and velocity:**
  - `ext_bubblepos`: centroid weighted by 1 + m_z·`ext_BubbleMz`, with weights below `ext_BackGroundTilt` (0.25) zeroed. Set `ext_BubbleMz` to the core sign; keep one texture per window.
  - `ext_centerBubble()` recentres in x and y. In a track, set `ext_enableCenterBubbleY = false`, or the track edges move within the window.
  - `ext_bubblespeed` is a finite difference: fit positions instead.
- **Hall angle:** atan of the slope of y(x) after the transient, several diameters from edges (PBC across the track when edges are not the question). Compare with 4πQ/(α𝒟_0), with 𝒟_0 = Σ(∂_x m)²·cx·cy per layer from a snapshot.
- **Energy:** E_sk = E_total(skyrmion) − E_total(uniform), both relaxed on the same mesh and box. Expect 0 < E_sk < 8πAt for a metastable skyrmion (d < 1), and ≈ 8πAt·√(2(1 − d)) near d → 1.
- **Numerics:** cell ≤ w/2 and ≥ ~10 cells across the diameter. The box should be ≥ 5–10 R from edges, or use PBC and remember the images. Halve the cell before trusting collapse fields or a minimum D.

**Vortices.**
- `ext_corepos` returns (x, y, p): the cell of maximum |m_z| (outermost cells excluded), with parabolic sub-cell interpolation; x includes the window shift. It is wrong when other cells have larger |m_z| (strong B_z, perpendicular layers, edge artefacts): analyse cropped snapshots instead.
- **Gyrotropic frequency:**
  1. relax `Vortex(c, p)` in a small in-plane field that displaces the core by ≲ 0.1–0.2 R_d;
  2. set `B_ext` to zero and `Run` with the physical `alpha` for ≥ 10–20 periods (tens of ns at 0.2–1 GHz), with `TableAutoSave` ≤ T_G/20;
  3. FFT, or fit a damped sinusoid to `ext_corepos` or ⟨m_x⟩, ⟨m_y⟩ (both ∝ displacement). Resolution Δf = 1/T_run (09 §7);
  4. halve the kick: a frequency that moves means the orbit was not small.
- **Thick disks:** use several cells through L. The core bends, and higher gyrotropic (flexure) modes appear.
- **Core switching:** watch the sign of the z component of `ext_corepos`, limit `MaxDt` to ~1 ps through the event, and repeat with a finer cell.

## Sanity checks
- Q ≈ ±1 per skyrmion and ±½ per vortex core (lattice version exactly). A drift of the finite-difference Q by more than a few % means under-resolution or edge contact.
- R from §3: d = 0.9 gives R ≈ 2.1Δ, d = 0.98 gives ≈ 5Δ; for Δ ≈ 5 nm, 10–25 nm. A simulated skyrmion much larger than this in an ultrathin single layer suggests D > D_c or a dipolar contribution.
- E_sk < 8πAt (≈ 90 k_BT for A = 15 pJ/m, t = 1 nm) for a skyrmion that should be metastable.
- |tan θ_SkH| ≤ 1/α; 30°–60° is typical for α ≈ 0.3 and R ≈ 5–10w.
- f_G ≈ 5 GHz × L/R_d for Py: sub-GHz for usual disks; a few GHz means a confusion with the radial or azimuthal spin-wave modes (06-spin-waves-fmr.md).
- v_c ≈ 330 m/s (Py) and v_c ∝ √A: in a simulation the core reverses at about this speed whatever the drive.

## Common mistakes
- Reading the c argument of `NeelSkyrmion`/`BlochSkyrmion` as Q; using the chirality disfavoured by the sign of D; starting from the 8-cell default size.
- Ku in place of K_eff in R; using free-film D_c windows for dots and tracks; ignoring dipolar energy in multilayers.
- Taking a mesh-dependent collapse field or minimum D as physical; trusting a non-integer finite-difference Q.
- Concluding "no labyrinth at d > 1" from a uniform start with PBC: seed with `RandomMagSeed(n)` or domains and compare `E_total`.
- Hall angles from runs near edges, before the transient decays, or from `ext_bubblespeed`; a wrong `ext_BubbleMz`; centring in y inside a finite track.
- `ext_corepos` with strong B_z or perpendicular layers; FFT records shorter than ~10 periods; large-orbit (nonlinear) frequencies; one layer through a thick disk.
- Comparing f_G with the rigid-vortex model; using a diameter for R_d.
- Expecting `Relax()` or `Minimize()` to respect `alpha` or `Temp` (both are ignored, 09 §4).

## References
- A. N. Bogdanov, A. Hubert, J. Magn. Magn. Mater. 138, 255 (1994).
- A. A. Belavin, A. M. Polyakov, JETP Lett. 22, 245 (1975).
- N. Nagaosa, Y. Tokura, "Topological properties and dynamics of magnetic skyrmions", Nature Nanotech. 8, 899 (2013).
- X. S. Wang, H. Y. Yuan, X. R. Wang, "A theory on skyrmion size", Commun. Phys. 1, 31 (2018).
- S. Rohart, A. Thiaville, Phys. Rev. B 88, 184422 (2013).
- F. Büttner, I. Lemesh, G. S. D. Beach, "Theory of isolated magnetic skyrmions: from fundamentals to room temperature applications", Sci. Rep. 8, 4464 (2018).
- A. A. Thiele, "Steady-state motion of magnetic domains", Phys. Rev. Lett. 30, 230 (1973).
- A. P. Malozemoff, J. C. Slonczewski, *Magnetic Domain Walls in Bubble Materials*, Academic Press (1979).
- W. Jiang et al., "Direct observation of the skyrmion Hall effect", Nature Phys. 13, 162 (2017).
- K. Litzius et al., "Skyrmion Hall effect revealed by direct time-resolved X-ray microscopy", Nature Phys. 13, 170 (2017).
- J. Wild et al., "Entropy-limited topological protection of skyrmions", Sci. Adv. 3, e1701704 (2017).
- B. Berg, M. Lüscher, Nucl. Phys. B 190, 412 (1981).
- K. Yu. Guslienko et al., "Eigenfrequencies of vortex state excitations in magnetic submicron-size disks", J. Appl. Phys. 91, 8037 (2002).
- K. Yu. Guslienko, W. Scholz, R. W. Chantrell, V. Novosad, "Vortex-state oscillations in soft magnetic cylindrical dots", Phys. Rev. B 71, 144407 (2005).
- B. Pigeau et al., "A frequency-controlled magnetic vortex memory", Appl. Phys. Lett. 96, 132506 (2010).
- K.-S. Lee et al., "Universal criterion and phase diagram for switching a magnetic vortex core in soft magnetic nanodots", Phys. Rev. Lett. 101, 267206 (2008).
- B. Van Waeyenberge et al., "Magnetic vortex core reversal by excitation with short bursts of an alternating field", Nature 444, 461 (2006).
- T. Okuno, K. Shigeto, T. Ono, K. Mibu, T. Shinjo, J. Magn. Magn. Mater. 240, 1 (2002).
- A. Thiaville, J. M. García, R. Dittrich, J. Miltat, T. Schrefl, "Micromagnetic study of Bloch-point-mediated vortex core reversal", Phys. Rev. B 67, 094410 (2003).
- R. P. Cowburn et al., "Single-domain circular nanomagnets", Phys. Rev. Lett. 83, 1042 (1999).
- A. Vansteenkiste et al., AIP Advances 4, 107133 (2014).
