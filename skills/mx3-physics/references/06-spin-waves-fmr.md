# Spin waves and FMR: Kittel modes, linewidth, thin-film dispersion, and measuring them

Use this chapter for uniform-mode resonance frequencies (Kittel, M_eff, Smit–Beljers), for converting linewidths and ringdown decay into Gilbert damping, for thin-film spin-wave dispersion (exchange, Damon–Eshbach, backward/forward volume, PSSW, DMI nonreciprocity), and for planning and analysing mumax3 ringdown, pulse and FFT simulations.
All closed forms here are linear theory: small precession amplitude, a saturated and uniformly magnetised static state, and α ≪ 1.

## 0. Conventions

| Symbol | Meaning | SI unit | mumax3 identifier |
|---|---|---|---|
| γ | gyromagnetic ratio | rad s⁻¹ T⁻¹ | `GammaLL` (default 1.7595e11; γ/2π = 28.0 GHz/T) |
| B | applied field, B = µ0H | T | `B_ext` (always tesla) |
| Ms (µ0Ms) | saturation magnetisation | A/m (T) | `Msat` |
| A | exchange stiffness | J/m | `Aex` |
| Ku, B_K = 2Ku/Ms | uniaxial anisotropy and its field | J/m³, T | `Ku1`, axis `anisU` |
| Kc1 | first cubic anisotropy constant | J/m³ | `Kc1`, axes `anisC1`, `anisC2` |
| D | interfacial DMI (volume-averaged) | J/m² | `Dind` |
| α | Gilbert damping | – | `alpha` |
| ω_M = γµ0Ms, ω_H = γB_int | characteristic angular frequencies | rad/s | – |
| λ_ex = 2A/(µ0Ms²) = l_ex² | exchange length squared | m² | – |

- Every formula below uses fields in tesla (B = µ0H). Where H in A/m is meant, it is written as H. To convert: 1 mT = 10 Oe = 795.8 A/m.
- mumax3 integrates the Landau–Lifshitz form ∂m/∂t = −γ/(1+α²)·[m×B_eff + α m×(m×B_eff)], which is the Gilbert equation with γ = `GammaLL`. γ itself needs no correction (01-units-and-magnitudes.md), and a field-swept resonance position is unshifted. Damped *free* precession, however, runs at ω/(1+α²) and decays at αω/(1+α²) (sphere). This is below 0.25 % for α ≤ 0.05 and 1 % at α = 0.1. It is 50 % at α = 1, so never measure frequencies with a relaxation-style α.

## 1. Uniform mode (Kittel)

**General form.** The body is uniformly magnetised along z ∥ B, with demagnetising factors N_x, N_y, N_z and anisotropy stiffness fields B_a,x and B_a,y:

f = (γ/2π)·√(B₁B₂), with B₁ = B + µ0(N_x − N_z)Ms + B_a,x and B₂ = B + µ0(N_y − N_z)Ms + B_a,y

For a uniaxial easy axis along z (∥ B), B_a = +2Ku/Ms in both brackets. For an easy axis along a transverse direction i, B_a,i = −2Ku/Ms.

| Geometry (B ∥ M, saturated) | f | Valid when |
|---|---|---|
| Sphere, no anisotropy | (γ/2π)·B | B > 0 |
| Sphere, easy axis ∥ B | (γ/2π)·(B + B_K) | M along the easy axis |
| Sphere, B ⊥ easy axis | (γ/2π)·√(B(B − B_K)) | B > B_K (saturated along the hard axis) |
| Film, B in-plane | (γ/2π)·√(B(B + µ0M_eff)) | no in-plane anisotropy; B saturates the film |
| Film, B in-plane ∥ in-plane easy axis | (γ/2π)·√((B + B_K∥)(B + B_K∥ + µ0M_eff)) | B_K∥ = 2Ku∥/Ms |
| (001) film, Kc1 > 0, B ∥ ⟨100⟩ | (γ/2π)·√((B + 2Kc1/Ms)(B + 2Kc1/Ms + µ0M_eff)) | B along a cubic easy axis |
| Film, B ∥ normal | (γ/2π)·(B − µ0M_eff) | B > µ0M_eff; also holds for PMA films (M_eff < 0) from B = 0 |
| Finite thin element | use the general form with prism N's (see the reversal chapter) | approximate only; the demag field is non-uniform |

