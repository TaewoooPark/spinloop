# Inverse problems: fitting parameters with an expensive simulator

Use this chapter for estimating material or model parameters (Ms, A, K, D, α, β, P, θ_SH, …) from data when every model evaluation is a mumax3 run of seconds to minutes: the χ² objective, Levenberg–Marquardt with finite-difference Jacobians, identifiability, local minima and regime changes, model error, uncertainty reporting, validation and bookkeeping.
It is a method chapter. The closed forms used for starting values and sanity checks are in the other chapters.

## 1. Objective: weighted least squares

χ²(p) = Σᵢ rᵢ², rᵢ = (yᵢ − fᵢ(p))/σᵢ, with data yᵢ, simulated observables fᵢ(p), N data, P free parameters, ν = N − P degrees of freedom, χ²_red = χ²_min/ν.

- σᵢ is the total 1σ error of datum i: σᵢ² = σ²_meas + σ²_sim (simulation scatter and discretisation, §3). Without σ, χ² has no scale, and mixing data kinds (GHz, mT, m/s) lets the kind with the largest numbers dominate.
- Correlated errors (one calibration shared by a whole sweep): χ² = rᵀC⁻¹r with the data covariance C.
- Correct model, correct σ, Gaussian noise: χ²_min ≈ ν ± √(2ν), i.e. χ²_red ≈ 1 ± √(2/ν). ν = 20 → χ² ≈ 14–26; ν = 100 → 86–114.

| χ²_red | residuals | meaning |
|---|---|---|
| ≈ 1 | random sign, no trend | consistent: report σ from the covariance (§9) |
| ≫ 1 | structured: a trend, or one sign per data kind | model discrepancy or a protocol mismatch (§6) |
| ≫ 1 | random | σ underestimated, or a local minimum (§5) |
| ≪ 1 | small and smooth | σ overestimated, or data not independent (oversampled curves) |

## 2. Gauss–Newton and Levenberg–Marquardt

Weighted Jacobian Jᵢⱼ = (∂fᵢ/∂pⱼ)/σᵢ (N × P). Linearising f(p + δ) ≈ f(p) + Jδ replaces the Hessian of χ²/2 by JᵀJ (good when the residuals are small or f is nearly linear):

- Gauss–Newton: JᵀJ δ = Jᵀr. Fast near the minimum; erratic far from it or when JᵀJ is nearly singular.
- Levenberg–Marquardt (LM): (JᵀJ + λ·diag(JᵀJ)) δ = Jᵀr. Small λ → Gauss–Newton; large λ → a short gradient step scaled per parameter.
  - Accept the step if χ² falls (λ ÷ 3–10); otherwise λ × 3–10 and re-solve with the same J, so a rejection costs one evaluation, not a new Jacobian. In narrow curved valleys raise λ quickly and lower it slowly ("delayed gratification", Transtrum et al. 2011).
- Scale the parameters:
  - θ = ln p for positive quantities that may be off by factors (Ms, A, K_u, α, P, |θ_SH|): ∂f/∂θ = p·∂f/∂p, and σ_θ is the relative error of p.
  - Signed quantities (D, β, field offsets): divide by a reference value so that every variable is of order one.
  - Impose bounds by transformation (log, or logit between min and max), not by clipping. A parameter that ends on a bound has no valid σ.
- Stop when accepted steps lower χ² by less than ~0.1·max(1, χ²_red), or when every |δⱼ| < ~0.1σⱼ: further steps move the parameters by less than their uncertainty.

## 3. Finite-difference Jacobians, the noise floor, Broyden updates

A Jacobian costs P evaluations (forward differences) or 2P (central). The step h trades truncation error against the observable's noise ε_f (ε_rel = ε_f/|f|; the h/p forms assume f varies on the scale of p itself):

| scheme | error of ∂f/∂p (magnitudes) | best step | relative error of the derivative |
|---|---|---|---|
| forward | (h/2)·f″ + 2ε_f/h | h ≈ 2√(ε_f/f″), i.e. h/p ≈ 2√ε_rel | ≈ 2√ε_rel |
| central | (h²/6)·f‴ + ε_f/h | h ≈ (3ε_f/f‴)^(1/3), i.e. h/p ≈ (3ε_rel)^(1/3) | ≈ ε_rel^(2/3) |

