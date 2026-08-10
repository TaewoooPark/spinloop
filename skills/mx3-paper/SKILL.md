---
name: mx3-paper
description: >-
  Turn a paper's methods section into a runnable mumax3 script, listing exactly
  which parameters the paper states and which had to be assumed. Also works in
  reverse: write the methods paragraph and provenance record for your own
  simulation so someone else can reproduce it. Use for "run it like this
  paper", "reproduce this paper's conditions", "set up the simulation from this
  paper", "write the methods section", "what parameters did they use".
---

# From a paper to a script, and back

Two directions, same discipline: **never let an assumed number look like a
reported one.**

---

## Direction 1 — reproducing a paper

Papers underspecify simulations. Almost every methods section omits something
the run needs, and the failure mode is silent: you assume a value, the
simulation runs, the answer disagrees, and you spend a week on physics when
the problem was a cell size nobody wrote down.

### Extract before writing anything

Work through this list and mark each item **stated** or **assumed**:

| | Usually stated | Usually missing |
|---|---|---|
| Ms, Aex | ✓ | |
| Ku1 / anisotropy axis | ✓ when relevant | easy axis direction |
| DMI (Dind/Dbulk) | ✓ when relevant | bulk vs interfacial |
| Sample dimensions | ✓ | |
| **Cell size** | sometimes | **often missing** |
| **Damping α** | sometimes | **often missing** |
| Solver / tolerance | rarely | almost always |
| Initial state | rarely | almost always |
| Temperature | if finite | assumed 0 |
| PBC | rarely | almost always |
| Field/current protocol | ✓ | ramp rate, settle criterion |

Cell size, damping and initial state are the three that most often decide
whether you reproduce a result. If the paper gives dimensions and a grid, the
cell size follows — do that arithmetic rather than guessing.

### Fill gaps by rule, and record the rule

| Missing | Reasonable default | Say |
|---|---|---|
| cell size | ≤ exchange length; `mx3 physics --Ms … --A …` | "assumed, paper did not state" |
| α (dynamics) | 0.01–0.02 | "assumed; results are α-sensitive" |
| α (static loop) | 1 | "relaxation only, α is numerical here" |
| initial state | `Uniform` along the easy axis | "assumed; a different start may give a different minimum" |
| solver | 5 (Dormand-Prince) | "assumed" |
| temperature | 0 | "assumed; paper reports no thermal effects" |

### Write it with the assumptions in the header

Hand off to **mx3-authoring**, and require every assumed value to appear on
the `Unverified` line:

```go
/*
  Reproduction of Fig. 3(a), Author et al., J. Appl. Phys. 123, 456 (2024)
  Units      : SI throughout
  Mesh       : 256x256x1 of 2x2x1 nm  (paper gives 512x512 nm; cell ASSUMED)
  Materials  : Ms 580e3 (stated), Aex 15e-12 (stated), Dind 3e-3 (stated),
               Ku1 0.8e6 (stated), alpha 0.3 (ASSUMED - not given)
  Outputs    : topological charge and m every 100 ps
  Unverified : cell size, damping, initial state and solver are all assumed;
               the paper states none of them. Disagreement with Fig. 3(a) is
               as likely to come from these as from the physics.
*/
```

### Then check before concluding anything

If the reproduction disagrees, the assumed parameters are the first suspects,
not the last. Run **mx3-check** for mesh convergence, and **mx3-tune** over the
assumed damping, before deciding the paper is wrong.

### Honest failure

Some papers cannot be reproduced from what they print. Saying "the methods
section does not determine the simulation; here is what I assumed and here is
how sensitive the answer is to each assumption" is a complete and useful
answer. Do not manufacture agreement by tuning assumed values until the figure
matches.

---

## Direction 2 — writing your own methods

Everything needed is already in the output directory. `log.txt` holds the
version banner and the script exactly as executed:

```bash
${CLAUDE_PLUGIN_ROOT}/lib/mx3 provenance sim.out --script
```

A methods paragraph that someone could actually follow:

> Micromagnetic simulations were performed with mumax³ 3.12 (commit 4506f313)
> using the Metal backend on Apple silicon. The sample was discretised into
> 128 × 32 × 1 cells of 3.91 × 3.91 × 3.0 nm; the in-plane cell size is below
> the exchange length of 5.7 nm. Material parameters were Ms = 800 kA/m,
> Aex = 13 pJ/m and α = 0.02. The Dormand-Prince solver was used with a
> maximum error per step of 1 × 10⁻⁵. Results were verified to be unchanged
> to within 2% under further mesh refinement.

Include, because they change the numbers:

- **exact build** — version *and* commit; forks differ
- **cell size, and that it is below the exchange length**
- **convergence statement** — from mx3-check, or say it was not tested
- **any approximation enabled** — `SpeculativeStep` and `DemagExtrapolation`
  alter the trajectory by design and must be declared
- **thermal runs**: this port uses Philox, not cuRAND's XORWOW, so a seed
  reproduces on Metal but does not reproduce a CUDA trajectory sample by
  sample. State that agreement is statistical.

### Reproduction bundle

Ship the `.mx3`, the `log.txt`, the build identifier, and mumax³'s own
`references.bib` (written into every output directory). That is enough for
someone else to re-run it exactly.

---

## Related skills

- **mx3-authoring** — writes the script, and enforces the assumption header
- **mx3-check** — supplies the convergence statement the methods needs
- **mx3-tune** — tests how much an assumed parameter actually matters
- **mx3-run** — `mx3 provenance` for the build record