**Effective magnetisation.** µ0M_eff = µ0Ms − 2K⊥/Ms (in T). K⊥ is the perpendicular uniaxial anisotropy: `Ku1` with `anisU` along the film normal, often interfacial with K⊥ = K_s/t. M_eff < 0 means the film has a perpendicular easy axis.
- To reproduce a measured M_eff, keep `Msat` = Ms and set `Ku1` = (µ0Ms/2)(Ms − M_eff); the demag field comes from the mesh. Never put M_eff into `Msat` (that changes every dipolar quantity, including DE group velocities and edge fields), and never add a "shape" Ku1 = −µ0Ms²/2 while demag is on (that counts it twice).

**Smit–Beljers (any orientation, single domain).** f = (γ/2π)·√(F_θθF_φφ − F_θφ²)/(Ms sinθ), with F the free-energy density (J/m³) evaluated at the equilibrium (θ, φ). Use it when B is not along an axis, or when M is canted below saturation. It is singular at θ = 0, so choose the polar axis away from M.

**Validity and accuracy.** Exact (to discretisation error, ≪1 %) for ellipsoids and for infinite films (mumax3 with `SetPBC`). In finite, non-ellipsoidal elements the main mode shifts, typically by several % to tens of %, and edge modes appear below it when B is in-plane, because the internal field is reduced at edges perpendicular to B.
**Most common misuse**: using the applied B where the internal field and the equilibrium angle matter, i.e. in unsaturated or canted states, for example a PMA film with an in-plane B below µ0|M_eff|.

**Typical values.** Py film (µ0Ms ≈ 1.0 T): 2.8, 6.4, 9.3 and 13.8 GHz at 10, 50, 100 and 200 mT in-plane. YIG film (µ0Ms ≈ 0.176 T): 1.2, 3.0, 4.7 and 7.7 GHz at the same fields. An in-plane film with no anisotropy has f → 0 as B → 0.

## 2. Linewidth and damping

**Field-swept FMR** (fixed f; M ∥ B; Gilbert damping; Lorentzian in B):

µ0ΔH_FWHM = µ0ΔH₀ + 4παf/γ  [T]   ⇔   ΔH_FWHM = ΔH₀ + 4παf/(µ0γ)  [A/m]

- HWHM is half of this; the peak-to-peak width of the derivative (lock-in) signal is ΔH_pp = ΔH_FWHM/√3. Example: α = 0.01 at 10 GHz gives a Gilbert part µ0ΔH_FWHM = 7.1 mT; α = 1e-4 gives 0.071 mT.
- For collinear M ∥ B this field linewidth does not depend on geometry (sphere, in-plane or perpendicular film), because damping enters as B → B + iαω/γ in both stiffness fields.
- ΔH₀ is inhomogeneous broadening: zero for an ideal simulated film, finite with grains, edges or unresolved modes. Two-magnon scattering (common in in-plane films) makes ΔH(f) nonlinear and is not described by α.

**Ringdown at fixed B** (free precession, amplitude ∝ e^{−Γt}):

Γ = (αγ/2)(B₁ + B₂)  [s⁻¹]   (B₁, B₂ are the two stiffness fields of the Kittel product)

| Case | Decay rate Γ | Remark |
|---|---|---|
| Sphere, perpendicular film (B₁ = B₂) | Γ = αω | circular precession |
| In-plane film | Γ = αγ(B + µ0M_eff/2) = αω·(B + µ0M_eff/2)/√(B(B + µ0M_eff)) | ellipticity factor ≥ 1 |
| General | Γ = Δω_HWHM = (∂ω/∂B)·µ0ΔH_HWHM | converts field linewidth to frequency linewidth |

For µ0M_eff = 1 T the ellipticity factor is 3.6, 2.4, 1.8 and 1.15 at B = 20, 50, 100 and 500 mT. The lifetime is τ = 1/Γ; the power |m|² decays at 2Γ.

