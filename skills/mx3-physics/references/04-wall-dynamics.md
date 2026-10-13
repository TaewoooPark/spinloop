# Domain-wall dynamics: the 1D model, Walker breakdown, and measuring velocities

Use this chapter for field-driven wall motion: mobility, Walker field and velocity with and without DMI, the precessional regime, transient times, what the 1D model misses in real strips, the creep–depinning–flow picture, and how to extract a trustworthy velocity from mumax3 (moving frame, transients, period averaging).
Static wall structure is in 03-domain-walls.md; current-driven motion in 11-spin-torques.md; thermal creep in 08-thermal.md; moving-frame numerics in 09-numerics.md §6.

**Notation (SI).** q = wall position (m); φ = wall-moment angle from the wall normal (0, π Néel; ±π/2 Bloch); Δ = √(A/K_eff) (from `Aex`, `Ku1`, `Msat`; 03 §1); B = applied field along the domain magnetisation (component of `B_ext`, T); B_K = 2K_D/Ms = N_x µ0Ms (T), the wall's hard-axis (Bloch–Néel) field, with N_x ≈ t ln2/(πΔ) in ultrathin films (03 §3); B_DMI = D/(MsΔ) (T) from `Dind`; α = `alpha`; γ = `GammaLL` = 1.7595e11 rad/(s·T) (γ/2π = 28.0 GHz/T). mumax3 integrates the Gilbert equation in its Landau–Lifshitz form with γ = `GammaLL`, so Gilbert-form results below apply with α = `alpha` unchanged.

## 1. Driving pressure and the 1D (q, φ) model
A field B along one domain pushes a 180° wall with pressure p = 2MsB (N/m²); the domain parallel to B grows.
Collective-coordinate equations (Slonczewski 1972; Malozemoff & Slonczewski 1979; DMI form from Thiaville et al. 2012, written with B in T), for one wall polarity:

    φ̇ + α q̇/Δ = γB
    q̇/Δ − α φ̇ = γ[(π/2)B_DMI sin φ − (B_K/2) sin 2φ]

- The opposite polarity and other sign conventions flip signs, not magnitudes. An in-plane field B_x along the wall normal adds to B_DMI for one polarity and subtracts for the other.
- **Assumptions:** 1D (nothing varies along the wall), rigid profile of fixed Δ, uniform B, no pinning, T = 0, thin film with local demagnetisation.
- The exact Walker travelling wave (Schryer & Walker 1974, D = 0) narrows as the wall moves, Δ(φ) = √(A/(K_eff + K_D cos²φ)): a few % for K_D ≪ K_eff.

## 2. Below breakdown: steady motion
v = γΔB/α [m/s]; mobility µ = γΔ/α [m/(s·T)]. φ is constant, set by B/α = (π/2)B_DMI sin φ − (B_K/2) sin 2φ.
- **Example:** Δ = 6 nm, α = 0.1: µ = 10.6 m/(s·mT). Mobilities span ~1 m/(s·mT) (PMA films with large α) to hundreds of m/(s·mT) (soft strips, α ≈ 0.01, wide walls).
- **Which Δ:** in real 2D walls use the Thiele width Δ_T = 2wt/∫(∂_x m)² dV (03 §9). For PMA films Δ_T ≈ √(A/K_eff) within ~10%; for soft-strip walls Δ_T scales with the strip width and √(A/K) is meaningless.
- **Accuracy:** in PMA films the 1D mobility agrees with micromagnetics to a few % (Thiaville et al. 2012: 1.96 m/(s·mT) from 1D micromagnetics vs γΔ/α = 1.99 with Δ = √(A/K_eff)); use Δ_T when the wall has tails or a 2D structure.
- **Misuse:** using πΔ for Δ (velocity π× too high); inferring α from a slope measured partly above B_W or in the creep regime; using an FMR α when extra wall damping (spin pumping, inhomogeneity) is present: the mobility measures the wall's effective damping.

## 3. Walker field and Walker velocity
**No DMI:** B_W = αB_K/2 = αK_D/Ms [T]; v_W = γΔB_K/2 [m/s], independent of α. For an ultrathin PMA film B_W = αN_xµ0Ms/2 and v_W = (ln2/2π)γµ0Ms·t, independent of Δ: ≈ 24 m/s for Ms = 1 MA/m, t = 1 nm.
**With DMI** (Thiaville et al. 2012): B_W = α sin φ_W [(π/2)B_DMI − B_K cos φ_W], with cos φ_W = (δ − √(δ² + 8))/4 and δ = D/D_N = (π/2)B_DMI/B_K (D_N from 03 §4). δ = 0 recovers αB_K/2.
- **Large D (δ ≫ 1):** B_W ≈ α(π/2)B_DMI = απD/(2MsΔ) and v_W ≈ (π/2)γD/Ms, independent of α and Δ.
- DMI stiffens φ toward Néel, extends the steady regime and leaves the mobility unchanged. B_W grows almost linearly with D: D = 0.6 mJ/m² raised it ~10× in Thiaville's example. An in-plane B_x shifts B_W up or down per wall polarity.