What sets ε_f in mumax3 (orders of magnitude; measure it for your own observable):

| source | size | remedy |
|---|---|---|
| float32 GPU arithmetic | ~1e-7 per operation, ~1e-6 in averages | negligible unless h/p < ~1e-3 |
| adaptive step (`MaxErr`), `Relax()`/`Minimize()` stopping rules | ~1e-6–1e-4 relative; the accepted step sequence jumps as p changes | tighter `MaxErr` or `RelaxTorqueThreshold`; `FixDt` for dynamics |
| quantised extraction: FFT bin 1/T_run, field step of a loop, cell size, threshold-crossing time | a whole bin or step; f(p) becomes a staircase | fit or interpolate: Lorentzian or parabolic peak, interpolated switching field, tanh fit of a wall profile |
| thermal noise (`Temp` > 0) | ensemble σ/√N_seeds | the same `ThermSeed` at p and p + h (common random numbers); many seeds |
| geometry that snaps to the grid (width, thickness, notch) | a staircase in the geometric parameter | keep the geometry fixed; never fit it finer than one cell |

- Measure ε_f before fitting: repeat the base evaluation, then evaluate p ± h for two or three values of h. Choose h with |Δf| ≳ 100ε_f. For simulator outputs this is typically h/p = 1–5 %, never the 1e-8 of double-precision codes.
- Forward and backward differences must agree to ~10 %. If they do not, h is too large or a regime boundary lies inside [p − h, p + h] (§5).
- Mesh, solver, `MaxErr`, run length, seeds and analysis code must be identical for every evaluation of a fit. Changing any of them changes the model.
- A run that physics guarantees cannot depend on pⱼ (a `Relax()` state does not depend on α) need not be repeated for column j.

Broyden update, with no extra evaluation (it reuses the run at the accepted point): J ← J + (Δr̃ − Jδ)δᵀ/(δᵀδ), where Δr̃ᵢ = [fᵢ(p + δ) − fᵢ(p)]/σᵢ.
- It corrects J only along δ. Refresh the full finite-difference Jacobian after two rejections in a row, when χ² stalls, or every ~P updates.
- Always recompute a finite-difference Jacobian at the final point. σ and correlations from a Broyden-updated J are unreliable.

## 4. Identifiability: what the data actually fix

Fisher information F = JᵀJ with the weighted J (= JᵀWJ with the unweighted Jacobian and W = diag(1/σᵢ²) or C_data⁻¹; Gaussian errors); covariance C = F⁻¹ at the minimum (linearised); σⱼ = √Cⱼⱼ; correlation ρⱼₖ = Cⱼₖ/(σⱼσₖ).

- Eigenvectors of F in log-parameter space: each eigen-combination is fixed to ±1/√λₖ (relative). The smallest-λ eigenvector names the product or ratio of parameters that the data cannot fix. Eigenvalues spread over many decades ("sloppy" models, Transtrum, Machta & Sethna) are the norm, not a bug.
- |ρ| > 0.9: the data fix a combination better than either parameter. |ρ| > 0.99, or cond(F) > ~1e6: practically non-identifiable. Fix one parameter from independent data, reparametrise to the combination, or add data.
- Sensitivity matrix Sᵢⱼ = (pⱼ/σᵢ)·∂fᵢ/∂pⱼ: the change of datum i, in units of its σ, per unit change of ln pⱼ. A column with all |S| ≪ 1 → that parameter is unconstrained; two nearly parallel columns → a degenerate pair. It costs P + 1 evaluations: compute it before the fit (ideally before the experiment) and use it to say which measurement constrains which parameter.

Common micromagnetic degeneracies. The data depend on the parameters only through a group: a length (Δ = √(A/K_eff), l_ex = √(2A/µ0Ms²)), an energy (K_eff, wall energy 4√(A·K_eff)), a field in T (µ0M_eff, 2K/Ms) or a ratio (β/α, κ = πD/(4√(A·K_eff))).

