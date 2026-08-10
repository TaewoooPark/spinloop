# spinloop

**Benchtop micromagnetics.** Run micromagnetic simulations on your Mac, get
answers instead of output directories.

A [Claude Code](https://claude.com/claude-code) plugin built on
[mumax3-ultrafast](https://github.com/TaewoooPark/mumax3-ultrafast), the Apple
Silicon Metal port of [mumax³](https://mumax.github.io/). Simulations that used
to mean a cluster queue finish in seconds on a laptop — which changes what you
can ask for. You can iterate inside a conversation.

## What it does

Six skills. Each one is a thing you would actually say out loud.

| Skill | You say | It does |
|---|---|---|
| **mx3-authoring** | "write me a hysteresis script" | Writes `.mx3`, and never shows you code that has not compiled. Catches unit and mesh errors `mumax3 -vet` cannot see. |
| **mx3-run** | "run it and show me" | Runs the simulation, then reports the curve and the number — not a folder of `.ovf` files. Diagnoses failures and divergence. |
| **mx3-tune** | "keep adjusting until it works" | Varies a parameter automatically until a target is met, or reports honestly that it cannot be. Also finds thresholds: the field where a sample switches, the anisotropy where a film turns perpendicular. |
| **mx3-check** | "can I trust this?" | Refines the mesh until the answer stops changing, and cross-checks against closed-form micromagnetics. Answers the reviewer question about convergence. |
| **mx3-match** | "match my measurement" | Compares a measured VSM/MOKE/AHE loop against simulation and finds the parameters that reproduce it — while being explicit about which features actually constrain what. |
| **mx3-paper** | "run it like this paper" | Turns a methods section into a runnable script, listing exactly which parameters the paper stated and which had to be assumed. Also writes your own methods paragraph. |

### Two things it will not do

- **Present unverified work as verified.** Every generated script passes
  `mumax3 -vet` before you see it, and reports separate what was checked
  mechanically from what you still have to judge as a physicist.
- **Claim your physics is right.** A converged mesh says nothing about whether
  the model matches your sample. The tooling removes mechanical failure so the
  remaining review is purely physical.

## Install

Requires macOS on Apple Silicon.

**1. Add the plugin.** In Claude Code:

```
/plugin marketplace add TaewoooPark/spinloop
/plugin install spinloop@spinloop
```

**2. Install the simulation engine.**

```
/setup
```

This downloads a ~4 MB verified release — **no Go, no Homebrew, no Xcode
required**. It checks the SHA-256 before installing, puts the binary in
`~/.local/share/spinloop/bin/`, and never touches `/usr/local`, `sudo`, or your
shell profile.

Already have `mumax3` on your `PATH`? It is left alone. Set `MUMAX3_BIN` to
choose which one the plugin uses.

### Checking the install

```
/setup --check
```

Reports what is installed, what the latest release is, and — more usefully —
probes the actual binary for the features the plugin depends on. Version
strings do not carry a commit hash, so a capability probe is the only check
that matches what will really run.

### Optional

- **matplotlib** — for quick plots. Without it you still get CSV.
- **`mumax3-convert`** — for rendering `.ovf` snapshots to PNG. It is not in
  the release; build from a source checkout (`cd mumax3-ultrafast && make`) if
  you want images. Everything else works without it.

## Try it

```
Write me a standard problem 4 script and run it.
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

## How it fits together

```
mx3-authoring  ──►  mx3-run  ──►  mx3-check
   writes            runs &         is it
   verified          reports        trustworthy
   scripts             │                │
                       ▼                │
                   mx3-tune  ◄──────────┘
                   repeat until
                   the target is met
                       ▲
                       │
              mx3-match / mx3-paper
              target comes from your
              data, or from a paper
```

All six share one library (`lib/mx3lib`), so "coercivity" means the same thing
in every skill.

## Requirements

- macOS on Apple Silicon (M1 or later)
- Python 3.9+ (standard library only)
- Claude Code

## Licence

GPL-3.0-or-later. See [LICENSE](LICENSE).

The simulation engine is [mumax3-ultrafast](https://github.com/TaewoooPark/mumax3-ultrafast),
derived from [mumax³](https://github.com/mumax/3) — cite
[Vansteenkiste et al., AIP Adv. 4, 107133 (2014)](https://doi.org/10.1063/1.4899186)
for any published work. Every simulation writes a `references.bib` telling you
what else to cite.