| Example: Ms = 1 MA/m, t = 1 nm, Δ = 6 nm, α = 0.1 | B_K | B_W | v_W |
|---|---|---|---|
| D = 0 (Bloch) | 46 mT | ≈ 2.3 mT | ≈ 24 m/s |
| D = 1 mJ/m² (B_DMI = 0.17 T, δ ≈ 5.7) | 46 mT | ≈ 27 mT | ≈ 280 m/s |

- **Validity:** rigid 1D wall, local thin-film demagnetisation, uniform field, no disorder.
- **Accuracy:** PMA strips wider than the Bloch–Néel transition width: tens of % against 2D micromagnetics, mainly through Δ and N_x (Thiaville et al. 2012). Soft in-plane strips (transverse walls, with B_K from the wall-volume demagnetising factors, Mougin et al. 2007): order of magnitude only, because breakdown starts by antivortex nucleation at an edge and depends on width, thickness, edge roughness (Nakatani et al. 2003) and transverse fields.
- **Misuse:** using the domain anisotropy K_eff in B_W = αK/Ms. The right K is the wall's transverse K_D; K_eff overestimates B_W by K_eff/K_D, often 10–100×. Also: quoting v_W from a run whose transient overshot B_W.

## 4. Above breakdown: precessional regime
1D, D = 0, time-averaged over the precession (from §1 with ⟨sin 2φ⟩ integrated exactly):
⟨v⟩ = (γΔ/α)[B − √(B² − B_W²)/(1 + α²)].
- **High field:** ⟨v⟩ → αγΔB/(1 + α²), so the high-field mobility is α²/(1 + α²) of the low-field one.
- **Minimum:** above B_W the velocity falls (negative differential mobility) to ⟨v⟩_min ≈ √2·α·v_W at B ≈ B_W/(α√2) (α ≪ 1), then rises with the high-field mobility. For α = 0.02: ⟨v⟩/v_W ≈ 0.64 at 1.1 B_W, 0.27 at 2 B_W, 0.10 at 5 B_W.
- **Exact 1D identity** (first equation of §1, any D): q(t) − q(0) = (Δ/α)[γBt − (φ(t) − φ(0))], hence ⟨v⟩ = (Δ/α)(γB − ⟨φ̇⟩) ≤ γΔB/α. Measuring the wall-moment rotation rate ⟨φ̇⟩ = 2πf_rot checks a simulated ⟨v⟩ without any fit; 2D walls obey it only approximately.
- **Precession:** ⟨φ̇⟩ = γ√(B² − B_W²)/(1 + α²). Without DMI the energy has period π in φ, so the position oscillates (forward, back) once per half turn: T_q = π(1 + α²)/(γ√(B² − B_W²)). Far above B_W, T_q ≈ π/(γB): 0.36 ns at 50 mT.
- **With DMI:** the cos φ term makes the q-oscillation period a full turn, and there is no closed form for ⟨v⟩. Integrate the two ODEs of §1 (seconds of CPU) or measure.
- **Misuse:** reading α from the high-field slope with the low-field formula (that slope is αγΔ/(1 + α²)); applying the D = 0 curve to DMI walls.
- **Accuracy:** narrow PMA strips follow the 1D curve qualitatively above B_W. In wide strips the wall moment twists along the wall: vertical Bloch lines nucleate at the edges and travel, and ⟨v⟩ and the period depart from 1D. With strong DMI the Bloch lines annihilate and v stays near v_W up to high fields instead of dropping (Yoshimura et al. 2016). In soft strips the wall cycles TW → antivortex wall → reversed TW, and the mobility drop is observed in Py nanowires (Beach et al. 2005); the 1D formula gives only the scale.

## 5. Transients
- The wall angle relaxes with τ ≈ (1 + α²)/(αγg′), where g′ is the φ-stiffness: g′ = B_K for a Bloch wall (D = 0) and g′ ≈ (π/2)B_DMI − B_K for a Néel wall (D ≫ D_N).
  - α = 0.1, B_K = 46 mT: τ ≈ 1.2 ns. α = 0.02: ≈ 6 ns.