| data | fix | cannot separate | break with |
|---|---|---|---|
| Kittel FMR f(B) of a film, in-plane or normal | γ and µ0M_eff = µ0Ms − 2K_u⊥/Ms (T) | Ms, K_u⊥ | Ms from magnetometry |
| K_eff of a PMA film at one thickness t | K_eff·t = (K_v − µ0Ms²/2)·t + K_s | K_v, K_s | a thickness series |
| static wall width or profile | Δ = √(A/K_eff) | A, K_eff | wall energy 4√(A·K_eff): domain period, nucleation field |
| exchange spin waves f(k) | γ and 2A/Ms (exchange field (2A/Ms)k², T) | A, Ms | an independent Ms |
| field-driven wall velocity below Walker | mobility γΔ/α | Δ, α | Walker field B_W = αB_K/2 (T); FMR linewidth for α |
| STT wall velocity below Walker | βu/α ∝ βP/(αMs) | β, P, α | above-Walker ⟨v⟩ ≈ u, which fixes P/Ms |
| SOT-driven chiral wall at saturation | (π/2)γD/Ms | D, Ms | Ms; the in-plane field B_DMI = D/(MsΔ) (T) that stops the wall |
| skyrmion radius at one field | one combination of A, K_eff, D | A, K_eff, D | radius versus field, plus wall width or Ms |
| switching rates over a narrow rate or temperature range | E_b/k_BT and ln f₀, strongly anticorrelated | E_b, f₀ | decades of sweep rate or pulse length |

Designing an extra measurement:
- A candidate with sensitivity row s (from P + 1 evaluations, or from a closed form) adds information sᵀs: predict the new σ from (F + sᵀs)⁻¹ before running anything expensive. A row orthogonal to the sloppy eigenvector adds nothing; prefer the candidate that most raises the smallest eigenvalue (E-optimal) or det F (D-optimal).
- Typical breakers: a second geometry (field direction, thickness, width); another regime of the same experiment (above and below Walker, low and high field); a static datum next to a dynamic one; another k or mode; a temperature series.

## 5. Local minima, multistart and regime changes

- Multistart: 5–20 starts from a Latin-hypercube or Sobol design in log-parameter space within physical bounds. Run each for a few iterations (or on a coarse mesh), refine the best 2–3 on the production model, and report whether distinct starts reach the same p̂ within σ.
- Multiple minima are generic for oscillatory or multi-branch observables: mode assignment (which peak is which mode), interference in spin-wave transmission, phase wrapping, the number of domains or textures.
- Regime changes make χ² kinked or discontinuous: ground-state changes (single domain ↔ vortex ↔ multidomain; skyrmion ↔ stripe or collapse), Walker breakdown (a kink in v(B) or v(J)), a new reversal path (coherent → nucleation), switching or not within the run time, a texture expelled through an edge, history-dependent metastable branches, mode crossings.
- Signs of a regime change:
  - χ² jumps for a parameter change smaller than h; forward and backward differences differ in sign or by orders of magnitude.
  - The residuals of one data kind flip sign abruptly while the others vary smoothly.
  - LM rejects step after step, with λ growing, although |Jᵀr| stays large.
  - A state label changes between evaluations. Record for every run `ext_topologicalcharge`, the number of walls, the final ⟨m⟩, the mode identity, switched or not, and compare with the state in which the data were taken.
- Handling: restrict the fit to the data's regime (bounds, or reject evaluations whose state label does not match); treat categorical outcomes (switched or not, state type) as constraints, not residuals; reproduce the experiment's protocol (field history, initial state) in every run; never take a difference across a transition.

## 6. Model discrepancy versus noise

