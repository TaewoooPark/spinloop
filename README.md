<!-- markdownlint-disable MD033 -->

# spinloop

**Describe the simulation. Get the answer.**

<p align="center">
  <img src="https://img.shields.io/github/stars/TaewoooPark/spinloop?style=flat-square&logo=github&logoColor=white&labelColor=000000&color=333333" alt="GitHub stars">
  <img src="https://img.shields.io/github/last-commit/TaewoooPark/spinloop?style=flat-square&labelColor=000000&color=333333" alt="Last commit">
  <img src="https://img.shields.io/github/languages/top/TaewoooPark/spinloop?style=flat-square&labelColor=000000&color=333333" alt="Top language">
  &nbsp;
  <img src="https://img.shields.io/badge/Claude%20Code-000000?style=flat-square&labelColor=000000&color=000000" alt="Claude Code">
  <img src="https://img.shields.io/badge/Python-000000?style=flat-square&logo=python&logoColor=white&labelColor=000000" alt="Python">
  <img src="https://img.shields.io/badge/Apple%20Silicon-000000?style=flat-square&logo=apple&logoColor=white&labelColor=000000" alt="Apple Silicon">
  <img src="https://img.shields.io/badge/Metal-000000?style=flat-square&logo=apple&logoColor=white&labelColor=000000" alt="Metal">
  <img src="https://img.shields.io/badge/mumax³-000000?style=flat-square&labelColor=000000&color=000000" alt="mumax3">
  &nbsp;
  <img src="https://img.shields.io/badge/10%20skills-000000?style=flat-square&labelColor=000000&color=000000" alt="10 skills">
  <img src="https://img.shields.io/badge/Every%20script%20compiled-000000?style=flat-square&labelColor=000000&color=000000" alt="Every script compiled first">
  <img src="https://img.shields.io/badge/Paper%20PDF%20→%20figure-000000?style=flat-square&labelColor=000000&color=000000" alt="Paper PDF to figure">
  <img src="https://img.shields.io/badge/No%20cluster-000000?style=flat-square&labelColor=000000&color=000000" alt="No cluster">
  <img src="https://img.shields.io/badge/GPL--3.0--or--later-000000?style=flat-square&labelColor=000000&color=000000" alt="GPL-3.0-or-later">
</p>

spinloop turns micromagnetic simulation into something you can **ask for in
ordinary sentences**. You say what you want to know — *"find the field where
this film switches"*, *"is my mesh fine enough to trust"*, *"run it like this
paper"* — and it writes the mumax³ script, runs it on your Mac, reads the
output, and hands you the number with the caveats attached.