**Spectral widths of e^{−Γt}cos ωt.** The power spectrum |FFT|² is Lorentzian with HWHM Γ (rad/s), so Δf_FWHM = Γ/π; the absorptive Im χ has the same FWHM; the amplitude spectrum |FFT| is √3 times wider. Always state which spectrum a width was read from.

**Extracting α.**

| Data | Formula | Note |
|---|---|---|
| µ0ΔH_FWHM at several f | slope of µ0ΔH_FWHM against f = 4πα/γ | preferred: the intercept separates ΔH₀ |
| Ringdown, sphere or perpendicular film | α = Γ/ω | |
| Ringdown, in-plane film | α = Γ/[γ(B + µ0M_eff/2)] | **not** Γ/ω, which is too large by the ellipticity factor |
| Power-spectrum FWHM Δf, in-plane film | α = πΔf/[γ(B + µ0M_eff/2)] | sphere or perpendicular film: α = Δf/(2f) |

Typical room-temperature α (sample-dependent ranges): YIG 1e-5–1e-4 (bulk, thick films) and 1e-4–1e-3 (nm films); Py 0.005–0.01; CoFeB 0.003–0.02; ultrathin films next to a heavy metal (spin pumping) 0.02–0.2.

## 3. Thin-film spin-wave dispersion (Kalinikos–Slavin, lowest order)

**Assumptions.** Infinite saturated film of thickness d, in-plane wavevector k, unpinned surface spins, lowest thickness mode n = 0, kd ≲ 1, linear regime. θ is the angle of M from the film normal; φ is the angle between k and the in-plane projection of M.
ω_H = γB_int, where B_int is the static internal field along M: in-plane B_int = B (+B_K∥); perpendicular B_int = B − µ0M_eff.

**Kalinikos–Slavin (n = 0).**

ω² = (ω_H + ω_Mλ_ex k²)(ω_H + ω_Mλ_ex k² + ω_M F)

F = P + sin²θ·[1 − P(1 + cos²φ) + ω_M P(1 − P) sin²φ/(ω_H + ω_Mλ_ex k²)],   P = 1 − (1 − e^{−kd})/(kd) ≈ kd/2 for kd ≪ 1

| Mode | Geometry | ω² | Dipolar v_g at small k |
|---|---|---|---|
| Backward volume (BV) | M in-plane, k ∥ M | (ω_H + ω_ex)(ω_H + ω_ex + ω_M(1 − P)) | −ω_Hω_M d/(4ω) < 0 |
| Damon–Eshbach (DE) | M in-plane, k ⊥ M | (ω_H + ω_ex)(ω_H + ω_ex + ω_M) + ω_M²P(1 − P) | +ω_M²d/(4ω) |
| Forward volume (FV) | M ⊥ film | (ω_H + ω_ex)(ω_H + ω_ex + ω_M P) | +ω_Hω_M d/(4ω) ≈ ω_M d/4 |
| Exchange-dominated | ω_ex ≫ dipolar terms | ω ≈ ω_H + ω_ex (+ an O(ω_M) offset) | 2γ(2A/Ms)k |

**Exchange term.** ω_ex = ω_Mλ_ex k² = γ(2A/Ms)k², which is a field B_ex = (2A/Ms)k². For Py it is 0.13 T (+3.6 GHz) at λ = 100 nm and 0.51 T (+14 GHz) at λ = 50 nm.

**Accuracy of KS against exact or full micromagnetics.**
- Without exchange, the exact DE result is ω² = ω_H(ω_H + ω_M) + (ω_M²/4)(1 − e^{−2kd}).
- The KS dipolar term P(1 − P) is 1.5 %, 4 % and 8 % high at kd = 0.1, 0.3 and 1, and is qualitatively wrong for kd ≳ 2. Use the exact DE form for thick films; in that limit DE waves become surface waves with ω → ω_H + ω_M/2.
- **Most common misuse**: applying KS to unsaturated textures or to strips narrower than a few wavelengths. Strips have quantised width modes and a non-uniform internal field.

