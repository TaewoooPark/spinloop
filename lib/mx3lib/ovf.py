"""Reading OOMMF/mumax3 OVF field files directly.

The rest of mx3lib is standard-library only, and .ovf work was delegated to
`mumax3-convert`. That turned out not to hold: the published mumax3-ultrafast
release ships the engine alone, so a fresh install has no converter and cannot
render a single picture of a magnetisation.

The format does not justify the dependency anyway. An OVF 2.0 file is a plain
ASCII header followed by either text numbers or little-endian floats, prefixed
by a sentinel that also tells you the byte order:

    # OOMMF OVF 2.0
    # xnodes: 58
    # ystepsize: 1e-09
    # valuedim: 3
    # Begin: Data Binary 4
    <float32 1234567.0><nx*ny*nz*valuedim float32>

OVF 1.0 is also accepted: it has no `valuedim`, carrying the component count in
`meshtype`/`valuemultiplier` instead, and its binary-4 sentinel differs.

Needs numpy, which every scientific Python has. Nothing else in mx3lib does.
"""

from __future__ import annotations

import re
import struct
from dataclasses import dataclass
from pathlib import Path

try:
    import numpy as np
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "reading .ovf needs numpy (pip install numpy). The rest of the plugin "
        "works without it."
    ) from exc


# Sentinels the writer puts in front of binary data, per OVF spec.
_SENTINEL = {
    ("2.0", 4): 1234567.0,
    ("2.0", 8): 123456789012345.0,
    ("1.0", 4): 1234567.0,
    ("1.0", 8): 123456789012345.0,
}


@dataclass
class Field:
    """One OVF segment: a rectangular grid of vectors or scalars."""

    data: "np.ndarray"          # (nz, ny, nx, ncomp)
    cellsize: tuple             # (dx, dy, dz) in metres
    origin: tuple               # (xmin, ymin, zmin) in metres
    title: str = ""
    labels: tuple = ()
    time_s: float | None = None
    path: Path | None = None

    @property
    def shape(self) -> tuple:
        nz, ny, nx, nc = self.data.shape
        return (nx, ny, nz, nc)

    @property
    def ncomp(self) -> int:
        return self.data.shape[3]

    @property
    def extent_nm(self) -> tuple:
        """(x0, x1, y0, y1) in nm, for imshow."""
        nz, ny, nx, _ = self.data.shape
        x0, y0 = self.origin[0] * 1e9, self.origin[1] * 1e9
        return (x0, x0 + nx * self.cellsize[0] * 1e9,
                y0, y0 + ny * self.cellsize[1] * 1e9)

    def layer(self, z: int = 0) -> "np.ndarray":
        """One xy plane, (ny, nx, ncomp)."""
        return self.data[z]

    def component(self, comp, z: int | None = None) -> "np.ndarray":
        """A single component by index or by name ('x', 'y', 'z')."""
        idx = {"x": 0, "y": 1, "z": 2}.get(str(comp).lower(), None)
        if idx is None:
            idx = int(comp)
        if idx >= self.ncomp:
            raise IndexError(
                f"component {comp} but this field has {self.ncomp} "
                f"({'scalar' if self.ncomp == 1 else 'vector'})"
            )
        return self.data[:, :, :, idx] if z is None else self.data[z, :, :, idx]

    def describe(self) -> str:
        nx, ny, nz, nc = self.shape
        dx, dy, dz = (c * 1e9 for c in self.cellsize)
        kind = "vector" if nc == 3 else f"{nc}-component"
        t = "" if self.time_s is None else f", t = {self.time_s:.4g} s"
        return (f"{self.title or 'field'}: {nx}x{ny}x{nz} {kind}, "
                f"cells {dx:g}x{dy:g}x{dz:g} nm{t}")