- Noise: random signs, |rᵢ| ~ 1, no trend with the control variable (field, frequency, current, size). Runs test: N residuals ordered along the control variable give ≈ N/2 + 1 ± √N/2 runs of one sign if they are noise; far fewer runs → structure.
- Systematic error: a trend or curvature of r against the control variable, one sign for a whole data kind, or two kinds pulling in opposite directions so that each misfits by several σ.
- Why a wrong model gives confident wrong parameters: C = (JᵀJ)⁻¹ measures only the curvature of χ² and shrinks like 1/N, while the bias does not shrink. With many precise data the quoted σ can be ten times smaller than the real error. Scaling by √χ²_red helps only when the misfit looks like noise.
- Tests: fit each data kind (or field range) alone and compare, since disagreement beyond the combined σ means no single parameter set explains all data; predict held-out data; re-evaluate f(p̂) on a finer mesh, with a longer run and a smaller `MaxErr`, where the shift must be ≪ σᵢ (otherwise the discretisation itself is a systematic error).

| data kind | residual pattern | usual cause |
|---|---|---|
| FMR f(B) | grows linearly with B | γ (g-factor) or field calibration |
| FMR f(B) | large only at low B | unsaturated state, domains, missing in-plane anisotropy |
| FMR f(B) | constant offset | M_eff, exchange bias or another internal field missing |
| hysteresis | simulated coercivity far above the measured one | Brown's paradox: the model lacks defects, edge roughness, grains, thermal activation; fitting K to H_c then drives K far too low |
| hysteresis | rounded approach to saturation not reproduced | dispersion of anisotropy axes, grains |
| wall velocity v(B), v(J) | low-drive points far below the model | creep or pinning regime: fit only the flow regime, or add disorder |
| wall velocity | mismatch above Walker | 2D wall dynamics (tilt, vortex or antivortex nucleation), strip width |
| skyrmion or bubble size | misfit at small radii | cell too coarse for the core; pinning, granularity |
| spin-wave f(k) | error grows with k | cell too coarse: the finite-difference exchange term is low by ≈ (kΔx)²/12 (relative) |
| spin-wave f(k) | misfit at small k | finite-width modes, dipolar terms, finite size or PBC |
| any, versus temperature | trend with T | Ms(T), A(T), K(T) not modelled |

Remedies: correct the model; add explicit nuisance parameters (field offset, scale factor, background) and report them; or add a stated model-error term to σ. Never drop misfitting points silently.

## 7. Starting values from closed forms

- Take starts from the closed forms in the other chapters: γ and M_eff from Kittel, α from the linewidth slope, Δ and the wall energy from wall formulas, A/Ms from the spin-wave dispersion, K from saturation fields, u = PgµBJ/(2eMs) for spin torque, D from the DMI field.
- Evaluate the simulator once at the start and inspect the residuals per data kind before iterating. This catches units, signs and the wrong regime.
- A closed form is an approximation whose bias can exceed the noise: Kittel assumes a uniform mode in an infinite film (edges and finite size shift the frequencies); the 1D wall model ignores wall tilt and 2D structure; Stoner–Wohlfarth switching fields exceed real coercivities several-fold; thin-film demagnetisation ignores the finite lateral size.
- Use closed forms to start and to sanity-check, not as the final model when the data are more precise than the approximation.
- LM usually converges from a start within a factor ~1.5–2 that lies in the right regime; otherwise use multistart (§5).

## 8. Sequential versus joint identification

- Sequential fitting is safe when the problem is nearly block-triangular: the stage-1 data fix p₁ precisely, and the stage-2 data barely respond to p₁ within σ₁. Example chain: Ms from magnetometry → γ and M_eff from FMR → α from linewidths → β and P from current-driven motion.
- The danger: a frozen parameter carries its bias into every later stage, correlated later parameters absorb it, and the later σ omit its uncertainty. The result looks precise and is wrong.
- Rule: use sequential fits to obtain starting values, then finish with one joint fit of all free parameters to all data. If the joint fit moves a previously frozen parameter by more than its σ, the sequential result was biased.
- A parameter that must stay fixed: refit with p₁ ± σ₁ and add the resulting shifts of the other parameters in quadrature.

## 9. Uncertainty reporting

