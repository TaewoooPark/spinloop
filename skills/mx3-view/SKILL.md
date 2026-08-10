---
name: mx3-view
description: >-
  Turn a simulated magnetisation into a picture or a movie - domain images,
  skyrmion and vortex colour maps, MOKE-style black and white, line profiles
  through a wall, and animations of the texture evolving. Reads .ovf directly,
  so it works on a plain release install with no extra tools. Use for "show me
  what it looks like", "make a picture of the domains", "is that actually a
  skyrmion", "make a movie of the domain wall moving", "plot the wall profile",
  "render this like a Kerr image", "export the field to numpy".
---

# Showing the magnetisation

A number cannot tell you whether the thing you measured is the thing you think
you measured. A skyrmion and a stripe domain give the same spatial average.
Only the picture separates them, so look at the texture before trusting any
quantity extracted from it.

`.ovf` is read directly by this plugin — a plain ASCII header and float32 data.
`mumax3-convert` is **not** in the published release, so nothing here depends
on it. (The reader was checked against `mumax3-convert` on the same file: the
arrays agree exactly.)

## Pictures

```bash
${CLAUDE_PLUGIN_ROOT}/lib/mx3 view sim.out                      # last snapshot, m_z
mx3 view sim.out --mode angle                                    # skyrmion/vortex colour wheel
mx3 view sim.out --mode component --comp z --arrows 24           # m_z map with in-plane arrows
mx3 view sim.out --mode kerr                                     # two-level, like polar MOKE
mx3 view sim.out --which all --out frames/                       # every snapshot
mx3 view sim.out --z 2                                           # a particular layer
```

Pick the mode from the question:

| The user asked | Mode |
|---|---|
| "what do the domains look like" | `component` (default) |
| "is that a skyrmion? which chirality?" | `angle` — hue shows the in-plane rotation |
| "how does it compare to my Kerr image" | `kerr` |
| "which way do the moments point" | `component --arrows 24` |

`angle` mode is the one worth reaching for with any topological texture. It is
the standard colour wheel: **black core, white background, saturated hue ring**
whose rotational sense is the chirality. A single-component map throws that
away — a Néel and a Bloch skyrmion look identical in `m_z`.

## Movies

```bash
mx3 movie sim.out --mode angle --fps 12
mx3 movie sim.out --out wall.mp4
```

Needs several snapshots, which means the script must have recorded them:

```go
AutoSave(m, 100e-12)     // one .ovf every 100 ps
```

If only one snapshot exists, say so and point at `AutoSave` rather than
producing a one-frame film. Writes `.mp4` when ffmpeg is present, `.gif`
otherwise.

## Profiles

```bash
mx3 profile sim.out --along x            # cut through the middle row
mx3 profile sim.out --along y --row 40
```

The conventional way to show a domain wall: all three components against
position, so the wall width and its type (Néel rotates in the cut plane, Bloch
out of it) are both visible.

## Raw data

```bash
mx3 export sim.out --which all --out arrays/
```

Writes `.npy` shaped `(z, y, x, component)`. Use when the user wants to do
their own analysis, or hand the array to MATLAB via `readNPY`/`writematrix`.

## What to look at, and what to say

Before quoting a number extracted from a texture, check the picture supports
it:

| Claim | What the picture must show |
|---|---|
| "the skyrmion is 25 nm across" | one compact reversed core, not a stripe or several |
| "the wall moved at 120 m/s" | a single wall, still a wall, not broken up |
| "it relaxed to a vortex" | one core, closed flux, not a multi-domain state |
| "the film is uniform" | no edge domains, no residual texture |

Report what the picture rules out, not just what it shows. "One compact core,
so the 25 nm is a skyrmion diameter and not a stripe width" is the useful
sentence.

## Practical notes

- Coarse meshes render blocky. That is honest — do not smooth it away with
  interpolation, because the blocks are the actual cells and their size is
  what `mx3-check` is about.
- `--z` picks the layer. For a multilayer, look at more than one: the texture
  can differ between layers and an average hides that.
- The colour scale is fixed to -1..+1 for `m_z`, so two runs are directly
  comparable by eye.

## Related skills

- **mx3-run** — the numbers to go with the picture
- **mx3-check** — whether the mesh under that picture is fine enough
- **mx3-match** — putting a `kerr` render next to a measured MOKE image
- **mx3-paper** — reproducing a published figure
