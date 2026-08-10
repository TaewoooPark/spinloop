---
name: mx3-lab
description: >-
  Build the simulation of a measurement, not just of a physics question - a VSM
  or MOKE major loop, a minor loop that turns round before saturation,
  coercivity against field angle, an FMR ringdown at a bias field. Emits the
  field sequence the instrument actually applies. Use for "simulate our VSM
  measurement", "same conditions as my MOKE", "minor loop", "switching field vs
  angle", "astroid", "FMR at 200 mT", "sweep the field like we do in the lab".
---

# Simulating a measurement

**mx3-match** compares against data you already took. This is the other
direction: the measurement *protocol* itself, turned into a field sequence.

Getting the sequence wrong makes the comparison meaningless however good the
physics is — a minor loop is not a major loop with a smaller range, and a
switching field at 45 degrees is not the same experiment as one at 0.

```bash
P=${CLAUDE_PLUGIN_ROOT}/skills/mx3-lab/scripts/protocol.py
python3 $P major   --Ms 800e3 --A 13e-12 --size 200e-9 --thick 20e-9 --out loop.mx3
python3 $P minor   ... --Breverse 25 --out minor.mx3
python3 $P astroid ... --angles 0 15 30 45 60 75 90 --out astroid.mx3
python3 $P fmr     ... --Bbias 200 --out fmr.mx3
```

Fields are given in **mT** and angles in **degrees**, because that is what the
instrument reads. The script converts to SI.

Always gate the result before running it:

```bash
${CLAUDE_PLUGIN_ROOT}/skills/mx3-authoring/scripts/vet.sh loop.mx3
```

## The four protocols

| | What it is | Why it is separate |
|---|---|---|
| `major` | saturate, sweep down, sweep back | the baseline VSM/MOKE loop |
| `minor` | turn round at `--Breverse`, before saturation | the loop does **not** close; it probes the reversal in progress, and the remanent state depends on where you turned |
| `astroid` | one loop per field angle | a far stronger test of shape and reversal mode than coercivity alone, and much less sensitive to defects |
| `fmr` | bias field, small transverse step, record the decay | frequencies come from the spectrum of the ringdown |

`astroid` writes a template with the angle on one line. Generate one file per
angle and batch them:

```bash
for a in 0 15 30 45 60 75 90; do
  sed "s/^angle_deg := .*/angle_deg := $a/" astroid.mx3 > astroid_$a.mx3
done
${CLAUDE_PLUGIN_ROOT}/lib/mx3 batch astroid_*.mx3 --jobs 3
```

## Reading the result

```bash
mx3 loop  sweep.out --field B_extx --moment mx     # Hc, Mr/Ms, squareness
mx3 view  sweep.out --mode kerr                    # what a polar MOKE would see
```

For the FMR ringdown, the frequencies are in the spectrum of the recorded
trace — `observe.peak_frequency` in the shared library, and compare against
`mx3 physics` for the Kittel prediction.

## What this cannot mirror

Say these plainly when reporting, because they are why a simulated loop and a
measured one differ even when everything else is right:

- **Sweep rate.** A quasi-static simulation relaxes fully at each step; a real
  sweep does not. Thermally activated reversal is rate-dependent and is not
  modelled at all at zero temperature.
- **Defects and edge roughness.** A clean simulated element reverses
  coherently and overestimates coercivity, often several-fold. See
  `mx3-match`.
- **Temperature.** Unless `Temp` is set, this is a 0 K measurement.
- **Ensemble.** A VSM measures many elements at once; this is one.

Shape, remanence and angular dependence transfer well. Absolute coercivity
does not.

## Related skills

- **mx3-match** — compare the result against the measured data
- **mx3-run** — run it and extract the loop metrics
- **mx3-view** — render it the way the microscope would show it
- **mx3-plan** — if the material regime is not settled yet