**Propagation length.** L_d = v_g/Γ. For 20 nm Py, DE waves at 10 GHz have v_g ≈ 2.5 km/s and, with α = 0.008, L_d ≈ 3 µm. YIG reaches the mm range.

**Perpendicular standing spin waves (PSSW).** These have k∥ = 0 and unpinned surfaces, with k_n = nπ/d (n = 1, 2, …) and B_ex,n = (2A/Ms)(nπ/d)².
- In-plane: f_n = (γ/2π)·√((B + B_ex,n)(B + B_ex,n + µ0M_eff)).
- Perpendicular: f_n = (γ/2π)·(B − µ0M_eff + B_ex,n).
- For Py, B_ex,1 is 0.80, 0.13 and 0.032 T for d = 20, 50 and 100 nm. The corresponding f₁ at 50 mT in-plane is about 35, 13 and 8.4 GHz.
- Surface pinning, for example `Ku1` placed only in the surface-layer regions, shifts k_n away from nπ/d.
- A uniform drive couples only to modes with a net moment. With free surfaces every n ≥ 1 profile cos(nπz/d) has zero net moment, so none is excited; symmetric pinning makes odd n visible. In a simulation, drive one surface layer (its own region) to excite all n.
- PSSW need several cells across d. A single-layer mesh (N_z = 1) has none.

**Interfacial-DMI nonreciprocity (Moon et al. 2013).** This applies to M in-plane and k ⊥ M (DE geometry), with D uniform across a thin film:

f(k) = f₀(|k|) ± (γ/2π)(2D/Ms)·k   ⇒   Δf = f(+k) − f(−k) = 2γDk/(πMs)   [D in J/m², k in rad/m, Ms in A/m]

- Δf ∝ sinφ: it is largest for k ⊥ M, zero for k ∥ M, and zero for perpendicular M.
- Example: D = 1 mJ/m², Ms = 1 MA/m and k = 10 rad/µm give Δf ≈ 1.1 GHz. Reversing M or D flips the sign.
- `Dind` is a volume quantity. An interfacial D_s (pJ/m) on a film of thickness t corresponds to `Dind` = D_s/t.
- Thick or asymmetric films also have a dipolar DE asymmetry. Compare against a run with `Dind` = 0 before attributing an asymmetry to DMI.
- This is also the standard way to fit D: the slope of Δf against k is 2γD/(πMs).

## 4. Sanity checks

| Check | Expected result | If it fails |
|---|---|---|
| One cubic cell (N = 1/3 on every axis), no anisotropy | f = 28.0 GHz/T × B to < 0.1 % | wrong `GammaLL`, units (mT vs T), or the FFT/time axis |
| Same cell with `Ku1`, `anisU` ∥ B | f = (γ/2π)(B + 2Ku1/Msat) | anisotropy axis or sign |
| In-plane film with PBC, several B | (f/(γ/2π))² − B² = µ0M_eff·B, a straight line through 0 with µ0M_eff = µ0Ms − 2Ku1/Ms | finite-size demag (PBC too small), unsaturated state |
| α recovered from the ringdown of an infinite film | equals the input `alpha` to about 1–2 % when the ellipticity factor is used | used Γ/ω; record too short; nonlinear amplitude |
| f(k) − f(0) at large k | → (γ/2π)(2A/Ms)k² | `Aex` error, or a mesh too coarse (kΔx > 0.5) |
| BV slope | ∂f/∂k < 0 at small k | k and M axes swapped |
| DE without DMI | f(+k) ≈ f(−k) in thin symmetric films | spurious DMI or a symmetry-breaking geometry |
| Halve the excitation amplitude | f and Γ unchanged; amplitude halves | nonlinear regime (foldover, Suhl instability) |

Order-of-magnitude anchors: 28 GHz/T; Py at 100 mT in-plane ≈ 9 GHz; a ringdown with α = 0.01 at 10 GHz lasts about 1–4 ns, depending on the ellipticity factor.

## 5. How a simulation measures it

