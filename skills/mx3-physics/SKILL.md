---
name: mx3-physics
description: >-
  Reference library of micromagnetic theory for planning and checking
  simulations: units and typical material values, characteristic lengths,
  energies and times, domain walls and their motion, skyrmions and
  vortices, spin waves and FMR, reversal and hysteresis, thermal effects,
  the numerics of mumax3, fitting and identifiability, spin torques. Closed
  forms with their regime of validity, sanity checks, how a simulation
  measures each quantity, common mistakes, references. Use for "what value
  should I expect", "is this number plausible", "which formula gives a
  starting value", "why does the simulation disagree with theory", "which
  cell size", "how do I measure X in mumax3", "which parameter does this
  observable depend on", "what does this unit mean".
---

# Micromagnetics reference library

A closed form does two jobs in a simulation study.
- **Before running**, it gives starting values and an expectation.
- **After running**, it says whether a result is plausible.

It never replaces a simulation of the actual geometry. Every formula here
states its assumptions; a real geometry (finite size, edges, demagnetising
fields, discretisation) can deviate, and the chapters say by roughly how much.
When a formula and a careful, converged simulation disagree, the simulation,
which makes fewer approximations, is the better reference; the formula is the
approximation.

## Chapters

Read with the `Read` tool:
`${CLAUDE_PLUGIN_ROOT}/skills/mx3-physics/references/<file>`.

| file | covers | read it when |
|---|---|---|
| `01-units-and-magnitudes.md` | SI and CGS, mumax3 parameter units, typical values of common materials, field magnitudes, signs of a unit error | entering parameters; a result off by 10³ or 4π |
| `02-scales.md` | exchange length, wall width, Q, K_eff, wall energy, critical DMI, time scales, cell-size rules | before choosing a mesh; for orders of magnitude |
| `03-domain-walls.md` | static walls: profiles and width definitions, energy, Bloch versus Néel, DMI and chirality, walls in strips, applied-field effects, pinning, measuring widths | any static wall question |
| `04-wall-dynamics.md` | field-driven motion, the 1D (q, φ) model, Walker breakdown, DMI, what the 1D model misses, measuring velocities | wall motion under field |
| `05-skyrmions-vortices.md` | skyrmion size and stability, topological charge, Thiele equation and Hall angle, vortex cores and gyration | skyrmions, bubbles, vortices |
| `06-spin-waves-fmr.md` | Kittel formulas, M_eff, linewidth and damping, dispersion, DMI nonreciprocity, ringdown and FFT practice | resonance, spin waves, extracting α |
| `07-reversal-hysteresis.md` | Stoner–Wohlfarth, Brown's paradox, reversal modes, demagnetising factors, loop simulation practice, multilayers | loops, coercivity, switching |
| `08-thermal.md` | Temp in mumax3, temperature scaling of parameters, Néel–Brown, thermal stability, statistics | finite temperature, retention, creep |
| `09-numerics.md` | discretisation, float32 precision, solvers, Relax versus Minimize versus Run, boundaries, moving frames, robust observables, convergence tests | before trusting any number; odd results |
| `10-inverse-problems.md` | χ², Levenberg–Marquardt, Jacobians and noise, identifiability, correlations, local minima, model discrepancy, uncertainty | fitting parameters to data (with **mx3-fit**) |
| `11-spin-torques.md` | Zhang–Li and Slonczewski torques, SOT, current-driven walls and skyrmions, sign conventions | currents |

## Using a formula

1. **Units first.** mumax3 takes SI throughout, and `B_ext` is in tesla. Chapter 01
   lists the conversions that go wrong.
2. **Check the regime.**
   - Thin film or bulk; 1D or 2D; rigid profile or not.
   - Small amplitude; below or above an instability (Walker breakdown,
     switching, nucleation).
   - Each formula says where it holds.
3. **Estimate the bias.** A closed form is often off by a few to tens of percent
   in a real geometry. That bias can be far larger than the noise in good data,
   so a value from a formula is a start, not a result.
4. **Compare with a simulation.**
   - Simulate the actual geometry once at the estimate and look at which
     quantities miss, and by how much.
   - A miss that is the same sign across one kind of observable points to the
     model or the regime, not the noise.
5. **Disagreement.**
   - Check the units, the regime and the numerics (chapter 09) before
     doubting the physics.
   - **mx3-consult** can reason it through with you.

The command `${CLAUDE_PLUGIN_ROOT}/lib/mx3 physics --Ms .. --A .. --Ku1 .. --D ..`
evaluates the main length and energy scales for a given set of parameters.

## Constants

| quantity | value |
|---|---|
| µ0 | 4π × 10⁻⁷ T·m/A = 1.25664 × 10⁻⁶ |
| γ (mumax3 `GammaLL` default) | 1.7595 × 10¹¹ rad/(s·T); γ/2π = 28.0 GHz/T |
| µB | 9.274 × 10⁻²⁴ J/T |
| kB | 1.380649 × 10⁻²³ J/K; kB·300 K = 4.14 × 10⁻²¹ J |
| e | 1.602 × 10⁻¹⁹ C |
| ħ | 1.0546 × 10⁻³⁴ J·s |

## Related skills

- **mx3-consult**: ask the expert session that holds this library
- **mx3-fit**: fit parameters once you know which data constrain which
  parameter
- **mx3-authoring**: `references/units-and-scales.md` and `pitfalls.md`, for
  script-level conventions
