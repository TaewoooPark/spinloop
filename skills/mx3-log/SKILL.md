---
name: mx3-log
description: >-
  Keep a lab notebook for a folder of simulations - what was run, what was
  concluded, and what is still open - reconstructed from the output directories
  themselves. Use for "what did I run last time", "where were we", "record that
  conclusion", "what is still unresolved", "summarise this project", "make
  notes on these simulations".
---

# The notebook

Work on one sample runs over weeks. Without a record, every session starts by
re-deriving what was already settled — and the person least able to reload that
context is the one who did not write the scripts.

```bash
N=${CLAUDE_PLUGIN_ROOT}/skills/mx3-log/scripts/notebook.py
python3 $N --root . scan                        # find every run and record it
python3 $N --root . note "Hc converged at 4 nm"
python3 $N --root . note "does the frame width matter?" --open
python3 $N --root . open                        # what is still unresolved
python3 $N --root . resolve "frame width" --answer "no, <1% over 5-20 nm"
python3 $N --root . show
```

Everything lives in one `MX3-NOTEBOOK.md` beside the simulations. Plain
markdown — readable, editable and committable without this tool.

## What scan reconstructs

Each mumax3 output directory carries `log.txt`, which holds the script exactly
as executed and the build that ran it. So the run history comes from
**evidence, not memory**: mesh, material parameters, how many rows and
snapshots, when it ran, and a `DIVERGED (NaN)` flag where the table went bad.

`scan` is idempotent — re-running it adds only what is new.

## When to write

- **After a conclusion, not after a run.** "Ran sweep_3.mx3" is already in the
  directory. "Coercivity is mesh-converged below 4 nm" is not.
- **Open questions as they appear.** The assumption you had to make and did not
  test is exactly what you will forget.
- **At the end of a session**, record where things stand, so the next one does
  not start cold.

## At the start of a session

Read the notebook before proposing anything:

```bash
python3 $N --root . show
python3 $N --root . open
```

If a user asks something the notebook already settled, say so and cite the
note rather than re-running it. If an open question is relevant to what they
just asked, raise it.

## Related skills

- **mx3-run** — produces the directories this reads
- **mx3-check** — its convergence verdicts are the notes worth keeping
- **mx3-paper** — a reproduction spec is a more formal version of the same idea
