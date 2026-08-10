# What mumax3-ultrafast adds

This fork executes the unmodified mumax³ physical model through Metal. The
equations and solvers were not reimplemented, so a script written for upstream
mumax³ runs unchanged. What it *adds* is a set of performance knobs that do not
exist upstream — and that no model's prior knowledge covers, because they landed
on **2026-08-01**.

**Check availability before emitting any of these.** `scripts/preflight.sh`
probes the actual binary; a build older than those commits rejects them at the
vet gate:

```
t7_fork.mx3 : script line 3: SpeculativeStep = true: undefined: SpeculativeStep
```

## SpeculativeStep — 1.53×

```go
SpeculativeStep = true
```

Overlaps host encoding with GPU execution. At research mesh sizes the Apple GPU
often waits on the host rather than on arithmetic: at 128×128 the host takes
longer to encode a Dormand-Prince step than the GPU takes to run it.

**It is an approximation.** `MaxErr` is still enforced, but the rejection lands
one step late, so the sequence of time steps differs from the exact controller
and the trajectory diverges at roughly the **1% level after a few thousand
steps**.

**It closes itself** — becomes a silent no-op — under any of:

- `FixDt` set
- finite `Temp`
- `Relax()`
- `DemagExtrapolation`
- post-step hooks

Setting it alongside those is not a speed-up; it is dead code. `lint_mx3.py`
flags this as `R-FORK-SPEC`.

## MinimizeOnGPU — 1.58×

```go
MinimizeOnGPU = true
```

Keeps `Minimize()`'s Barzilai-Borwein step size in device memory so an
iteration does not round-trip to the host.

**Every descent step stays bit-identical.** Only the convergence check is one
iteration late, so a minimisation may stop one iteration further along than the
default build. This is the safest of the three knobs.

## DemagExtrapolation — off by default

```go
SetSolver(5)
DemagExtrapolation = true
```

High-order polynomial extrapolation of the demagnetising field, which
accelerates demag-heavy solver 4/5/6 workloads by replacing exact convolutions
with extrapolated ones.

**It is an approximation, and its error depends on trajectory and time step.**
A successful benchmark on one problem is not an accuracy guarantee for another.
A/B it against a default run before trusting results.

Unsupported solvers and unsafe model states **fail closed** to exact
convolution — so pairing it with solver 1/2/3 silently does nothing
(`R-FORK-DEMAG`).

Instrumentation, for verifying it actually engaged:

```go
IsDemagExtrapolationActive()     // bool
GetDemagExtrapolatedEvals()      // convolutions replaced
GetDemagExactEvals()             // convolutions still done exactly
GetDemagRejectedAttempts()       // solver attempts rejected
GetDemagExtrapolationStatus()    // string: active, or why not
ResetDemagExtrapolation()        // discard history and counters
```

## Batch queueing — 2.53×, and it is not in the script

The largest easy win for parameter sweeps is a CLI flag, so it is invisible if
you only look at the script:

```bash
mumax3 -j 3 sweep_*.mx3     # N queued inputs per GPU
```

Measured 2.53× aggregate for three `Minimize()` jobs. Because mx3 has no
user-defined functions, generating one file per parameter and batching them is
the idiomatic sweep anyway. See `recipes.md`.

## Wall-clock guards

```go
RelaxWallClockTime    = 300    // seconds; interrupts Relax()
MinimizeWallClockTime = 300    // seconds; interrupts Minimize()
```

Introduced 2026-03-27. Useful whenever a relaxation might not converge — an
unattended sweep otherwise hangs on one bad parameter set.

## Sizing — throughput is not flat in problem size

- Peak throughput per cell is at **256²** on the measured M4.
- At and below **128²**, a fixed per-evaluation overhead of **172–187 µs**
  dominates and a wider GPU cannot help at all.
- Capacity ceiling is **83.9 M cells**; 104.9 M fails. (Ties OOMMF on capacity;
  4.5× faster at that size.)

Consequence for script design: below 128² do not try to go faster by enlarging
the mesh or tuning the solver — batch the sweep with `-j` instead.
`lint_mx3.py` reports this as `R-SIZE` (INFO).

## Metal FFT backend

Chosen automatically. VkFFT handles eligible 2D demag transforms whose padded
dimensions are powers of two no larger than 512×512 and whose active data is a
strict prefix; MPSGraph handles everything else.

Environment overrides, not script settings:

```bash
MUMAX3_METAL_FFT_BACKEND=mps      # keep all plans on MPSGraph
MUMAX3_METAL_FFT_BACKEND=vkfft    # extend VkFFT to the padded 1024x1024 tier
```

## Thermal simulations do not reproduce CUDA trajectories

Thermal noise uses **Philox**, not cuRAND's XORWOW. A seed is reproducible on
Metal, but it will not reproduce CUDA's sample-by-sample trajectory. The
statistical behaviour is what was validated, not the sample sequence.

If you are reproducing a published CUDA thermal run, expect statistical
agreement only — and say so in the header.

## Physics fidelity of the port

Against unchanged upstream CUDA-era regression references:

| Measure | Result |
|---|---|
| Non-thermal upstream physics tests passed | 15 / 15 |
| Assertions within original upstream tolerances | 103 / 103 |
| Mean average-magnetisation vector agreement | 99.9923% |
| Zero-tolerance assertions matched exactly | 19 / 19 |
| Official mumax³ example simulations completed | 15 / 15 |

Tolerance conformance, not bit-for-bit identity: parallel GPU reductions can
differ in their last floating-point bits.

## Writing portable scripts

If the script must also run on upstream CUDA mumax³, none of the fork knobs may
appear in it. Keep them in a separate opt-in block, or out entirely:

```go
// Portable: runs on upstream mumax3 and on mumax3-ultrafast.
SetSolver(5)
MaxErr = 1e-5
```

State portability in the header when it matters — it is a reproducibility
property, not a performance one.
