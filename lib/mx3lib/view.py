"""Pictures of a magnetisation, in the conventions magnetists read.

Numbers alone cannot tell you whether the thing you measured is the thing you
think you measured. A skyrmion and a stripe domain give the same spatial
average; only the picture separates them.

Three renderings, each matching how the field is normally shown:

  component   one component as a diverging colour map (blue-white-red for
              m_z), the convention of every out-of-plane domain figure
  angle       hue for the in-plane direction, lightness for m_z - the standard
              skyrmion/vortex picture, where chirality is visible
  kerr        two-level black and white, mimicking what a polar MOKE
              microscope actually shows, so a simulation can be put next to a
              measured image

Needs numpy and matplotlib. The rest of mx3lib does not.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np

from .ovf import Field, read


def _mpl():
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        return plt
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "rendering needs matplotlib (pip install matplotlib). Field data can "
            "still be exported with `mx3 export`."
        ) from exc


def _angle_rgb(layer: np.ndarray) -> np.ndarray:
    """Hue = in-plane angle, lightness = out-of-plane component.

    The usual skyrmion colour wheel: the core reads white or black by its
    polarity, and the rotational sense of the surrounding hue shows chirality,
    which a single-component map throws away.
    """
    mx, my, mz = layer[..., 0], layer[..., 1], layer[..., 2]
    hue = (np.arctan2(my, mx) / (2 * math.pi)) % 1.0
    # HSL, not HSV: lightness carries m_z, so the picture reads the way every
    # skyrmion figure does -- black core, white background, and a fully
    # saturated ring where the moment lies in plane. HSV puts the in-plane ring
    # at low value instead, which comes out muddy.
    light = np.clip(0.5 * (mz + 1.0), 0.0, 1.0)
    sat = np.clip(np.hypot(mx, my), 0.0, 1.0)
    sat = np.where(sat < 1e-6, 0.0, 1.0) * sat

    c = (1.0 - np.abs(2.0 * light - 1.0)) * sat
    hp = hue * 6.0
    x = c * (1.0 - np.abs(hp % 2.0 - 1.0))
    z = np.zeros_like(c)
    seg = np.floor(hp).astype(int) % 6
    r = np.select([seg == 0, seg == 1, seg == 2, seg == 3, seg == 4, seg == 5],
                  [c, x, z, z, x, c])
    g = np.select([seg == 0, seg == 1, seg == 2, seg == 3, seg == 4, seg == 5],
                  [x, c, c, x, z, z])
    b = np.select([seg == 0, seg == 1, seg == 2, seg == 3, seg == 4, seg == 5],
                  [z, z, x, c, c, x])
    m0 = light - c / 2.0
    return np.clip(np.stack([r + m0, g + m0, b + m0], axis=-1), 0.0, 1.0)


def render(field: Field, out: str | Path, mode: str = "component",
           comp: str = "z", z: int = 0, arrows: int = 0,
           title: str | None = None, dpi: int = 150) -> Path:
    """One snapshot to a PNG. Returns the path written."""
    plt = _mpl()
    out = Path(out)
    layer = field.layer(z)
    ext = field.extent_nm

    fig, ax = plt.subplots(figsize=(6.4, 5.2))

    if mode == "component" or field.ncomp == 1:
        idx = {"x": 0, "y": 1, "z": 2}.get(comp.lower(), 0) if field.ncomp > 1 else 0
        img = layer[..., idx]
        im = ax.imshow(img, origin="lower", extent=ext, cmap="RdBu_r",
                       vmin=-1, vmax=1, interpolation="nearest")
        cb = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.03)
        cb.set_label(f"m_{comp}" if field.ncomp > 1 else (field.title or "value"))
    elif mode == "angle":
        if field.ncomp < 3:
            raise ValueError("angle mode needs a vector field")
        ax.imshow(_angle_rgb(layer), origin="lower", extent=ext,
                  interpolation="nearest")
    elif mode == "kerr":
        idx = {"x": 0, "y": 1, "z": 2}.get(comp.lower(), 2)
        ax.imshow(np.sign(layer[..., idx]), origin="lower", extent=ext,
                  cmap="gray", vmin=-1, vmax=1, interpolation="nearest")
    else:
        raise ValueError(f"unknown mode {mode!r}; use component, angle or kerr")

    if arrows and field.ncomp >= 2:
        ny, nx = layer.shape[:2]
        step = max(1, int(round(max(nx, ny) / arrows)))
        ys, xs = np.mgrid[0:ny:step, 0:nx:step]
        xn = ext[0] + (xs + 0.5) * field.cellsize[0] * 1e9
        yn = ext[2] + (ys + 0.5) * field.cellsize[1] * 1e9
        ax.quiver(xn, yn, layer[::step, ::step, 0], layer[::step, ::step, 1],
                  color="k", pivot="mid", scale=30, width=0.004, alpha=0.75)

    ax.set_xlabel("x (nm)")
    ax.set_ylabel("y (nm)")
    if title is None:
        title = field.describe()
        if field.time_s:
            title += ""
    ax.set_title(title, fontsize=10)
    fig.tight_layout()
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=dpi)
    plt.close(fig)
    return out


def profile(field: Field, out: str | Path, along: str = "x", z: int = 0,
            row: int | None = None, dpi: int = 150) -> Path:
    """A line cut through the field - the usual way a wall profile is shown."""
    plt = _mpl()
    out = Path(out)
    layer = field.layer(z)
    ny, nx = layer.shape[:2]

    if along.lower() == "x":
        j = ny // 2 if row is None else row
        line = layer[j, :, :]
        pos = (np.arange(nx) + 0.5) * field.cellsize[0] * 1e9 + field.origin[0] * 1e9
        xlabel = f"x (nm)   [row y = {j}]"
    else:
        i = nx // 2 if row is None else row
        line = layer[:, i, :]
        pos = (np.arange(ny) + 0.5) * field.cellsize[1] * 1e9 + field.origin[1] * 1e9
        xlabel = f"y (nm)   [column x = {i}]"

    fig, ax = plt.subplots(figsize=(7, 4.2))
    names = list(field.labels) or ["m_x", "m_y", "m_z"][:line.shape[1]]
    for k in range(line.shape[1]):
        ax.plot(pos, line[:, k], lw=2, label=names[k] if k < len(names) else f"c{k}")
    ax.axhline(0, color="k", lw=0.6, ls=":")
    ax.set_xlabel(xlabel)
    ax.set_ylabel("magnetisation")
    ax.grid(alpha=0.3)
    ax.legend()
    ax.set_title(field.describe(), fontsize=10)
    fig.tight_layout()
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=dpi)
    plt.close(fig)
    return out


def movie(paths, out: str | Path, mode: str = "component", comp: str = "z",
          z: int = 0, fps: int = 12, arrows: int = 0, dpi: int = 110) -> Path:
    """Animate a series of snapshots.

    Writes .mp4 when ffmpeg is available and .gif otherwise; the extension of
    `out` is honoured if it is one of those.
    """
    plt = _mpl()
    import matplotlib.animation as animation
    out = Path(out)
    paths = list(paths)
    if not paths:
        raise ValueError("no snapshots to animate")

    first = read(paths[0])
    ext = first.extent_nm
    fig, ax = plt.subplots(figsize=(6.4, 5.2))

    def frame_rgb(f: Field):
        layer = f.layer(z)
        if mode == "angle":
            return _angle_rgb(layer)
        idx = {"x": 0, "y": 1, "z": 2}.get(comp.lower(), 2)
        return layer[..., idx]

    if mode == "angle":
        im = ax.imshow(frame_rgb(first), origin="lower", extent=ext,
                       interpolation="nearest")
    else:
        im = ax.imshow(frame_rgb(first), origin="lower", extent=ext,
                       cmap="RdBu_r", vmin=-1, vmax=1, interpolation="nearest")
        fig.colorbar(im, ax=ax, fraction=0.046, pad=0.03).set_label(f"m_{comp}")
    ax.set_xlabel("x (nm)")
    ax.set_ylabel("y (nm)")
    ttl = ax.set_title("", fontsize=10)

    def update(i):
        f = read(paths[i])
        im.set_data(frame_rgb(f))
        t = "" if f.time_s is None else f"   t = {f.time_s * 1e9:.3f} ns"
        ttl.set_text(f"{Path(paths[i]).name}{t}")
        return im, ttl

    anim = animation.FuncAnimation(fig, update, frames=len(paths), blit=False)
    out.parent.mkdir(parents=True, exist_ok=True)

    from shutil import which
    if out.suffix.lower() == ".mp4" and which("ffmpeg"):
        anim.save(out, writer=animation.FFMpegWriter(fps=fps), dpi=dpi)
    else:
        out = out.with_suffix(".gif")
        anim.save(out, writer=animation.PillowWriter(fps=fps), dpi=dpi)
    plt.close(fig)
    return out
