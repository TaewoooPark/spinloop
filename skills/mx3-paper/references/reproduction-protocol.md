# The reproduction protocol

A reproduction can always be made to agree. Turn the exchange constant down,
nudge the anisotropy, and any figure can be hit. The result is worthless: you
have fitted a curve, not reproduced a physical claim.

The whole protocol exists to prevent that one failure, and it comes down to a
single division.

## Two kinds of number, and one rule

| | | May you change it? |
|---|---|---|
| **stated** | the paper prints a value | **Never.** |
| **assumed** | the paper is silent | Yes — you invented it. |
| **numerics** | not physics: cell size, boundary conditions, solver, whether demag is on | Yes, but only when the paper's *model* justifies it. |

**If agreement requires changing a stated value, that is the finding.** Report
the value that would be required and by how much it differs. Do not change it
and call the result a reproduction.

Every assumed value stays on the record, in the script header and in the spec,
because agreement reached under assumptions is conditional on those
assumptions. A different set might agree equally well.

## The spec

One JSON file carries the whole reproduction. `scripts/extract_paper.py`
drafts it; you complete it by reading the paper.

```json
{
  "paper": {"id": "arXiv:1803.11174", "figure": "Fig. 1a"},

  "stated": {
    "Aex":  {"value": 13e-12, "as_printed": "13 pJ/m", "page": 3},
    "Msat": {"value": 0.86e6, "as_printed": "0.86 MA/m", "page": 3}
  },

  "assumed": {
    "alpha": {"value": 1.0, "why": "not stated; static problem, damping only
              sets how fast Relax() converges"}
  },

  "numerics": {
    "EnableDemag": "false - the paper states it excludes the demagnetising
                    field (p.7); its energy functional has no such term",
    "OpenBC": "true - the paper's Eq. 11 boundary condition is the free-spin
               condition"
  },

  "targets": [
    {"name": "edge tilt m_z", "kind": "analytic",
     "metric": "last:m_xrange0_z", "expected": 0.7532, "tolerance": 0.02,
     "source": "Eq. 12: sin(Theta)=Delta/xi, Delta=sqrt(A/Ku), xi=2A/D"}
  ]
}
```

Every `stated` entry carries the page it came from. That is what makes the
reproduction auditable: a reader can check any number in one step.

## Targets, best kind first

A reproduction without a target is not a reproduction; it is a run that
happened. Pick the strongest target the paper supports.

| kind | What it is | Why this order |
|---|---|---|
| `analytic` | a closed form the paper derives | exact, no reading error, and it tests the physics rather than the plotting |
| `stated` | a number in the text or a table | exact, but only as good as the paper's own rounding |
| `digitised` | points you read off a figure | carries your error; state the uncertainty and set the tolerance accordingly |
| `qualitative` | "a skyrmion forms and is stable" | cannot fail automatically; say so rather than inventing a number |

Prefer an analytic target even when the figure is what you were asked to
reproduce. If the paper derives the curve it plots, matching the derivation
*is* matching the figure — and it is checkable to three digits instead of by
eye.

Metrics are the same ones `mx3-tune` and `mx3-check` use (`last:`, `abs:`,
`max:`, `min:`, `loop:`, `velocity:`). To target one cell rather than the whole
sample, crop it into the table:

```go
TableAdd(Crop(m, 0, 1, 0, 1, 0, 1))   // -> columns m_xrange0_x/y/z
```

Note this reports the cell **centre**, half a cell in from the physical
boundary. For an edge quantity with a short decay length that is a real offset
— worth about 0.1° in the worked example, more on a coarse mesh.

## Order of investigation when a target misses

Work down this list. It is ordered by how often each cause is the real one,
and the first two have nothing to do with the paper's physics.

**1. Numerics.** These look exactly like a physics disagreement and are not.

- Is the mesh converged? Run `mx3-check`. An unconverged mesh can be off by
  tens of percent and perfectly reproducible.
- Boundary conditions. See `simulator-conventions.md` — in the worked example
  this alone was a 13° error.
- Is demagnetisation on when the paper's model excludes it, or off when it
  includes it?
- Did the run actually settle? `mx3 settled`.

**2. Assumed parameters.** You invented them, so vary them — one at a time,
with `mx3-tune`. Two free parameters against one target is under-determined and
will converge on something meaningless.

**3. The model.** Is the paper simulating something you have not built —
a multilayer as an effective medium, a temperature-dependent Ms, a current
you left out?

**4. Only now, the stated values.** And not to change them: to report what
would be required. "The figure is reproduced only with Ms = 0.7 MA/m, 19% below
the stated 0.86" is a legitimate and useful result.

## Honest outcomes

Three endings are all acceptable. Manufacturing agreement is not.

- **Reproduced.** Targets met, with the assumptions listed.
- **Reproduced conditionally.** Targets met only under an assumption the paper
  does not state. Say which, and how sensitive the result is to it.
- **Not reproducible from what is printed.** The methods section does not
  determine the simulation. Report what you assumed, what you tried, and how
  much each assumption moved the answer. This is a complete answer and a
  common one.

## Worked example

`assets/worked-example/` holds a full reproduction of the 1D edge-tilting
problem from arXiv:1803.11174: the spec, the script, and the run that passes
both targets.

It is worth reading for what went wrong on the way. The first attempt used
every stated parameter correctly and still gave a 28° edge tilt against the
analytic 41°. Refining the mesh 8× did not fix it — the answer converged to
28.8°, which ruled out discretisation. Increasing DMI to twice the stated value
did not reach the target either, which ruled out a simple unit convention.

The cause was `OpenBC`, a mumax3 setting the paper never mentions because the
paper is not about mumax3. With the free boundary the paper's own equation
assumes, the same script gives 40.5° and converges to the analytic value.

Not one stated parameter was touched.
