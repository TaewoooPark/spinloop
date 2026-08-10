---
name: mx3-check
description: >-
  Decide whether a simulation result can be trusted, by refining the mesh
  until the answer stops changing and by comparing against closed-form
  micromagnetics (exchange length, domain wall width, critical DMI, Kittel
  resonance, Walker field). Answers the reviewer question "did you check
  convergence". Use for "can I trust this result", "is this good enough to
  publish", "is the mesh fine enough", "check convergence", "does this agree
  with theory", "sanity check this result", "validate this". Needs a runnable
  script — use mx3-authoring first.
---

# Is this result trustworthy?

Two independent questions, and a result needs both.

1. **Does the answer stop changing when the mesh is refined?** If it does not,
   you are reporting a discretisation artefact.
2. **Does it agree with what theory predicts?** If it disagrees by a factor,
   one of the two is wrong and it is worth knowing which before publishing.

Neither is expensive here. A convergence study is five runs of the same
problem — on a queue that is five waits and nobody bothers; on this machine it
is a couple of minutes.

## 1. Mesh convergence

The template must declare grid and cell together, so refining holds the
physical size fixed:

```go
N  := 32
dx := 8e-9

SetGridSize(N, N/2, 1)
SetCellSize(dx, dx, 5e-9)
```

Do **not** name the cell `cell` — identifiers are case-insensitive and it
collides with the built-in `Cell()`. Use `dx`.

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/mx3-check/scripts/converge.py TEMPLATE.mx3 \
  --metric "loop:coercivity" --cells 16 32 64 128 \
  --Ms 800e3 --A 13e-12 --tolerance 0.02
```

The metrics are the same ones `mx3-tune` searches on — one definition, shared.

It reports the coarsest cell whose answer is within tolerance of the finest,
and refuses to certify anything if the two finest still disagree:

```
NOT CONVERGED.
  the two finest settings still differ by 9.0% - the series has not
  converged anywhere; refine further before trusting any of it
```

That refusal is the point. A three-point series that happens to bracket a
tolerance is not convergence; it can be two coarse runs agreeing by accident.

Exit `0` converged, `1` not.

## 2. Comparison with closed form

```bash
${CLAUDE_PLUGIN_ROOT}/lib/mx3 physics --Ms 800e3 --A 13e-12 \
    --Ku1 1.2e6 --alpha 0.02 --cell 4e-9 --D 1.5e-3
```

| Quantity | Formula | Use it to check |
|---|---|---|
| exchange length | √(2A/µ₀Ms²) | is the cell small enough at all |
| wall width | π√(A/K_eff) | simulated wall profile |
| K_eff | Ku1 − µ₀Ms²/2 | whether the film should be perpendicular |
| critical DMI | 4√(A·K_eff)/π | whether a uniform state should survive |
| Kittel FMR | (γ/2π)√(B(B+µ₀Ms)) | resonance from an FFT of m(t) |
| Walker field | ~αK/Ms | where wall velocity should peak |

**Read the assumptions before quoting a disagreement.** Most of these assume
an *extended* film. A 64 nm patch has demagnetising factors well away from
(0,0,1), and will legitimately differ by several percent. A measured 6%
deviation in that situation is agreement, not a discrepancy.

The Walker field in particular is an order-of-magnitude check: conventions
differ by factors of two, so treat "within about 2×" as consistent and never
quote it to three digits.

## 3. Reference problems

The strongest single check is a problem with a published answer. Standard
problem 4 is in
`${CLAUDE_PLUGIN_ROOT}/skills/mx3-authoring/assets/templates/dynamics.mx3`,
with the upstream reference values asserted inside it:

```go
ExpectV("m relaxed", m.Average(), vector(0.9669684, 0.1252732, 0), 1e-5)
```

If that passes on this machine, the installation is sound and a disagreement
elsewhere is in the new script, not the engine.

## What to report

Separate what was tested from what was not:

```
Converged: coercivity changes by less than 2% for cells at or below 4 nm.
  Your 8 nm run reads 2.66 mT; at 4 nm it is 2.44 mT — 9% high.
  4 runs, 2 min.

Consistent with theory: the exchange length is 5.7 nm, so 4 nm resolves a
domain wall with room to spare.

Not tested: time-step convergence (MaxErr), and whether 1 ns is long enough
to reach steady state. Those are separate questions.
```

Never report "verified". Report which specific thing was checked and what
remains open. A converged mesh says nothing about whether the model is right.

## Other convergence axes

Mesh is the usual culprit but not the only one:

- **Time step** — lower `MaxErr` (default 1e-5) by 10× and see if the
  trajectory moves.
- **Run length** — `mx3 settled sim.out --y mz`; a trace still drifting at the
  last step has not reached the state being reported.
- **Initial state** — `Relax()` finds *a* minimum. Start from `Uniform`,
  `Vortex` and `RandomMag` and compare `E_total`; if they disagree the
  reported state is not the ground state.
- **Approximations** — if `SpeculativeStep` or `DemagExtrapolation` were on,
  A/B against a default run. Both change the trajectory by design.

## Related skills

- **mx3-run** — inspect a single result
- **mx3-tune** — the search whose answer this validates
- **mx3-authoring** — `pitfalls.md` catalogues the errors that survive `-vet`
