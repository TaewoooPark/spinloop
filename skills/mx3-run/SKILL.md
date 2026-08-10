---
name: mx3-run
description: >-
  Run a mumax3 simulation and show the result — plots, key numbers, snapshot
  images — instead of leaving the user with an output directory to decode.
  Also reads results that already exist, including ones produced elsewhere.
  Diagnoses runs that failed, diverged (NaN), or saved nothing. Use for
  "run this simulation", "run it and show me", "show me the results", "plot
  the hysteresis loop", "what happened in this run", "why did this fail",
  "open this output folder", "did it diverge". For writing the script in the
  first place use mx3-authoring; for repeating runs until a target is met use
  mx3-tune.
---

# Running a simulation and showing what came out

A mumax3 run leaves `table.txt`, a pile of `.ovf` files and `log.txt`. The
researcher wants a curve and a number. This skill covers the distance.

Everything goes through `${CLAUDE_PLUGIN_ROOT}/lib/mx3`, which is shared with
the other skills in this plugin so that "coercivity" means the same thing
everywhere.

## Before running

Check the script first if this skill wrote it or the user just edited it:

```bash
${CLAUDE_PLUGIN_ROOT}/skills/mx3-authoring/scripts/vet.sh sim.mx3
```

A failed run costs minutes; a failed compile costs seconds. Never skip this to
"save time".

## Run

```bash
${CLAUDE_PLUGIN_ROOT}/lib/mx3 run sim.mx3 --timeout 1800
```

If it reports no engine, install one — a verified 4 MB download, no
compiler needed — then retry:

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/install_engine.sh
```

The version banner is left on deliberately, so `log.txt` records which build
produced the result. Results land in `sim.out/`.

Exit codes: `0` ran, `1` the script failed, `2` this machine cannot run it.
A `2` means stop editing the script — the problem is not in the script.

Before a long run, say how long it will be. If the mesh is below 128×128, say
so: a fixed ~180 µs per evaluation dominates there, so a bigger mesh or a
faster GPU will not help, and several parameter sets at once will.

## Show

```bash
mx3 summary  sim.out                    # what is in here, and did it diverge
mx3 table    sim.out --csv out.csv      # the time series
mx3 plot     sim.out --y mz --out m.png # quick curve (needs matplotlib)
mx3 image    sim.out                    # last snapshot as PNG
mx3 image    sim.out --all --arrows 16  # every snapshot, with arrows
```

Pick the view from the question, not from what is available:

| The user asked | Show |
|---|---|
| "show me the hysteresis loop" | `mx3 loop` + a plot of m vs B |
| "how fast is the domain wall" | `mx3 velocity --pos ext_dwpos` |
| "did the skyrmion survive" | last `ext_topologicalcharge`, plus the final snapshot |
| "has it finished settling" | `mx3 settled --y mz` |
| "what does it look like" | `mx3 image` |

Derived numbers:

```bash
mx3 loop     sim.out --field B_extx --moment mx   # coercivity, remanence, squareness
mx3 velocity sim.out --pos ext_dwpos              # steady-state speed + fit quality
mx3 settled  sim.out --y mz                       # did it stop changing
```

Report the fit quality when you report a velocity. A low r² means the motion
was not steady — past Walker breakdown the wall oscillates, and a single
velocity quoted from that is meaningless.

## When it fails

`mx3 summary` flags NaN columns and the row where they start. That row is the
answer to "when did it go wrong", which is more useful than "it went wrong".

| Symptom | Usual cause |
|---|---|
| NaN partway through | time step too large, or `alpha = 0` with a strong field; lower `MaxErr` or set `FixDt` |
| `table.txt` missing | the script never called `TableSave`/`TableAutoSave` |
| no `.ovf` | no `Save(m)`/`AutoSave(m, …)` |
| runs forever | `Relax()` cannot converge — check `alpha > 0`; set `RelaxWallClockTime` |
| dies at startup | usually a mesh or region error — see mx3-authoring's `pitfalls.md` |

For a script that compiles but dies when the engine builds the world (bad
region index, missing OVF, empty geometry):

```bash
${CLAUDE_PLUGIN_ROOT}/skills/mx3-authoring/scripts/smoke_run.sh sim.mx3
```

## Reading results produced elsewhere

`mx3 summary`, `table`, `loop`, `image` all work on any mumax3 output
directory, including one from a cluster or a colleague. Point it at a parent
directory and it finds every run underneath:

```bash
mx3 summary ~/simulations/           # every output dir under here
mx3 provenance sim.out --script      # which build, and the script as executed
```

`log.txt` holds the script verbatim, so a directory can always say what made
it. If `provenance` reports INCOMPLETE, the run was started with `-v=false`
and that record is gone — worth saying, because it cannot be recovered.

## Reporting

Lead with the answer, not the file listing:

```
Coercivity is 55 mT; the loop is square (squareness 0.999).
  ran 58 s, 26 field steps, mumax 3.12 (Metal)
  plot: sim.out/loop.png

Worth checking: the 4 nm cell is below the 5.7 nm exchange length, so the
mesh resolves a wall — but I have not verified the answer is converged.
Run mx3-check if this number is going into a paper.
```

Say what was measured, what it cost, and what has *not* been established.
A run completing is not evidence that the result is right.

## Related skills

- **mx3-authoring** — write or fix the script
- **mx3-tune** — vary a parameter until a target is met
- **mx3-check** — is the mesh fine enough to trust this
- **mx3-match** — compare against measured data
- **mx3-view** — a picture of the magnetisation behind the numbers
- **mx3-log** — record what this run settled