- **Critical slowing down:** near B_W, g′ → 0 and τ grows as (1 − B²/B_W²)^(−1/2).
- During the transient the wall gains or loses exactly (Δ/α)·|Δφ| of distance relative to steady motion (1D identity of §4), e.g. 150 nm for Δ = 6 nm, α = 0.02, Δφ = 0.5 rad. This offset shifts the intercept of a position fit; including the transient in the fit biases the slope.
- **DMI strips:** the in-plane wall tilt relaxes with a time ∝ w² (Boulle et al. 2013), so wide strips need very long runs.
- **Rule:** discard ≥ 3–5 τ after any change of field, current or regime before fitting.

## 6. What the 1D model misses in real strips
Extended collective-coordinate models add degrees of freedom one at a time: q–φ–Δ (breathing width), q–φ–χ (in-plane tilt χ; Boulle et al. 2013), the Thiele equation for vortex walls (core position; Thiaville et al. 2005), and wall-volume demagnetising factors for confined strips (Mougin et al. 2007). Use them to interpret a simulation, with Δ, B_K and B_DMI measured from the static state (03 §9), not as a substitute for one.

| Effect | Where | Consequence | Handle |
|---|---|---|---|
| finite width, edges | in-plane strips | antivortex nucleation at an edge starts breakdown; edge roughness can delay it and raise peak velocities (Nakatani et al. 2003) | simulate the real width; `EdgeSmooth` |
| demagnetising fields | all | wall-volume N factors set B_K (Mougin et al. 2007); Néel walls grow m_x tails; finite-strip stray fields pull walls (PMA: toward the strip centre; head-to-head walls: toward the ends) | long strips, moving frame, `ext_rmSurfaceCharge` |
| wall tilting | DMI strips under field or SOT | wall rotates in-plane by χ, lowering velocity at large D; extended q–φ–χ model (Boulle et al. 2013) | wide enough boxes; `ext_dwtilt` (03 §9) |
| non-uniform φ along the wall | wide PMA strips above B_W | Bloch lines, irregular "Walker oscillations" | period averaging (§9) |
| vortex walls | wide soft strips | core moves across the strip (gyrotropic force); above a threshold it is expelled and VW ↔ TW transformations repeat | Thiele approach (Thiaville et al. 2005); measure |
| breathing, inertia | all | Δ changes with φ and B; transient overshoot | q–φ–Δ models; discard transients |
| spin-wave emission | high v, abrupt changes | drag, ripples; reflections from box ends | absorbing ends |
| cylindrical wires | Bloch-point walls | no Walker breakdown, velocity limited by spin-wave emission (Yan et al. 2010); singular core is mesh-dependent | state the mesh |
| disorder, temperature | experiments | pinning, creep, rounded B_W | §7, 08-thermal.md |

## 7. Creep, depinning, flow (brief)
- **Flow** (B well above the depinning field B_dep): the regimes of §2–4; v linear in B below B_W.
- **Depinning** (T = 0): v = 0 below B_dep, rising as a power law above it; temperature rounds the threshold.
- **Creep** (B ≪ B_dep, T > 0): ln v = ln v0 − (U_c/k_BT)(B_dep/B)^µ with µ = 1/4 for a 1D elastic wall in a 2D random medium (Lemerle et al. 1998; Metaxas et al. 2007). Slopes of ln v vs B^(−1/4) identify creep in data. An in-plane field changes σ differently for up|down and down|up DMI walls, so creep becomes asymmetric (Je et al. 2013; 03 §6).
- **In mumax3:** creep waiting times (µs–s) are out of reach. T = 0 depinning with grains (03 §7) is feasible. Finite `Temp` (Heun with `FixDt`, or a validated adaptive step, 08-thermal.md) with several `ThermSeed` values shows only the thermal rounding near B_dep.

## 8. Current-driven motion (brief)
- **Spin-transfer torque** (`J` in-plane, `Pol`, `xi`; Zhang–Li): below breakdown v = (β/α)u. With β = 0 there is intrinsic pinning below u_c = γΔB_K/2.
- **Spin–orbit torques** (Slonczewski term or effective fields): move only chiral Néel walls, so DMI is required. v saturates near (π/2)γD/Ms, and the direction is set by the signs of θ_SH and D (Emori et al. 2013; Ryu et al. 2013).
- Formulas, mumax3 mappings and confounders (Oersted field, Joule heating) are in 11-spin-torques.md §2–3 and §5–7. The measurement practice of §9 applies unchanged.

