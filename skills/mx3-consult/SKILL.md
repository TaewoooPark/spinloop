---
name: mx3-consult
description: >-
  Ask a separate expert session — a model that holds the whole mx3-physics
  library in its context and keeps the conversation — a physics or method
  question, and get a reasoned second opinion: is this formula right for my
  geometry, why does the fit miss these points, what start values make
  sense, which measurement would separate two parameters, is this plan
  sound. Use when stuck, before committing to an expensive plan, when
  a result looks wrong, or to check a closed-form estimate. Every exchange
  is logged in the repository.
---

# Consulting the expert session

Your own context fills with tool output; the consultant's does not. It holds the
**mx3-physics** library (closed forms, scales, typical values, numerics, fitting
method) and the conversation with you, nothing else, and it is told to check units,
regimes and arithmetic. Use it as a colleague down the hall: a short, specific
question with the numbers, and the evidence attached.

```bash
C="python3 ${CLAUDE_PLUGIN_ROOT}/skills/mx3-consult/scripts/consult.py"
$C ask "QUESTION" [--attach FILE]...     # answer printed; the session remembers earlier questions
$C ask "QUESTION" --new                  # start the conversation over
$C ask "QUESTION" --session fit          # a separate conversation
$C history                               # what was asked so far
$C check                                 # is the consultant reachable
```

An answer takes 20 s to a few minutes (the consultant reasons before it answers). The connection comes from the environment
(`MX3_CONSULT_*`, otherwise the same model endpoint this session uses).

## When it pays

| moment | ask |
|---|---|
| before the first expensive batch | "Here is my plan and my start values (attached). Which assumption is weakest? What would you check first?" |
| choosing start values | "M_eff from FMR and H_K from a hard-axis loop (attached). Which closed forms give Ms and Ku, and how biased are they for a finite element?" |
| a misfit that does not go away | "Residuals by kind attached. χ² = … at …. Which parameter or model detail would produce this pattern?" |
| a number that looks wrong | "I get 300 GHz for … with …. Plausible? Check my units." |
| an under-determined fit | "Correlation Ms–Ku = 0.98 from Kittel data. Which observable would break it?" |
| before reporting | "Here are my values, σ and correlations. Is anything inconsistent with the physics?" |

## How to ask well

- **One question per call**, with the numbers in the question: the parameter values,
  units, geometry, what was run and what came out.
- **Attach evidence, not dumps**: a residual table, an excerpt of your notes, one script, a
  short CSV. Each attachment is cut at 20,000 characters. Never attach simulation
  output directories or OVF files.
- **Ask for checks you can run**: "what run would tell these two explanations apart?"
- **Follow-ups go to the same session**, so it remembers: "You suggested X; I ran it
  and got Y. Now?"

## What to do with the answer

- The consultant cannot run anything. Its statements about *your* system are
  hypotheses: test them with a simulation before acting on them, and record in your
  notes which advice you followed and what the test showed.
- Typical material values from it are for orientation and starting points, never a
  substitute for your own measurements or fits.
- If the answer conflicts with your simulation, the simulation of the actual protocol
  wins. Say so in the notes, and ask a follow-up if the conflict matters.
- If it says it is unsure, believe it.

## Cost

Each call sends the library (about 55–65 k tokens) and the session so far. Ask when
an answer can save a batch of simulations or a wrong turn, not for things a quick
look in the library answers: **mx3-physics** points to the right chapter for that.

## Related skills

- **mx3-physics** — the same library, to read directly
- **mx3-fit** — the fitting loop whose residuals you will often attach