- σⱼ = √Cⱼⱼ with C = (JᵀJ)⁻¹ from a fresh finite-difference Jacobian at p̂ (for log parameters, σ is relative).
- χ²_red > 1 with noise-like residuals: multiply every σⱼ by √χ²_red (equivalent to scaling all σᵢ). With structured residuals, also quote the spread between subset fits (§6) as a systematic error.
- Profile likelihood for non-linear, bounded or strongly correlated parameters: fix pⱼ on a grid, re-minimise over the others (warm starts), and plot χ²_min(pⱼ).
  - Intervals: Δχ² = 1 (68 %) and 3.84 (95 %) for one parameter; Δχ² = 2.30 (68 %) for a joint region of two parameters; multiply the thresholds by χ²_red if σ was rescaled. A flat or one-sided profile means the covariance σ is meaningless (not identifiable).
- Bootstrap (resample data or residuals, refit 100–1000 times) only when a fit is cheap. With an expensive simulator, profile the one or two parameters that matter instead.
- Report p̂ ± σ (σ to two significant digits), χ²_min, ν, χ²_red and whether σ was scaled, every |ρ| > 0.9 together with the well-determined combinations, the fixed parameters with their assumed values, and the model assumptions (mesh, T = 0, idealised geometry).

## 10. Parameter-recovery tests on synthetic data

1. Choose p_true in the data's regime. Simulate y_syn = f(p_true) at exactly the real data points, with the real protocol.
2. Noise-free: from a typical start (e.g. a factor 1.5 off), the fit must return p_true to ≪ σ with χ² ≈ 0. Otherwise the optimiser, the finite-difference steps or the observable extraction is broken.
3. Add Gaussian noise with the real σ (several realisations if affordable). Expect χ² ≈ ν and z = (p̂ − p_true)/σ̂ scattered like N(0, 1). |z| > 3, or σ̂ smaller than the scatter of p̂ across realisations → bias or optimistic σ.
4. A huge σ or |ρ| ≈ 1 in this test means the design cannot identify the parameter. Change the design before spending GPU time on the real fit, or before measuring.

Generating and fitting with the identical model and mesh (the "inverse crime") tests the optimiser, not model error. To see the discretisation bias, generate y_syn on a finer mesh or with longer runs, and check that the recovered p̂ stays within σ of p_true.

## 11. Bookkeeping

- Record every evaluation: the full parameter vector at full precision (Python `repr`), every fixed input (mesh, solver, `MaxErr`, seeds, run times), the script and template hash, the engine build and GPU, the raw outputs, the extracted observables, state labels and wall time.
- One Jacobian = one base point plus P perturbed points, with everything else identical. Never combine runs from different parameter sets, templates, meshes or engine builds in one Jacobian or one χ².
- Scripts are immutable. Generate them from a template; a template change is a new model version with a new cache; never edit a script that has run. Cache key = (template hash, parameter vector, fixed inputs).
- Keep the optimiser state (p, λ, J, accepted and rejected steps, χ² history) on disk, so that a killed fit resumes exactly.
- Rerun the best point at the end: the observable must reproduce within ε_f (GPU reductions are not bit-identical across devices or builds).

## 12. Cost arithmetic and checklist

GPU time ≈ N_eval × (runs per evaluation) × (seconds per run) ÷ (runs in parallel).
- LM: 1 (start) + P (Jacobian; 2P if central) + 5–15 iterations × (1 + rejections) + Jacobian refreshes + P (final Jacobian). With Broyden updates most iterations cost one evaluation.
- Example: P = 3, 20 runs per evaluation, 30 s per run → 10 min per evaluation and 30 min per Jacobian. About 25 evaluations ≈ 4.2 h per fit; 5 starts ≈ 21 h; a 7-point profile at ~4 evaluations per point ≈ 4.7 h.
- Savings: skip runs that cannot depend on a parameter; run the independent Jacobian columns in parallel; run the multistart on a coarse mesh and finish on the production mesh (check the coarse → fine shift); fix the parameters that the sensitivity matrix shows are unconstrained.

