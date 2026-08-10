---
name: mx3-tune
description: >-
  Vary a simulation parameter automatically, running again and again until a
  target is reached — or reporting honestly that it cannot be. Also finds the
  threshold where a behaviour starts: the field at which a sample switches,
  the anisotropy at which a film turns perpendicular, the current at which a
  wall depins. Use for "make it do X", "keep running until it works", "find
  the value that gives", "find where it starts happening", "make the coercivity
  20 mT", "what conditions make a skyrmion stable", "at what field does it
  switch", "find the transition point", "threshold". Needs a runnable script — use
  mx3-authoring to write one first.
---

# Searching a parameter until the simulation hits a target

This is the thing a laptop makes possible and a queue does not. One run takes
seconds, so twenty runs is a conversation rather than a week.

## The two questions

They are different and the user usually means one specifically.

| They say | They want | Flag |
|---|---|---|
| "make the film perpendicular" | *a* value that works | (default) |
| "find where it turns perpendicular" | *where it starts* | `--threshold` |

Ask only if it is genuinely ambiguous. "Make it happen" stops at the first
success; "find the threshold" narrows onto the boundary and costs a few more
runs.

## What the template needs

One line declaring the parameter, and nothing else special:

```go
Ku_value := 0.5e6      // the line tune.py rewrites

SetGridSize(64, 64, 1)
SetCellSize(4e-9, 4e-9, 1e-9)
Msat = 1050e3
Ku1  = Ku_value        // used here
...
TableSave()            // REQUIRED: the goal is measured from table.txt
```

Two hard requirements:

1. **The script must write a table.** A goal that cannot be measured is a loop
   that cannot terminate.
2. **Bound the relaxers**, or one bad parameter set stalls the whole search:
   ```go
   RelaxWallClockTime = 60
   ```

Name the parameter carefully. mx3 identifiers are **case-insensitive**, so
`cell`, `step` and `t` collide with built-ins and will not compile. `dx`, `N`,
`Ku_value` are safe. Check `mx3-authoring/references/api-index.md` if unsure.

## Run it

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/mx3-tune/scripts/tune.py TEMPLATE.mx3 \
  --param Ku_value --range 0.3e6 1.5e6 \
  --goal "abs:mz >= 0.95" \
  --points 5 --budget 20 --time 1800 \
  --threshold            # only when they asked WHERE, not WHETHER
```

If the engine is missing or predates the batching work, install it first
(`${CLAUDE_PLUGIN_ROOT}/scripts/install_engine.sh`): without `-j` the
coarse scan still runs, just one point at a time.

Strategy is scan-then-narrow: a coarse scan across the range, then bisection
into the interval that brackets the target. Chosen because the report is
readable — "I tried these five, it happens between these two, I looked there"
is something a researcher can check without knowing what an optimiser is.

## Goals it can measure

The goal is `metric comparator value`. Every metric maps to something the
engine or the table already provides.

| Metric | Means | Template must record |
|---|---|---|
| `last:mz` | final value of a column | that column |
| `abs:mz` | final absolute value | |
| `max:mz`, `min:mz` | extreme over the run | |
| `loop:coercivity` | switching field, in T | `TableAdd(B_ext)` + a swept loop |
| `loop:remanence`, `loop:squareness` | | |
| `velocity:ext_dwpos` | steady wall speed, m/s | `TableAdd(ext_dwpos)` + `ext_centerWall` |
| `settled:mz` | 0 if it stopped changing | |

Examples:

```
--goal "abs:mz >= 0.95"                 # is it perpendicular
--goal "loop:coercivity >= 0.02"        # coercive field at least 20 mT
--goal "abs:ext_topologicalcharge >= 0.9"   # a skyrmion is present
--goal "velocity:ext_dwpos >= 100"      # wall moves at 100 m/s
```

If the user's target is not in this list, the honest move is to say what can
be measured rather than inventing a proxy. Adding one means adding it to
`measure()` in `tune.py`, which `mx3-check` shares.

## Budgets are mandatory

Always set both, and tell the user before starting:

```
--budget 20      # at most 20 runs
--time 1800      # at most 30 minutes
```

Estimate first. A run that takes 60 s with a budget of 20 is 20 minutes — say
that out loud before walking away from it.

## The four outcomes

It always stops for exactly one reason, and reports which:

| | Means | What to say |
|---|---|---|
| `reached` | the goal is met | give the value, and the bracket if `--threshold` |
| `bracketed` | crossed between two values, tolerance not met | give the interval — that *is* the answer |
| `exhausted` | budget ran out | give the interval reached so far, and what another N runs would cost |
| `impossible` | never approaches the target anywhere in range | **this is a result** |

`impossible` is not a failure. "No value of Ku in 0.3–1.5 MJ/m³ makes this
film perpendicular" is a physics answer. Report the closest value reached and
suggest widening the range or reconsidering the model — do not quietly widen
it and try again.

## Reporting

```
The film turns perpendicular between Ku1 = 6.38e5 and 6.56e5 J/m3.
  9 runs, 48 s

Compare: mu0*Ms^2/2 = 6.93e5 J/m3 is where an INFINITE film would switch.
This one is 64 nm across, so its edges lower the demagnetising factor and it
switches ~6% early. The simulation and the formula agree as well as they should.

Not established: whether 4 nm cells resolve this transition. Run mx3-check
before quoting the number.
```

Always compare against a closed form when one exists —
`${CLAUDE_PLUGIN_ROOT}/lib/mx3 physics --Ms … --A … --Ku1 …` gives them. A
search that lands where theory says it should is far more convincing than a
search that merely terminated.

## Related skills

- **mx3-authoring** — write the template, with a declared parameter
- **mx3-run** — inspect any single trial's output
- **mx3-check** — confirm the answer survives mesh refinement
- **mx3-match** — same loop, but the target is measured data
