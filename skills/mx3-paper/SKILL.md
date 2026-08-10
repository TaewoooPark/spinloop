---
name: mx3-paper
description: >-
  Reproduce a paper's micromagnetic simulation from its PDF. Extracts material
  parameters with the page each came from, marks what the paper never stated,
  builds a runnable script, runs it, and checks the result against targets taken
  from the paper - refusing to reach agreement by adjusting any value the paper
  actually printed. Also works in reverse: writes the methods paragraph and
  provenance record for your own simulation. Use for "run it like this paper",
  "reproduce this paper's conditions", "reproduce Figure 3", "set up the
  simulation from this PDF", "what parameters did they use", "why doesn't my
  result match the paper", "write the methods section".
---

# Reproducing a paper

The failure mode this skill exists to prevent: you assume a cell size nobody
wrote down, the simulation runs, the answer disagrees, and you spend a week on
physics when the problem was an assumption.

So every number carries a label - **stated** or **assumed** - from the first
step to the final report, and nothing the paper printed is ever adjusted to
improve agreement.

Read `references/reproduction-protocol.md` before starting. It is the rulebook.

## 1. Harvest

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/mx3-paper/scripts/extract_paper.py paper.pdf \
        --json spec.json
```

Finds every unit-bearing quantity, converts it to SI, and reports it with its
page and the sentence around it. It deliberately does **not** choose: a paper
routinely contains several parameter sets (its own sample, a cited comparison,
a second geometry), and picking between them needs the context.

It also reports what is missing. Cell size, damping and initial state are the
three omissions that most often decide whether a reproduction works.

Then **read the pages it points at** before trusting anything. Use `Read` on the
PDF for the methods section and the caption of the figure you are targeting.

## 2. Complete the spec

Fill in `spec.json` by hand from the paper (format in the protocol reference):

- `stated` - value, how it was printed, and the **page**. Auditable in one step.
- `assumed` - value and *why*. Defaults below.
- `numerics` - cell size, `OpenBC`, `EnableDemag`, solver, each with the
  sentence in the paper that justifies it.
- `targets` - what "reproduced" means, quantitatively.

### Defaults for what papers omit

| Missing | Use | Record as |
|---|---|---|
| cell size | <= exchange length (`mx3 physics`) | assumed |
| alpha, dynamics | 0.01-0.02 | assumed; results are alpha-sensitive |
| alpha, static loop | 1 | assumed; numerical only, does not move the minimum |
| initial state | `Uniform` along the easy axis | assumed; another start may find another minimum |
| solver | 5 (Dormand-Prince) | assumed |
| temperature | 0 | assumed |

### Targets, strongest first

`analytic` (a closed form the paper derives) -> `stated` (a number in the text)
-> `digitised` (points read off a figure) -> `qualitative`.

**Prefer the analytic target even when a figure is what you were asked to
reproduce.** If the paper derives the curve it plots, matching the derivation is
matching the figure - checkable to three digits instead of by eye.

## 3. Build and run

Hand the spec to **mx3-authoring**, which enforces the header: every assumed
value must appear on the `Unverified` line. Then **mx3-run**.

To target a single cell rather than a sample average:

```go
TableAdd(Crop(m, 0, 1, 0, 1, 0, 1))   // -> m_xrange0_x/y/z in table.txt
```

This reports the cell *centre*, half a cell inside the boundary - a real offset
for edge quantities on a coarse mesh.

## 4. Verify

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/mx3-paper/scripts/verify_repro.py \
        spec.json sim.out
```

PASS/FAIL per target with the size of the gap. A target that could not be
measured is reported as unchecked, never as a pass.

When something misses it prints what you may change, in order. Follow that
order - the first two categories have nothing to do with the paper's physics:

1. **Numerics.** Mesh converged (`mx3-check`)? Boundary conditions? Demag
   matching the paper's model? These look exactly like physics disagreements.
2. **Assumed parameters.** Vary one at a time with **mx3-tune**.
3. **The model.** Something the paper simulates that you have not built.
4. **Stated values** - not to change them, but to report what would be required.

## The rule

**Never adjust a stated value to reach agreement.** If the figure only
reproduces with a different Ms than the paper reports, that *is* the result:
report the required value and the discrepancy.

Equally, never reach for a fudge with no physical meaning - a scale factor on
the output, a tolerance widened until it passes, a target quietly dropped. Every
change must be a physical or numerical choice you can name and justify from the
paper's own text.

## Worked example: when it disagrees

`assets/worked-example/` reproduces the 1D edge-tilting problem of
arXiv:1803.11174. Read it for the middle of the story.

Every stated parameter was correct, and the first run gave a 28 deg edge tilt
against the analytic 41 deg. What followed:

- refined the mesh 8x - converged to 28.8 deg, so **not** discretisation
- doubled the DMI - saturated at 0.80, so **not** a unit convention
- found `OpenBC`, a mumax3 setting the paper never mentions because the paper is
  not about mumax3. The paper's Eq. 11 boundary condition *is* the free-spin
  condition. Setting it: 40.5 deg, converging to the analytic value.

No stated parameter was touched. The false answer had been stable and
mesh-converged, so convergence testing alone would not have caught it - which is
why the protocol checks conventions before concluding anything about physics.

`references/simulator-conventions.md` catalogues these: boundary conditions,
demag inclusion, bare `Ku1` versus effective `Keff`, DMI type and sign, and the
unit traps (`emu/cm3`, `Ms` quoted as mu0*Ms in tesla).

## Reverse direction: your own methods section

Everything needed is already in the output directory.

```bash
${CLAUDE_PLUGIN_ROOT}/lib/mx3 provenance sim.out --script
```

Include, because they change the numbers: exact build **and commit**; cell size
and that it is below the exchange length; a convergence statement from
**mx3-check** or an explicit note that it was not tested; any approximation
enabled (`SpeculativeStep` and `DemagExtrapolation` alter the trajectory by
design); and for thermal runs, that this port uses Philox rather than XORWOW, so
agreement with a CUDA run is statistical, not trajectory-by-trajectory.

Ship the `.mx3`, `log.txt`, the build identifier, and the `references.bib`
mumax3 writes into every output directory.

## Related skills

- **mx3-authoring** - writes the script and enforces the assumption header
- **mx3-run** - runs it and extracts the observable
- **mx3-check** - the convergence statement, and step 1 of any disagreement
- **mx3-tune** - varies an assumed parameter to test how much it matters