## 9. How a simulation measures a velocity
**Protocol.**
1. Relax the wall at B = 0 (`Minimize()`/`Relax()`; they ignore `alpha`).
2. Set the physical `alpha`, then step `B_ext` (or the current) and `Run`.
3. Record `TableAdd(ext_dwpos)` and `TableAdd(m)`, and `TableAutoSave(Δt_s)` with Δt_s ≤ T_q/10 above breakdown and ≥ 50 rows per fit window. Rows land on the first step after each period, so fit against the table's t column (09 §3). Add sparse `AutoSave(m, …)` to see the structure.
4. One run per field value, each from the relaxed wall (run them as a batch, `mx3 batch`). A slow field ramp mixes transients into the curve.

**Wall position.**
- **Static frame**, magnet filling the box along x (length L): q = (L/2)(1 + s⟨m_c⟩) from the left end, with s = sign of m_c in the left domain and c = z (PMA walls) or x (head-to-head walls). Valid for a straight wall several Δ from the strip ends.
- **Moving frame:** `ext_centerWall(c)` (c = 2 for PMA, 0 for head-to-head) shifts the content by one cell whenever |⟨m_c⟩| > 4/Nx, i.e. when the wall is ≈ 2 cells off centre.
  - `ext_dwpos` = −`TotalShift`, the window displacement in one-cell steps.
  - Sub-cell position: x_wall = `ext_dwpos` + s(L/2)⟨m_c⟩, with L = Nx·cx. Constant offsets do not affect v.
  - `ext_dwxpos` = `ext_dwpos` + (L/2)⟨m_x⟩. It is correct only for an x-magnetised wall with +x on the left; for PMA walls ⟨m_x⟩ is the wall moment, not a position.
  - `ext_dwspeed` is a finite difference of the one-cell staircase between table rows: too noisy to fit.
- `ext_centerWallInLayer`/`ext_centerWallInRegion` centre on one layer or region.

**Moving-frame mechanics (mumax3 3.12 source).**
- `ShiftMagL`/`ShiftMagR` are auto-set to ±ê_c from the leftmost cell at mid-height if unset. The run panics ("unclear in which direction to shift") if |m_c| < 0.1 there: then set them yourself.
- Inserted columns are exactly ±ê_c. With tilted domains (in-plane field, canting) every shift injects a small step that radiates spin waves. Set `EdgeCarryShift = true` (copies the border magnetisation) or set `ShiftMagL`/`ShiftMagR` to the actual domain vector.
- `Shift` moves m, geometry and regions together (`ShiftM`, `ShiftGeom`, `ShiftRegions`, all true by default). Inserted cells re-evaluate `SetGeom`, `DefRegion` and `ext_makegrains` shapes at lab-frame coordinates, so notches and grains stay fixed in the lab and the wall keeps meeting new disorder. Regions set cell by cell (`DefRegionCell`) or loaded from a file enter as region 0.
- Absorbing high-`alpha` end regions drift out of the window with the content. In an otherwise uniform strip, keep them in place with `ShiftRegions = false`.
- Head-to-head walls: the window's end charges pull the wall. Compensate with `ext_rmSurfaceCharge(region, mxLeft, mxRight)` (a static field added to `B_ext`).

**Fitting.**
- Skip ≥ 3–5 τ (§5), longer near B_W and in wide DMI strips.
- **Below B_W:** linear least squares of x_wall(t); report v, r² and the residual RMS. Using the cell-quantised `ext_dwpos` alone gives a velocity error of order cell/T_fit.
- **Above B_W:** average over a whole number of oscillation periods, found from zero crossings of ⟨m_x⟩ or ⟨m_y⟩ (the wall moment) or of the position residual, or fit over ≥ 10 periods. A window that is not a whole number of periods biases ⟨v⟩ by up to (oscillation amplitude)/(window duration). Over many periods r² stays high: a low r² over a short window means the window is too short, not that ⟨v⟩ is meaningless.
- **B_W:** locate the onset of continuous rotation of the wall moment (⟨m_x⟩, ⟨m_y⟩ start to oscillate) in a field series, not only the velocity peak.

**Box and numerics.**
- Window length ≳ several wall widths plus several strip widths (in-plane strips ≥ 3–5 w; PMA ≥ ~20Δ and ≥ w). Double it once to check (09 §8).
- In a static frame the strip ends and finite-strip magnetostatics accelerate or decelerate the wall: fit only the central part.
- Spin waves from transients and fast walls reflect from window ends: use graded absorbing ends (09 §6).
- **Lattice pinning:** in a perfect strip at T = 0 the wall must move at any small field. If v = 0 below a field that shrinks as the cell shrinks, the cell is too coarse (cell ≤ Δ/2).
- Solver 5 (default) with `MaxErr` ≤ 1e-5; repeat one high-field point with `MaxErr`/10.

