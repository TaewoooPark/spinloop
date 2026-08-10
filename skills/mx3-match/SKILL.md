---
name: mx3-match
description: >-
  Compare a simulation against measured data — a VSM/MOKE/AHE hysteresis loop,
  a switching field, a measured domain wall velocity — and find the material
  parameters that reproduce it. Reports which features agree and which do not,
  instead of tuning until the numbers happen to match. Use for "match my
  measurement", "compare with my experiment", "reproduce this measured loop",
  "find the parameters for our sample", "compare my MOKE loop with a
  simulation", "fit parameters to
  my data", "reproduce this hysteresis loop", "compare with experiment".
---

# Matching a simulation to measured data

The one thing every simulation package assumes you already have is the thing
an experimentalist does not: the material parameters of *this* sample. This
skill works backwards from data.

## Say this before starting

Fitting a loop is an inverse problem. Several parameter sets reproduce the
same curve, and the one the search lands on is not necessarily the sample's.
That is not a reason to skip it — it is a reason to be explicit about which
features carry information:

| Feature | What it constrains | How trustworthy |
|---|---|---|
| Saturation level | Ms (if the signal is calibrated) | good |
| Mr/Ms, loop shape | anisotropy, geometry, reversal mode | good |
| Coercivity Hc | reversal *mechanism* | **weak** |
| Loop opening at high field | rotation, Ku | moderate |

**Coercivity is the trap.** A defect-free simulated element reverses
coherently, so it overestimates Hc — often several-fold. Real samples nucleate
at defects, edges and grain boundaries the simulation does not have. Forcing
Hc to match by lowering Ku or Ms gives parameters that are wrong for every
other observable.

Match Mr/Ms and shape first. Treat Hc agreement as a bonus, and say plainly
when it does not agree and why.

## Step 1 — read the measurement

Any two-column text or CSV: field, then signal. Units are converted for you
(`T`, `mT`, `Oe`, `kOe`, `A/m`, `kA/m`). Headers and `#`/`%`/`;` comments are
skipped. The signal can be raw instrument output — volts of Kerr rotation, emu,
Hall voltage — because both loops are normalised before comparison.

For AHE data, subtract the ordinary Hall background first: the linear-in-field
term is not magnetisation and will distort both saturation and squareness.

## Step 2 — simulate the same measurement

Use **mx3-authoring** to write a loop that sweeps the same field range along
the same axis, with the sample's real geometry. Getting the axis wrong is the
most common cause of a failed match, and it looks like a physics disagreement.

```go
TableAdd(B_ext)                      // required for the comparison
for B := 60.0; B >= -60.0; B -= 2.0 {
	B_ext = vector(B*1e-3, 0, 0)
	Relax()
	TableSave()
}
// and the ascending branch
```

Both branches matter: the comparison matches descending to descending and
ascending to ascending. A loop is multivalued in B, so a single branch can only
be compared with a single branch.

## Step 3 — compare

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/mx3-match/scripts/compare_loop.py \
  measured.csv sim.out --field-unit Oe --plot overlay.png
```

```
                  measured      simulated
  coercivity      30 mT         55 mT
  squareness      1.000         0.999
  branch RMS      0.816   (0 = identical, normalised units)
```

The verdict distinguishes the cases that mean different things:

- **shape agrees, Hc does not** — the expected outcome; the model is right and
  the sample has defects. Report the ratio, do not tune it away.
- **Hc agrees, shape does not** — the reversal mechanism differs. Check
  geometry, edge roughness, field axis, before touching material parameters.
- **neither agrees** — check units and field axis first. Most "disagreements"
  at this stage are an Oe/mT mix-up or a field along the wrong axis.

## Step 4 — search, if a parameter is genuinely unknown

Once the shape matches, hand the remaining unknown to **mx3-tune** with the
measured value as the target:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/mx3-tune/scripts/tune.py loop.mx3 \
  --param Ku_value --range 0.2e6 1.0e6 \
  --goal "loop:squareness >= 0.95" --budget 15 --time 1800
```

Search on the feature that actually constrains the parameter. Searching on
coercivity will converge — to the wrong answer, confidently.

Vary **one** parameter at a time. Two free parameters against one loop is
under-determined, and the search will find a value without finding the truth.
If two are genuinely unknown, get one from an independent measurement (Ms from
saturation, thickness from XRR) rather than from the same loop.

## Reporting

```
The simulated loop reproduces the measured shape: squareness 0.999 vs 1.000,
both fully square, both saturating by 40 mT.

Coercivity does not match: 55 mT simulated against 30 mT measured, a factor
of 1.8. This is the expected direction. The simulated element is defect-free
and reverses coherently; your sample almost certainly nucleates at an edge or
defect. I have NOT adjusted Ku to close this gap, because doing so would give
an anisotropy that is wrong for the resonance and the wall width.

What this constrains: shape and saturation are consistent with
Ms = 800 kA/m, Aex = 13 pJ/m.
What it does not: the coercivity, and therefore anything that depends on the
reversal mechanism.
```

## Beyond loops

The same logic holds for other measurements, without a dedicated script yet:

- **Domain wall velocity vs field** (MOKE, Kerr microscopy) — simulate with
  `ext_centerWall` and `TableAdd(ext_dwpos)`, compare slope with
  `mx3 velocity`. Below Walker breakdown the mobility is the cleanest
  parameter constraint available.
- **FMR frequency vs field** — compare against the Kittel formula from
  `mx3 physics`; the intercept gives anisotropy and the curvature gives Ms.
- **Switching field vs angle (astroid)** — a strong shape test, and much less
  sensitive to defects than Hc alone.

## Related skills

- **mx3-authoring** — write the loop that mirrors the measurement
- **mx3-run** — extract the simulated loop metrics
- **mx3-tune** — search the remaining unknown parameter
- **mx3-check** — confirm the match is not a mesh artefact
- **mx3-lab** — simulate the measurement protocol itself, not just its result
- **mx3-view** — a `kerr` render to put beside the measured image
