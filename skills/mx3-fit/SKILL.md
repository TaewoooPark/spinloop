---
name: mx3-fit
description: >-
  Fit several unknown parameters at once to many measured numbers, each of
  which comes from a mumax3 simulation — least squares with
  Levenberg-Marquardt, resumable in time-boxed calls, with chi2, residuals,
  uncertainties and correlations at the end. Use for "fit Ms, Ku1 and alpha to
  these data", "identify the material parameters from several
  measurements", "least-squares fit of simulations to data", "inverse
  problem", "parameter estimation with error bars", "the fit needs a
  Jacobian", "how well do the data determine each parameter". For one
  parameter against one target use mx3-tune; for comparing a hysteresis
  loop use mx3-match.
---

# Fitting several parameters to many measurements

When every datum needs a simulation, a fit is expensive and long, and the
usual ways to lose it are bookkeeping, not mathematics: a step that was never
recorded, a Jacobian taken from mixed parameter sets, a batch killed half-way,
a parameter tuned alone while the others drift. `fit.py` does the loop:

- **Method**: Levenberg–Marquardt on χ² = Σ((model − data)/σ)².
  - A finite-difference Jacobian costs one evaluation per parameter.
  - Between full Jacobians, Broyden updates refresh it, so most steps cost a
    single evaluation.
  - When χ² stops falling, a final Jacobian at the best set gives σ and the
    correlations.
- **Bookkeeping**: every run is saved and every script kept. A call ends when
  its time budget does, and the next call continues the fit.

```
fit.py init   SPEC.json            writes the starting set's scripts (vet one), creates the state
fit.py step   SPEC.json --budget S runs for at most S seconds; call it again until it says done
fit.py status SPEC.json            where it stands
fit.py report SPEC.json            best set, chi2, residuals, sigma, correlations (also report.json)
fit.py eval   SPEC.json --set NAME=v,... --budget S    one parameter set by hand (recorded, cached)
```

Path: `python3 "${CLAUDE_PLUGIN_ROOT}/skills/mx3-fit/scripts/fit.py"`. The
docstring (`fit.py -h`) has the full spec format.

## Joint, not one at a time

When two parameters both move the same data, adjusting them one at a time
zig-zags along the valley and stops far from the minimum. It also never shows
that they are correlated. A joint fit uses all data for all parameters in
every step, and its report says which combinations the data actually fix.
Reach for it as soon as there are two or more unknowns and more data than
unknowns.

## Set-up

1. **One template per kind of measurement.**
   - Write each as an `.mx3` with a placeholder token for every free
     parameter and for each run's own setting (a field, a frequency, a size),
     e.g. `@MS@`, `@ALPHA@`, `@B@`. You choose the tokens; the spec names them.
   - Numbers are written with `repr()` (exact float round-trip).
   - Units are SI and fields are **in tesla**: 50 mT is `0.05`.
   - Bound every relaxer and every run time, because one bad parameter set
     must not hang the fit.
2. **One measure command per run.**
   - It prints the observable; its last printed number is used.
   - `{out}` is replaced by the run's output directory, e.g.
     `"python3 tools/ringdown.py freq {out}"`.
   - Several data can come from one simulation (a frequency and a decay
     rate from one ringdown). Give them the same template and settings and
     different measure commands. The simulation runs once and is measured
     twice.
3. **Data with σ.**
   - Without σ, χ² has no scale and the uncertainties mean nothing.
   - If σ is not given, estimate it (repeat runs, scatter, instrument
     resolution) and say how you estimated it.
4. **Bounds and a start.**
   - Bounds should be the physically plausible range.
   - Positive parameters that may be off by large factors use `"scale": "log"`
     (the default when min > 0).
   - Take the start from closed forms (`mx3 physics`, the **mx3-physics**
     library). Levenberg–Marquardt converges from roughly a factor 1.5 away,
     but a start in the wrong regime (wrong branch, wrong phase) can lead to a
     local minimum.
5. **skip_for (optional).** For runs that cannot depend on a parameter, the
   Jacobian reuses the base value instead of running them.
   - Example: an energy minimisation (`Relax`, `Minimize`) does not depend on
     the damping α.
   - List only what physics guarantees.
6. `fit.py init SPEC.json`, then vet one of the scripts it wrote, then step.

Minimal spec:

```json
{
  "workdir": "scratch/fit",
  "params": {
    "Ms":    {"init": 8.0e5, "min": 4e5, "max": 1.6e6, "placeholder": "@MS@"},
    "alpha": {"init": 0.02,  "min": 0.002, "max": 0.2, "placeholder": "@ALPHA@"}
  },
  "runs": [
    {"id": "f050", "template": "model/ringdown.mx3.in", "set": {"@B@": "0.05"},
     "measure": "python3 tools/freq.py {out}", "value": 6.63e9, "sigma": 2e7},
    {"id": "s000", "template": "model/static.mx3.in", "set": {"@B@": "0"},
     "measure": "python3 tools/mz.py {out}", "value": 0.87, "sigma": 0.01, "skip_for": ["alpha"]}
  ]
}
```

To log each run your own way as well, set `"record"` to any command, e.g.
`"python3 log_run.py {id} {value} {script}"`; it runs after each run, with
`{script} {out} {value} {label} {id} {param:NAME}` available. `"script_dir"` sets
where the generated scripts are written (default `<workdir>/runs`).

## Time

One evaluation is the sum of its runs. Plan for 1 + P (start and Jacobian),
then 5–15 steps, then P (final Jacobian), for P parameters. Say the estimate
before starting.

The fit stops by itself ("phase done") when no step can lower χ² by more than
0.1 or 0.1 % (`chi2_abs_tol`, `tolerance`). Smaller changes move the parameters
by less than a third of their uncertainty and are mostly simulation noise.

**The budget must be shorter than the shell's limit for one command.** Keep
`--budget` a few minutes below your shell's per-command time limit (the default
budget, 100 s, suits a 2-minute limit). If your shell tool lets you raise the
limit for a call, raise it and set the budget accordingly: fewer, longer calls
cost less overhead.

A run is started only when the time left covers it. A run cut off at the end
of the budget is repeated in the next call; nothing is lost. Do not start
other GPU jobs while a step runs.

If the shell gives up on a call before its budget is over, `fit.py` keeps
working in the background until the budget ends. A second call refuses to
start until then, and says when the first one will be done, so two calls
never write the same fit.

Between calls, read the printed lines. Each evaluation prints its χ² and
parameters, and `status` shows the last 15.

## Reading the report

| what you see | what it means | do |
|---|---|---|
| χ² ≈ dof (N − P) ± √(2·dof) | model and data agree to the noise | report; σ as printed |
| χ² ≫ dof, residuals of one kind all one sign | a systematic misfit: units, a protocol detail, wrong regime | check that kind before fitting further |
| χ² ≫ dof, residuals scattered | σ too small, or a local minimum | estimate σ again; restart from another start (`init --force`; finished runs are cached) |
| a parameter AT A BOUND | the bound is wrong, or that parameter is compensating for something | widen only for a physical reason |
| \|correlation\| > 0.9 | the data fix a combination better than each one | report the combination, and add a measurement sensitive to only one of them if you can |
| "Jacobian singular" | a parameter changes no datum | remove it or add data that respond to it |

- **σ**: the σ column is from (JᵀWJ)⁻¹ at the best set. When χ²/dof > 1, the
  next column scales it by √(χ²/dof).
- **Sensitivity**: "what each datum responds to" shows which parameters each
  measurement constrains. Use it to explain the result, not only to state it.

## Things that break fits

- **Fields in mT where tesla are expected.** `mx3 run` warns above 5 T.
- **A measure command that prints the wrong last number.** Run it by hand on
  one output first.
- **A noisy simulated observable** (cell-size steps, a short averaging
  window). Finite differences then measure noise.
  - Check by running the same set with one parameter ±2 %: the change must be
    much larger than the run-to-run scatter.
  - If it is not, set `"jacobian_step": 0.05`.
- **Editing a template or a script after runs exist.** That mixes two models.
  Change the template, then `init --force`.
- **Starting far away in a different regime** (e.g. above versus below an
  instability). Look at the starting set's residuals per kind before letting
  it run.

## Related skills

- **mx3-physics**: closed forms and typical values for the start and for
  sanity checks
- **mx3-consult**: a second opinion on a misfit, a model or a plan
- **mx3-authoring**: the templates; vet one generated script
- **mx3-run**: inspect any single run's output
- **mx3-tune**: one parameter, one target
- **mx3-match**: hysteresis-loop comparison