**1. Ground state first.**
- `Relax()` (or `Minimize()`) at the bias field. Relaxers switch precession off and do not use `alpha`, and they disable thermal noise.
- Then set the physical `alpha` and excite with `Run()`.
- For an "infinite film", use `SetPBC(px, py, 0)` and check that the k = 0 frequency has converged with respect to the repetition count.

**2. Excitation.**

| Method | mumax3 form | Excites | Caveats |
|---|---|---|---|
| Ringdown (small tilt) | after `Relax()`, set `m = Uniform(...)` a few degrees off equilibrium; or apply a short field pulse, then `B_ext` = bias | k = 0 modes; clean exponential decay | a tilt of `Uniform` only suits uniform states; keep the cone angle ≲ 1–3° |
| Short field pulse | `B_ext = vector(Bx, 0, b0*heaviside(tp - t))` | all modes up to ≈ 1/tp with a net moment | spectral weight is not flat |
| Sinc pulse | `B_ext = vector(Bx, 0, b0*sinc(2*pi*fc*(t - t0)))` | flat drive for f < fc | mumax3 `sinc(x)` = sin x / x (no π); choose t0 ≈ 5–10/fc so the truncation at t = 0 is small; b0 ≲ 0.1–1 mT |
| Local antenna | `B_ext.SetRegion(r, vector(Bx, 0, b0*sinc(...)))`, or `B_ext.Add(mask, f(t))` | propagating waves with k up to ~2π/w for antenna width w | `SetRegion` **replaces** the uniform value in region r, so include the bias in the expression, or use `Add` (mask × f(t), added on top) |
| CW drive | `b0*sin(2*pi*f*t)` | one f: steady-state mode profile, decay length | run ≳ 3–5/Γ before analysing |

- A spatially uniform drive excites only modes with a net dynamic moment. Use local or gradient drives for antisymmetric modes.
- Closures capture only `t` (grammar.md). Constants such as b0 and fc are frozen when the expression is declared.

**3. Sampling and FFT.**
- The sampling interval Δt_s is the `TableAutoSave` or `AutoSave` period, not the solver step. The Nyquist frequency 1/(2Δt_s) must be ≥ 2–3 × the highest mode; anything above it folds down (a 36 ps period sampled every 100 ps is aliased).
- The resolution is δf = 1/T_rec, so 10 ns gives 100 MHz. For a resolved line you need δf ≪ Γ/π.
- With adaptive steps a save happens at the first step after each multiple of the period; only the end time of `Run()` is hit exactly. Interpolate onto a uniform grid using the table's t column, or use `FixDt` dividing the period.
- Subtract the static (time-averaged) part before the FFT. Use a Hann window only when the signal has not decayed by the end of the record; a window broadens lines, so never read α from a windowed spectrum. Zero-padding interpolates the spectrum; it does not add resolution.

**4. Mode maps.**
- Save `m` (or one component or one layer, via `m.Comp(i)`, `CropLayer`, `CropRegion`) with `AutoSave` at Δt_s.
- FFT each cell along time, then map |m̂(r, f_peak)| and its phase.
- Data volume per snapshot is N_cells × components × 4 B. Crop to keep it manageable.

**5. Dispersion maps.**
- Use a sinc excitation in time from a narrow antenna, or a sinc in both space and time.
- Record one component along a line of cells parallel to k, then 2D-FFT m(x, t) → |m̂(k, f)|².
- k resolution is 2π/L and k_max = π/Δx. Overlay the KS or DE curves.
- The finite-difference Laplacian replaces k² by (4/Δx²)sin²(kΔx/2). The exchange term is then 2 % low at kΔx = 0.5, 8 % low at kΔx = 1 and 19 % low at kΔx = π/2.
- For quantitative dispersion keep kΔx ≤ 0.5 (λ ≥ about 12 cells).