def _parse_header(raw: bytes) -> tuple[dict, int, str, int]:
    """Header keys, byte offset of the data, encoding, and OVF version."""
    head = {}
    version = "2.0"
    pos = 0
    encoding, width = "text", 0

    # Headers are ASCII; decode leniently so a stray byte cannot kill the parse.
    text = raw[:200_000].decode("latin-1")
    for line in text.splitlines(keepends=True):
        pos += len(line)
        s = line.strip()
        if not s.startswith("#"):
            continue
        body = s[1:].strip()
        low = body.lower()
        if low.startswith("oommf"):
            m = re.search(r"ovf\s*([\d.]+)", body, re.I)
            if m:
                version = m.group(1)
            continue
        if low.startswith("begin: data"):
            m = re.match(r"begin:\s*data\s+(binary\s*([48])|text)", low)
            if not m:
                raise ValueError(f"unrecognised data section: {body!r}")
            if m.group(1).startswith("binary"):
                encoding, width = "binary", int(m.group(2))
            else:
                encoding, width = "text", 0
            break
        if ":" in body:
            k, _, v = body.partition(":")
            head[k.strip().lower()] = v.strip()
    else:
        raise ValueError("no '# Begin: Data' section - not an OVF file?")
    return head, pos, encoding, width, version   # type: ignore[return-value]


def read(path: str | Path) -> Field:
    """Read the first segment of an OVF file."""
    path = Path(path)
    raw = path.read_bytes()
    head, offset, encoding, width, version = _parse_header(raw)

    def num(key, default=None, cast=float):
        v = head.get(key)
        if v is None:
            if default is None:
                raise ValueError(f"OVF header has no {key!r}")
            return default
        return cast(v.split()[0])

    nx, ny, nz = (int(num(k, cast=float)) for k in ("xnodes", "ynodes", "znodes"))
    dx, dy, dz = (num(k) for k in ("xstepsize", "ystepsize", "zstepsize"))
    x0, y0, z0 = (num(k, 0.0) for k in ("xmin", "ymin", "zmin"))

    if "valuedim" in head:
        ncomp = int(num("valuedim"))
    else:                       # OVF 1.0: vector unless it says otherwise
        ncomp = 1 if "scalar" in head.get("meshtype", "").lower() else 3

    count = nx * ny * nz * ncomp

    if encoding == "binary":
        fmt = "<f" if width == 4 else "<d"
        want = _SENTINEL[(version if version in ("1.0", "2.0") else "2.0", width)]
        got = struct.unpack(fmt, raw[offset:offset + width])[0]
        if abs(got - want) > abs(want) * 1e-6:
            raise ValueError(
                f"{path.name}: binary sentinel is {got!r}, expected {want!r}. "
                f"The file may be truncated, or written with an unexpected byte "
                f"order."
            )
        dtype = np.dtype("<f4" if width == 4 else "<f8")
        start = offset + width
        need = count * dtype.itemsize
        if len(raw) < start + need:
            raise ValueError(
                f"{path.name}: header promises {count} values ({need} bytes) but "
                f"only {len(raw) - start} remain - file is truncated."
            )
        flat = np.frombuffer(raw, dtype=dtype, count=count, offset=start)
    else:
        tail = raw[offset:].decode("latin-1")
        vals = []
        for line in tail.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            vals.extend(float(t) for t in line.split())
            if len(vals) >= count:
                break
        if len(vals) < count:
            raise ValueError(
                f"{path.name}: expected {count} values, found {len(vals)}"
            )
        flat = np.asarray(vals[:count], dtype=np.float64)

    data = np.asarray(flat, dtype=np.float64).reshape(nz, ny, nx, ncomp)

    time_s = None
    desc = head.get("desc", "")
    m = re.search(r"total simulation time:\s*([\deE.+-]+)", desc, re.I)
    if m:
        try:
            time_s = float(m.group(1))
        except ValueError:
            pass

    labels = tuple(head.get("valuelabels", "").split()) or ()
    return Field(data=data, cellsize=(dx, dy, dz), origin=(x0, y0, z0),
                 title=head.get("title", path.stem), labels=labels,
                 time_s=time_s, path=path)


def read_series(paths) -> list:
    """Read several snapshots, in the order given."""
    return [read(p) for p in paths]