Checklist:
1. Data with σ, including σ_sim. The simulation reproduces the protocol: field history, initial state, geometry, temperature.
2. Closed-form start; one evaluation; residuals per data kind sane (units, signs, regime).
3. Noise floor ε_f from repeats and small steps; h chosen (typically 1–5 %).
4. Sensitivity matrix at the start; identifiable set chosen; degenerate groups reparametrised or fixed.
5. Synthetic recovery test, noise-free and then noisy.
6. LM in scaled (log) parameters with Broyden updates; a fresh Jacobian at the end.
7. Diagnosis: χ² against ν ± √(2ν), residual patterns per kind, runs test, ρ, parameters at bounds.
8. Model check at p̂: finer mesh, longer run, smaller `MaxErr` → shift ≪ σ.
9. σ (× √χ²_red if χ²_red > 1); profiles for non-linear parameters; report with the assumptions.
10. Archive evaluations, templates and the optimiser log.

## Sanity checks

- χ²_min within ν ± 2√(2ν). Outside it, read §1 and §6 before quoting any σ.
- No parameter on a bound; no |ρ| > 0.95 without the combination stated.
- Finite-difference step: |Δf| ≫ ε_f, and forward and backward differences agree.
- At least two distinct starts reach the same p̂.
- p̂ is physically plausible (typical values in the other chapters). A fitted value far from an independent measurement (Ms against magnetometry, α against the FMR linewidth) signals a parameter compensating for missing physics.
- The synthetic recovery test passes at the real σ.

## Common mistakes

- No σ, or only the measurement σ while the simulated observable has its own scatter.
- A relative step of 1e-6–1e-8 (the derivative of noise) or of 20 % (a derivative across a regime change).
- σ and correlations taken from a Broyden-updated Jacobian.
- Quoting the covariance σ with χ²_red ≫ 1 and structured residuals.
- Freezing a parameter at a closed-form value and fitting the rest (§8).
- Fitting an ideal model to coercivities or to creep-regime velocities: confident, wrong parameters.
- Editing a template in the middle of a fit; mixing runs from different meshes, `MaxErr` values or engine builds.
- Treating categorical outcomes (switched or not, state type) as continuous residuals.
- Quoting individual σ for a pair with |ρ| ≈ 1 instead of the combination that the data fix.

## References

- W. H. Press, S. A. Teukolsky, W. T. Vetterling, B. P. Flannery, *Numerical Recipes*, 3rd ed., Cambridge University Press (2007), ch. 15 "Modeling of Data" (Levenberg–Marquardt, confidence limits from Δχ²).
- J. Nocedal, S. J. Wright, *Numerical Optimization*, 2nd ed., Springer (2006): least-squares methods, finite-difference derivatives, Broyden and quasi-Newton updates.
- K. Levenberg, Q. Appl. Math. 2, 164 (1944); D. W. Marquardt, J. Soc. Ind. Appl. Math. 11, 431 (1963).
- C. G. Broyden, Math. Comp. 19, 577 (1965).
- A. Tarantola, *Inverse Problem Theory and Methods for Model Parameter Estimation*, SIAM (2005).
- Y. Bard, *Nonlinear Parameter Estimation*, Academic Press (1974).
- M. K. Transtrum, B. B. Machta, J. P. Sethna, Phys. Rev. Lett. 104, 060201 (2010); Phys. Rev. E 83, 036701 (2011) — sloppy models, geometry of least squares, LM improvements.
- R. N. Gutenkunst et al., PLoS Comput. Biol. 3, e189 (2007) — universally sloppy parameter sensitivities.
- A. Raue et al., Bioinformatics 25, 1923 (2009) — identifiability from the profile likelihood.
- M. C. Kennedy, A. O'Hagan, J. R. Stat. Soc. B 63, 425 (2001) — model discrepancy in the calibration of computer models.
- B. Efron, R. J. Tibshirani, *An Introduction to the Bootstrap*, Chapman & Hall (1993).
- J. Kaipio, E. Somersalo, *Statistical and Computational Inverse Problems*, Springer (2005) — the "inverse crime".
- A. Aharoni, *Introduction to the Theory of Ferromagnetism*, 2nd ed., Oxford University Press (2000) — Brown's paradox.
- A. Vansteenkiste et al., AIP Advances 4, 107133 (2014) — mumax3 (single-precision GPU arithmetic, adaptive time stepping).
