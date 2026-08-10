---
name: mx3-authoring
description: >-
  Write, fix, or review mumax3 micromagnetic simulation inputs (.mx3) for
  mumax3-ultrafast, the Apple Silicon Metal port. Every script is gated through
  `mumax3 -vet` before it is shown, then linted for the traps vet cannot see:
  SI unit slips, float-to-int grid truncation, and cells coarser than the
  exchange length. Knows the fork-only tuning API (SpeculativeStep,
  MinimizeOnGPU, DemagExtrapolation) and when each is a silent no-op. Use for
  "write me an mx3 script", "mumax3 simulation", "hysteresis loop script",
  "skyrmion simulation", "domain wall simulation", "parameter sweep", "why
  won't this mx3 run", "mx3 error", "micromagnetic simulation script",
  "standard problem 4". Not for
  plotting or analysing results that already exist.
---

# Authoring .mx3 for mumax3-ultrafast

mx3 looks like Go and is not Go. The parser accepts **seven statement types**
and no function declarations. The API is 527 entries that either exist or do
not. Both facts are checkable, so check them — do not write from memory.

## Hard rules

1. **Never show an unvetted script.** `scripts/vet.sh` must pass first. Failed
   attempts are yours to fix, not the user's to read.
2. **Never use an identifier that is not in `references/api-index.md`.** If it
   is not there, it does not exist. Do not guess a plausible name.
3. **Every script opens with the assumption header** (see below). No exceptions.
4. **Report machine-checked and human-judgement separately.** Never merge them
   into one "verified".
5. **Fork-only knobs need a reason and a caveat**, and must survive the
   capability probe in `scripts/preflight.sh` — older binaries reject them.

## Workflow

```
1. preflight.sh          once per session. Tells you what can be verified.
                         Missing binary -> say so; do not claim verification.
2. Read references       api-index.md for names, recipes.md for shape.
3. Write                 header block + body. Assert with Expect() when a
                         reference value is known.
4. vet.sh FILE           exit 1 -> fix, retry (cap 3). exit 2 -> environment
                         problem: stop editing and tell the user.
5. lint_mx3.py FILE      ERROR must be fixed. WARN must be fixed or explained
                         in the header. Never silence one silently.
6. smoke_run.sh FILE     only if the script uses regions, shapes, LoadFile or
                         custom terms. Catches world-construction failures.
7. Report split          see "Reporting" below.
```

## The language, in short

Consult `references/grammar.md` before writing anything unusual. The parts that
bite every time:

- Statements allowed: assignment, expression, `if`, C-style `for`, `++/--`,
  block, empty. **No `func`, no `range`, no `break`, no `continue`, no
  `switch`, no slices, no maps, no `import`.**
- Identifiers are **case-insensitive**: `setgridsize` == `SetGridSize`.
- `for` is `for i := 0; i < n; i++ { }` only.
- Selectors work for method calls (`Msat.SetRegion(...)`), not field reads.
- Reuse across parameter sets is done with **separate files**, not functions —
  then `mumax3 -j 3 *.mx3`.

## Units — every value is bare SI

| Quantity | Unit | Typical |
|---|---|---|
| `SetCellSize` | m | `4e-9` |
| `SetGridSize` | **cell count, integer** | `128` |
| `Msat` | A/m | `800e3` (permalloy) |
| `Aex` | J/m | `13e-12` |
| `Ku1` | J/m³ | `0.5e6` |
| `B_ext` | T | `vector(0, 0, 1e-3)` |
| `Run` | s | `1e-9` |

`SetGridSize(128e-9, 32, 1)` **passes vet** and truncates to zero cells. Cell
counts are counts. See `references/units-and-scales.md`.

## Required header

```go
/*
  <one line: what this simulates>
  Units      : SI throughout (m, A/m, J/m, T, s)
  Mesh       : 128x32x1 cells of 3.9x3.9x3.0 nm  (l_ex = 5.7 nm, resolved)
  Materials  : permalloy - Msat 800e3 A/m, Aex 13e-12 J/m, alpha 0.02
  Outputs    : table.txt every 10 ps, m every 100 ps
  Unverified : material constants, total run time, whether 1 ns reaches
               steady state - reader must confirm.
*/
```

`Unverified` is the point of the header. It is what keeps step 7 honest.

## Reporting

```
Verified mechanically
  - mumax3 -vet: PASS
  - identifiers: all present in api-index.md
  - lint: clean (or: N warnings, each explained in the header)

You must check
  - <material constants for the real system>
  - <whether the run time reaches the regime of interest>
  - <any approximation knob that was enabled>
```

If the binary was unavailable, say **"not verified — mumax3 not on PATH"**.
Never present unverified code as checked.

## Reference map

| Need | Read |
|---|---|
| Does this name exist? What are its arguments? | `references/api-index.md` |
| What syntax is legal? | `references/grammar.md` |
| Fork-only API, performance knobs, caveats | `references/ultrafast-deltas.md` |
| Units, exchange length, material constants | `references/units-and-scales.md` |
| Compiles but is wrong — why? | `references/pitfalls.md` |
| Canonical script shapes | `references/recipes.md` |
| Starting skeletons | `assets/templates/` |

## Scripts

| Script | Purpose | Exit |
|---|---|---|
| `scripts/preflight.sh` | what this machine can verify | 0 ready / 1 degraded |
| `scripts/vet.sh` | compile gate | 0 pass / 1 code / 2 env |
| `scripts/lint_mx3.py` | semantic checks vet cannot do | 0 ok / 1 error |
| `scripts/smoke_run.sh` | shrunken run, world-construction check | 0 / 1 / 2 |
| `scripts/gen_api_reference.go` | regenerate the index after upgrading mumax3 | |

Lint categories: `physics`, `structure`, `fork`, `convention`, `perf`.
Use `--only physics,structure` when reviewing someone else's script, where the
house header convention does not apply.

## What this skill does not do

Physics is not verified. A vet-clean, lint-clean script can still model the
wrong system with the wrong constants. The tooling removes mechanical failure
so the remaining review is purely physical — it does not perform that review.

## Related skills

This skill writes the script. Hand off from here:

| Next | Skill |
|---|---|
| "run it and show me the results" | **mx3-run** |
| "keep adjusting until it works" | **mx3-tune** — needs a declared parameter and `TableSave()` |
| "can I trust this result" | **mx3-check** — needs `N`/`dx` declared separately |
| "match my measurement" | **mx3-match** |
| "run it like this paper" | **mx3-paper** |
| "show me what it looks like" | **mx3-view** |
| "what should I even simulate?" | **mx3-plan** — run this *before* writing |
| "simulate our VSM/MOKE measurement" | **mx3-lab** |

Two conventions make the handoff work, so apply them by default when the
script is likely to be swept or refined:

```go
Ku_value := 0.5e6     // one declared line per parameter -> mx3-tune
N        := 64        // grid and cell declared separately -> mx3-check
dx       := 4e-9      // never name it `cell`: collides with Cell()
SetGridSize(N, N, 1)
SetCellSize(dx, dx, 2e-9)
...
TableSave()           // a goal that cannot be measured cannot terminate a loop
```