**6. Absorbing boundaries.**
- Ramp `alpha` smoothly (quadratically or exponentially) from the physical value to about 0.5–1 over ≳ 2–3 of the longest wavelengths.
- Build the ramp from about 10–30 strip regions (`DefRegion`, `alpha.SetRegion`; at most 256 regions). An abrupt step in α reflects waves.
- A reflection shows up as a standing-wave modulation of |m̂| with period λ/2. Confirm by doubling the ramp length.
- At T > 0 the ramp also raises the thermal noise locally, as the fluctuation–dissipation theorem requires.

**7. Reading f and Γ from a time trace.** Analyse only after the drive has ended (t > t0 + a few periods).
1. **Damped-sinusoid fit**: y = A e^{−Γt}cos(2πft + φ) + c₀ (+ c₁t) by nonlinear least squares. Seed f from the FFT peak and Γ from the slope of the log envelope. Take error bars from the covariance, and check the residuals for a second (beating) mode.
2. **Zero crossings**: subtract the baseline and interpolate the upward crossings. The mean spacing gives the period, independent of the envelope. Γ comes from ln(peak amplitude) against time.
3. **Hilbert envelope**: form the analytic signal y + iH[y]. The slope of ln|env| gives −Γ. (1/2π)·d(unwrapped phase)/dt is the instantaneous frequency, which exposes amplitude-dependent shifts and beating. Drop 1–2 periods at each end, and band-pass first if several modes are present.
4. **Several modes**: fit a sum of damped sinusoids (matrix-pencil or Prony-type methods), or band-pass each mode and repeat steps 1–3.

Record ≥ 2–3 decay times for Γ to about 1 %, while keeping the signal well above the solver noise (`MaxErr`).

## 6. Common mistakes

- Mixing units: putting H in Oe or A/m into a B formula, or µ0Ms into an Ms slot. γ/2π = 28.0 GHz/T = 2.80 MHz/Oe.
- α = Γ/ω or Δf/(2f) for in-plane films. Both overestimate α by the ellipticity factor (2.4× for Py at 50 mT).
- Reading a width from |FFT| instead of the power spectrum, or from a record whose 1/T_rec is comparable to the line width.
- Large-amplitude excitation: nonlinear frequency shift and spin-wave instabilities. Always run the amplitude-halving test.
- Leaving the large relaxation-style `alpha` on during a dynamics run. Relaxers do not need it.
- Finite-size films treated as infinite: Kittel with N_z = 1 applied to a small mesh without PBC, or an edge mode mistaken for the main mode.
- Aliasing from a long save period. Sample at ≤ 1/(5 f_max).
- Expecting PSSW from a single-layer mesh, or a DMI shift from k ∥ M.
- An antenna made with `B_ext.SetRegion(...)` that silently drops the bias field in that region.
- KS used for kd ≫ 1 or in unsaturated states. Kittel used with the applied field below saturation.
- A cell too coarse for the wavelengths studied (kΔx > 0.5), or `Msat` set to M_eff.

## 7. References

- C. Kittel, "On the theory of ferromagnetic resonance absorption", Phys. Rev. 73, 155 (1948).
- J. Smit and H. G. Beljers, Philips Res. Rep. 10, 113 (1955): resonance frequency for arbitrary free energy.
- R. W. Damon and J. R. Eshbach, "Magnetostatic modes of a ferromagnet slab", J. Phys. Chem. Solids 19, 308 (1961).
- B. A. Kalinikos and A. N. Slavin, "Theory of dipole-exchange spin wave spectrum for ferromagnetic films with mixed exchange boundary conditions", J. Phys. C 19, 7013 (1986).
- A. G. Gurevich and G. A. Melkov, *Magnetization Oscillations and Waves* (CRC Press, 1996).
- D. D. Stancil and A. Prabhakar, *Spin Waves: Theory and Applications* (Springer, 2009).
- J.-H. Moon et al., "Spin-wave propagation in the presence of interfacial Dzyaloshinskii–Moriya interaction", Phys. Rev. B 88, 184404 (2013).
- S. S. Kalarickal et al., "Ferromagnetic resonance linewidth in metallic thin films: comparison of measurement methods", J. Appl. Phys. 99, 093909 (2006).
- A. Vansteenkiste et al., "The design and verification of MuMax3", AIP Advances 4, 107133 (2014).