## Sanity checks
- Below B_W, v/B ≈ γΔ/α: Δ = 6 nm, α = 0.1 gives 10.6 m/(s·mT).
- v_W without DMI = (ln2/2π)γµ0Ms·t ≈ 10–50 m/s in ultrathin PMA films; with D ≈ 1 mJ/m², Ms ≈ 1 MA/m, ≈ 250–300 m/s.
- B_W = αB_K/2 without DMI: ~0.05–15 mT for α = 0.01–0.3 and B_K ≈ 10–100 mT. A value K_eff/K_D (10–100×) larger means K_eff was used instead of K_D.
- High-field mobility ≈ α²/(1 + α²) of the low-field mobility.
- Position oscillation period above B_W ≈ π/(γB) for B ≫ B_W.
- Transient τ ≈ (1 + α²)/(αγB_K) is several ns at α ≈ 0.02: runs shorter than ~5τ give no steady velocity.
- Bound: ⟨v⟩ ≤ γΔB/α at every field (1D; γΔ_T B/α for 2D walls). A simulated velocity well above it points to a unit error, a wrong Δ, or motion driven by something else (end charges, a field gradient, a current term left on).

## Common mistakes
- Fitting the transient, or across B_W; quoting a velocity above B_W that is not averaged over whole periods.
- Using `ext_dwspeed`, or `ext_dwxpos` for PMA walls; the wrong component c in `ext_centerWall`.
- Tilted domains without `EdgeCarryShift` or explicit `ShiftMagL`/`ShiftMagR`; uncompensated end charges for head-to-head walls.
- Expecting the 1D B_W in wide or soft strips; using K_eff in B_W; using πΔ or √(A/K) as the mobility width of a soft-strip wall.
- Leaving a relaxation-time `alpha` in the production run; ramping the field instead of stepping it.
- Reporting one disorder realisation as "the" depinning field.

## References
- N. L. Schryer, L. R. Walker, "The motion of 180° domain walls in uniform dc magnetic fields", J. Appl. Phys. 45, 5406 (1974).
- J. C. Slonczewski, "Dynamics of magnetic domain walls", Int. J. Magnetism 2, 85 (1972).
- A. P. Malozemoff, J. C. Slonczewski, *Magnetic Domain Walls in Bubble Materials*, Academic Press (1979).
- A. Hubert, R. Schäfer, *Magnetic Domains*, Springer (1998).
- A. Thiaville, S. Rohart, É. Jué, V. Cros, A. Fert, EPL 100, 57002 (2012).
- A. Thiaville, Y. Nakatani, J. Miltat, Y. Suzuki, "Micromagnetic understanding of current-driven domain wall motion in patterned nanowires", EPL 69, 990 (2005).
- A. Mougin, M. Cormier, J. P. Adam, P. J. Metaxas, J. Ferré, EPL 78, 57007 (2007).
- O. Boulle et al., Phys. Rev. Lett. 111, 217203 (2013).
- Y. Nakatani, A. Thiaville, J. Miltat, "Faster magnetic walls in rough wires", Nature Mater. 2, 521 (2003).
- G. S. D. Beach, C. Nistor, C. Knutson, M. Tsoi, J. L. Erskine, "Dynamics of field-driven domain-wall propagation in ferromagnetic nanowires", Nature Mater. 4, 741 (2005).
- Y. Yoshimura et al., "Soliton-like magnetic domain wall motion induced by the interfacial Dzyaloshinskii–Moriya interaction", Nature Phys. 12, 157 (2016).
- M. Yan, A. Kákay, S. Gliga, R. Hertel, "Beating the Walker limit with massless domain walls in cylindrical nanowires", Phys. Rev. Lett. 104, 057201 (2010).
- S. Lemerle et al., "Domain wall creep in an Ising ultrathin magnetic film", Phys. Rev. Lett. 80, 849 (1998).
- P. J. Metaxas et al., "Creep and flow regimes of magnetic domain-wall motion in ultrathin Pt/Co/Pt films with perpendicular anisotropy", Phys. Rev. Lett. 99, 217208 (2007).
- S. Emori et al., Nature Mater. 12, 611 (2013); K.-S. Ryu et al., Nature Nanotech. 8, 527 (2013); S.-G. Je et al., Phys. Rev. B 88, 214401 (2013).
- A. Vansteenkiste et al., AIP Advances 4, 107133 (2014).