It is built on [mumax3-ultrafast](https://github.com/TaewoooPark/mumax3-ultrafast),
the Apple Silicon Metal port of [mumax³](https://mumax.github.io/). Simulations
that used to mean a cluster queue now finish in seconds on a laptop — which
changes what you can reasonably ask for. You can iterate inside a conversation
instead of inside a job scheduler.

The point is not to write your scripts for you. It is to **remove the mechanical
failures** — a typo that costs you an overnight run, a mesh too coarse to mean
anything, a paper's parameter in cgs pasted into an SI field — so that the only
thing left to review is the physics.

> *"A converged mesh tells you the number stopped moving. It does not tell you the number is right. spinloop removes everything except that question."*

[**taewoopark.com** — author site](https://taewoopark.com)

---

## New to this? Read this box first

If you have never used a tool like this, here is the whole idea in four
sentences.

**Claude Code** is a program you run in your Mac's Terminal and talk to in plain
English, the way you'd talk to a colleague. **spinloop** is an add-on that
teaches it micromagnetics: how to write mumax³ scripts, run them, read the
`.ovf` and `table.txt` output, and say whether the answer is trustworthy.

You do **not** write Python. You do **not** learn a new interface. You type what
you want, and you get a number, a plot, or a picture back — plus a plain
statement of what was checked mechanically and what you still have to judge as a
physicist.

Setup is two commands, below. If you can open Terminal, you can run this.

---

## Why this exists

Micromagnetics is a standard instrument in an experimental magnetism group, and
almost nobody in one has time to become a simulation person. The barrier was
never the physics — it is everything around it:

- **The script has to be exactly right.** `.mx3` is a small language with sharp
  edges. `SetGridSize(128e-9, 32, 1)` passes mumax³'s own syntax check and then
  crashes at runtime. An `Ms` in emu/cm³ where the code wants A/m runs happily
  and gives you a wrong answer with three confident digits.
- **A number is not an answer.** Coercivity from a 8 nm mesh and coercivity from
  a 2 nm mesh can differ by 20%. Nobody tells you which one you got.
- **The Mac was a second-class machine.** Upstream mumax³ is CUDA-only. Until
  mumax3-ultrafast, a physicist with a MacBook had to keep a Linux box, rent
  one, or wait on the CPU.

The last one is now solved, and that changes the first two. When a run takes
seconds instead of an overnight queue slot, *checking* becomes cheap — you can
afford to refine the mesh three times, cross-check against a closed-form
estimate, and re-run a sweep, all inside one conversation. spinloop is the layer
that makes you actually do it.

---

## The ten things you can say

Each skill is a sentence you'd say out loud. You never invoke them by name —
just say what you want.

| You say | What you get |
|---|---|
| *"write me a hysteresis script"* | **mx3-authoring** — a `.mx3` file that has already been compiled. You are never shown code that does not run. It also catches unit and mesh mistakes that mumax³'s own checker cannot see. |
| *"run it and show me"* | **mx3-run** — the simulation runs, and you get the curve and the number. Not a folder of `.ovf` files. If it diverges or stalls, you're told why. |
| *"keep adjusting until it works"* | **mx3-tune** — varies a parameter automatically until your target is met, or reports honestly that it cannot be. Also finds thresholds: the field where a sample switches, the anisotropy where a film turns perpendicular. |
| *"can I trust this?"* | **mx3-check** — refines the mesh until the answer stops changing, then cross-checks against textbook micromagnetics. This is the reviewer's convergence question, answered before they ask it. |
| *"match my measurement"* | **mx3-match** — takes your measured VSM / MOKE / AHE loop and finds parameters that reproduce it, while telling you which features of the loop actually constrain which parameter. |
| *"run it like this paper"* | **mx3-paper** — give it the PDF. It pulls out the parameters, converts the units, writes the script, and lists exactly which values the paper stated and which had to be assumed. It also writes your own methods paragraph. |
| *"show me what it looks like"* | **mx3-view** — domain images, skyrmion colour maps, MOKE-style renders, wall profiles, movies. Reads `.ovf` itself, so nothing extra to install. |
| *"what should I even simulate?"* | **mx3-plan** — from your material parameters: which magnetic states are possible, where the boundaries are, what mesh you need, what it will cost. Instant — nothing is simulated. |
| *"simulate our VSM measurement"* | **mx3-lab** — builds the field sequence a real instrument applies: major and minor loops, switching field vs. angle, FMR ringdown. |
| *"what did I run last time?"* | **mx3-log** — a lab notebook rebuilt from the output folders themselves. What ran, what it settled at, what is still open. |

All ten share one library, so **"coercivity" means the same thing in every
skill** — the same reader, the same definition, the same units.

---

## What it looks like

Real output from this repository, not a mock-up.

### Before you simulate anything

You have a CoFeB film and a question. This costs one second and zero GPU time:

```
$ skills/mx3-plan/scripts/plan.py --Ms 1050e3 --A 19e-12 --Ku 1.2e6 \
      --thickness 1e-9 --width 200e-9

Material
  Ms 1.05e+06 A/m   A 1.9e-11 J/m   Ku 1.2e+06 J/m3
  exchange length      5.24 nm
  shape anisotropy     6.927e+05 J/m3   (mu0*Ms^2/2)
  effective anisotropy +5.073e+05 J/m3   (PERPENDICULAR easy axis)
  domain wall width    19.23 nm  (pi*sqrt(A/Keff))

Mesh
  cell size            <= 5.24 nm required, 2.62 nm comfortable
  for 200 x 200 x 1 nm at 2.62 nm: 77 x 77 x 1 = 5,929 cells
  77x77 is in the latency-bound regime: a fixed ~180 us per evaluation
  dominates, so a faster GPU or a bigger mesh will not help.

Worth running, in this order
  - relax from Uniform(0,0,1) and from RandomMag(), compare E_total - if they
    differ, the ground state is not what you assumed
  - hysteresis loop along z: coercivity and squareness
  - confirm the answer does not move under mesh refinement
```

### The mistake it catches before you waste a night

Now suppose you take that **effective** anisotropy, `+5.073e5 J/m³`, and paste it
straight into `Ku1`. That is a real mistake, it is extremely easy to make, and
mumax³ will run it without complaint:

```
$ skills/mx3-authoring/scripts/lint_mx3.py skyrmion.mx3

skyrmion.mx3:6: ERROR: [R-KEFF] Ku1 = 507300 J/m3 with Msat = 1.05e+06 A/m
  gives Keff = -1.854e+05 J/m3, so the film has no perpendicular easy axis -
  but the script initialises a perpendicular texture.
    -> Either the texture cannot be stable, or Ku1 has been given an
       ALREADY-EFFECTIVE anisotropy while demag is on, which subtracts
       mu0*Ms^2/2 = 6.927e+05 J/m3 twice. If the source quotes Keff,
       set Ku1 = Keff + 6.927e+05.
```

Demagnetisation is already switched on, so mumax³ subtracts the shape term
*again*. Your "perpendicular" film is in-plane, your skyrmion collapses, and
nothing in the log says so. Caught in milliseconds, before the run.

### The paper is in cgs and your code is in SI

```
$ mx3 convert 1400 emu/cm3 Msat     →  1.4e+06 A/m
$ mx3 convert 8.5 kOe field         →  0.85 T
                                       H = 6.764e+05 A/m converted as mu0*H = 0.85 T
$ mx3 convert 1.3e-6 erg/cm Aex     →  1.3e-11 J/m
$ mx3 convert 0.9 mJ/m2 DMI         →  0.0009 J/m2
```

Conversion is done by dimensional analysis, not a lookup table, so it handles
prefixes and combinations it has never seen. Where a unit is genuinely ambiguous
— magnetisation quoted in tesla, moments in emu — it **refuses to guess** and
asks you which convention the paper meant.

---

## Two things it will not do

- **Show you unverified work as if it were verified.** Every generated script
  passes mumax³'s own compiler before it reaches you, and every report keeps
  what was checked mechanically separate from what you still have to judge.
- **Tell you your physics is right.** A converged mesh says nothing about
  whether your model matches your sample. The tooling removes mechanical
  failure so that the remaining review is purely physical — which is the part
  only you can do.

---

## What it catches that a fast simulator does not

A faster GPU runs the wrong simulation faster. These are the failures that
survive speed, and each has a check behind it:

- **A converged answer that is still wrong.** Refining the mesh makes a number
  stop moving — including when a boundary-condition setting is wrong for your
  problem. Papers rarely state such settings, because papers are not about
  mumax³. Convergence testing alone will never find this; a cross-check against
  the closed-form answer will.
- **Parameters that describe an impossible simulation.** If a paper's stated
  `A` and `Ms` give an exchange length shorter than the material's own lattice
  constant, then no valid continuum simulation exists at any cell size. That is
  a result about the paper, and reporting it is more useful than producing a
  number.
- **A number lost between the PDF and the script.** A superscript minus sign
  dropped by a PDF extractor turns `1.3 × 10⁻¹¹` into `1.3 × 10¹¹` — twenty-two
  orders of magnitude, and perfectly plausible-looking in a table. Every
  extracted value is range-checked against what that quantity can physically be.

---

## Install

Requires **macOS on Apple Silicon** (M1 or newer).

**1 · Add the plugin.** In Claude Code, type:

```
/plugin marketplace add TaewoooPark/spinloop
/plugin install spinloop@spinloop
```

**2 · Install the simulation engine:**

```
/spinloop:setup
```

That downloads a **verified ~4 MB release** — **no Go, no Homebrew, no Xcode**.
It checks the SHA-256 before installing, puts the binary in
`~/.local/share/spinloop/bin/`, and never touches `/usr/local`, never asks for
`sudo`, and never edits your shell profile.

Already have `mumax3` on your `PATH`? It is left completely alone. Set
`MUMAX3_BIN` to choose which one the plugin uses.

### Checking the install

```
/spinloop:setup --check
```

Reports what is installed and what the latest release is — and, more usefully,
**probes the actual binary** for the features the plugin depends on. A version
string does not carry a commit hash, so asking the binary what it can do is the
only check that matches what will really run.

---

## Try it

Paste any of these into Claude Code once the plugin is installed.

```
Write me a standard problem 4 script and run it.
```

```
I have a CoFeB film, Ms 1050 kA/m, Ku 1.2 MJ/m3. What is worth simulating?
```

```
Find the anisotropy where a 64 nm CoFeB film turns perpendicular.
```

```
Is my 8 nm cell fine enough for this coercivity?
```

```
Here is my measured MOKE loop. What parameters reproduce it?
```

```
Here is a paper PDF. Reproduce Figure 3.
```

```
Show me what the domains look like, and make a movie of the wall moving.
```

---

## How the skills fit together

```
  mx3-authoring  ──►   mx3-run   ──►  mx3-check
   writes a            runs it &        is the answer
   script that         reports the      trustworthy?
   compiles            number
                           │                 │
                           ▼                 │
                       mx3-tune  ◄───────────┘
                       repeat until the
                       target is met
                           ▲
                           │
                  mx3-match  /  mx3-paper
                  the target comes from your
                  own data, or from a paper


                        mx3-view
              a picture of what those numbers describe
```

Before any of it, **mx3-plan** answers *what is worth simulating at all*, and
**mx3-lab** builds the field sequence when the goal is to mirror a bench
measurement. **mx3-log** keeps the record across sessions, so next month's you
does not re-derive this month's conclusions.

---

## What it needs

| | |
|---|---|
| **Required** | macOS on Apple Silicon (M1+) · Claude Code · Python 3.9+ (standard library only) |
| **For plots** | matplotlib — without it you still get CSV |
| **For pictures and movies** | numpy + matplotlib — almost every scientific Python already has both. Without them, fields export as `.npy` |
| **For `.mp4`** | ffmpeg — without it you get `.gif` |

`.ovf` files are read by the plugin itself, so **`mumax3-convert` is not
required** even though the published release does not ship it. The reader was
checked against `mumax3-convert` on the same file: the arrays agree exactly.

---

## Scope

Stated plainly, because a tool that hides its edges is worth nothing:

- **It does not validate your physics.** It validates that your script compiles,
  that your mesh resolves the length scales, and that your numbers are
  internally consistent. Whether the model describes your sample is your call
  and always will be.
- **Apple Silicon only.** The engine is a Metal port. On Linux or Windows with
  an NVIDIA card, use upstream mumax³ directly — the scripts this writes are
  ordinary `.mx3` and run there unchanged.
- **A reproduction that disagrees is still a result.** When a paper cannot be
  reproduced, the useful output is the diagnosed reason, not a fudged number.
  Hardcoding a parameter to force agreement is explicitly out of scope.
- **Thermal runs are reproducible, not identical to CUDA.** The engine uses
  Philox rather than cuRAND's XORWOW, so a seed reproduces on Metal but does not
  replay CUDA's sample-by-sample trajectory.

---

## Built on

The simulation engine is
[mumax3-ultrafast](https://github.com/TaewoooPark/mumax3-ultrafast), a native
Metal port of [mumax³](https://github.com/mumax/3) — 3.3× to 30× faster than
every other micromagnetic simulator that runs on Apple Silicon, and validated
against the upstream CUDA-era references.

Cite [Vansteenkiste et al., *AIP Advances* **4**, 107133 (2014)](https://doi.org/10.1063/1.4899186)
for any published work. Every simulation also writes a `references.bib`
telling you what else to cite for the features it used.

Distributed under the [GNU GPL v3 or later](LICENSE).

---

## Creator

I am **Taewoo Park**, an undergraduate physics student at the Korea Advanced
Institute of Science and Technology (KAIST). Since October 2025 I have conducted
experimental spintronics research on magnetic domain wall motion and
neuromorphic computing applications at the
[KAIST Ultrafast Spin Dynamics Laboratory (USDL)](https://spintronics.kaist.ac.kr/),
led by **Professor Kab Jin Kim**. From June 2023 through March 2024 I studied
domain wall motion through theoretical modeling and micromagnetic simulation in
the KAIST Quantum Spin Dynamics Laboratory under **Professor Se Kwon Kim**.

spinloop is the tool I wanted while doing that work.

<p align="center">
  <a href="https://github.com/TaewoooPark"><img src="https://img.shields.io/badge/-GitHub-181717?style=for-the-badge&logo=github&logoColor=white&cacheSeconds=3600" alt="GitHub"></a>
  <a href="https://x.com/theoverstrcture"><img src="https://img.shields.io/badge/-X-000000?style=for-the-badge&logo=x&logoColor=white&cacheSeconds=3600" alt="X (Twitter)"></a>
  <a href="https://www.linkedin.com/in/taewoo-park-427a05352"><img src="https://img.shields.io/badge/-LinkedIn-0A66C2?style=for-the-badge&logo=linkedin&logoColor=white&cacheSeconds=3600" alt="LinkedIn"></a>
  <a href="https://taewoopark.com"><img src="https://img.shields.io/badge/-taewoopark.com-000000?style=for-the-badge&logo=safari&logoColor=white&cacheSeconds=3600" alt="Personal site"></a>
  <a href="mailto:ptw151125@kaist.ac.kr"><img src="https://img.shields.io/badge/-Email-D14836?style=for-the-badge&logo=gmail&logoColor=white&cacheSeconds=3600" alt="Email"></a>
</p>

<p align="center"><sub>Ask in sentences. Get an answer, not a folder. Nothing unverified reaches you.</sub></p>
