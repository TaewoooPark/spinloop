"""Reading a mumax3 output directory.

A mumax3 run leaves a self-describing directory:

    log.txt          the version banner, then every statement as it executed
    table.txt        tab-separated time series, one header line
    m000000.ovf      field snapshots
    references.bib   citations mumax3 decided your run needs

Nothing here re-implements a file format. `table.txt` is a TSV, and `.ovf` is
handed to `mumax3-convert`, which already emits numpy, csv, json, vtk and png.
The work is knowing which of those to ask for, and pulling the provenance back
out of log.txt so a directory can say what produced it.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from .table import Table


@dataclass
class Provenance:
    """Where a result came from. Read back out of log.txt."""

    version: str = ""       # "mumax 3.12 [darwin_arm64 go1.26.5(gc) Metal-3]"
    commit: str = ""
    gpu: str = ""
    backend: str = ""       # Metal | CUDA
    cpu: str = ""
    os: str = ""
    hostname: str = ""
    timestamp: str = ""
    script: str = ""        # the statements as executed
    citations: list = field(default_factory=list)

    @property
    def complete(self) -> bool:
        """False when the run suppressed the banner (-v=false), which means the
        directory cannot say which build made it."""
        return bool(self.version and self.commit)


class OutputDir:
    """One mumax3 output directory."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        if not self.path.is_dir():
            raise NotADirectoryError(f"not an output directory: {self.path}")
        self._table: Table | None = None
        self._prov: Provenance | None = None

    # -- discovery ---------------------------------------------------------

    @classmethod
    def find(cls, root: str | Path, recursive: bool = True) -> list["OutputDir"]:
        """Every output directory at or under `root`, oldest first.

        A directory counts if it holds a log.txt, which mumax3 always writes.
        """
        root = Path(root)
        if (root / "log.txt").is_file():
            return [cls(root)]
        pattern = "**/log.txt" if recursive else "*/log.txt"
        found = [cls(p.parent) for p in sorted(root.glob(pattern))]
        found.sort(key=lambda d: d.path.stat().st_mtime)
        return found

    # -- contents ----------------------------------------------------------

    @property
    def table(self) -> Table | None:
        if self._table is None:
            f = self.path / "table.txt"
            self._table = Table.read(f) if f.is_file() else None
        return self._table

    @property
    def ovfs(self) -> list[Path]:
        """Field snapshots, in the order mumax3 numbered them."""
        out = sorted(self.path.glob("*.ovf")) + sorted(self.path.glob("*.omf"))
        return sorted(set(out))

    def ovf_groups(self) -> dict[str, list[Path]]:
        """Snapshots grouped by quantity: m000001.ovf and m000002.ovf together."""
        groups: dict[str, list[Path]] = {}
        for p in self.ovfs:
            stem = re.sub(r"\d+$", "", p.stem) or p.stem
            groups.setdefault(stem, []).append(p)
        return groups

    @property
    def images(self) -> list[Path]:
        out = []
        for ext in ("*.png", "*.jpg", "*.gif", "*.svg"):
            out += sorted(self.path.glob(ext))
        return out

    @property
    def log(self) -> str:
        f = self.path / "log.txt"
        return f.read_text(encoding="utf-8", errors="replace") if f.is_file() else ""

    # -- provenance --------------------------------------------------------

    @property
    def provenance(self) -> Provenance:
        if self._prov is None:
            self._prov = self._parse_log()
        return self._prov

    def _parse_log(self) -> Provenance:
        p = Provenance()
        script: list[str] = []
        in_citations = False

        for line in self.log.splitlines():
            s = line.strip()
            if not s:
                continue
            if s.startswith("//"):
                body = s[2:].strip()
                if body.startswith("mumax"):
                    p.version = body
                elif body.startswith("commit hash:"):
                    p.commit = body.split(":", 1)[1].strip()
                elif body.startswith("GPU info:"):
                    p.gpu = body.split(":", 1)[1].strip()
                    m = re.search(r"backend=(\w+)", p.gpu)
                    if m:
                        p.backend = m.group(1)
                    elif "PTX" in p.gpu:
                        p.backend = "CUDA"
                elif body.startswith("CPU info:"):
                    p.cpu = body.split(":", 1)[1].strip()
                elif body.startswith("OS  info:") or body.startswith("OS info:"):
                    p.os = body.split(":", 1)[1].strip()
                    m = re.search(r"Hostname:\s*(\S+)", body)
                    if m:
                        p.hostname = m.group(1)
                elif body.startswith("Timestamp:"):
                    p.timestamp = body.split(":", 1)[1].strip()
                elif "cite the following references" in body:
                    in_citations = True
                elif in_citations and body.startswith("*"):
                    # Skip the banner rules: "****...****//" also starts with '*'.
                    entry = body.lstrip("* ").strip().rstrip("/").strip()
                    if entry and not set(entry) <= {"*", "/"}:
                        p.citations.append(entry)
                continue
            # Not a log line: mumax3 echoed a statement it executed.
            script.append(line.rstrip())

        p.script = "\n".join(script)
        return p

    # -- ovf export, delegated to mumax3-convert ---------------------------

    def export(self, ovf: Path, fmt: str = "numpy", out: Path | None = None,
               comp: str | None = None, extra: list[str] | None = None) -> Path:
        """Convert one snapshot. `fmt` is any mumax3-convert output flag:
        numpy, csv, json, vtk, png, jpg, gif, svg, gplot, dump.

        Returns the produced file. Raises RuntimeError with convert's own
        message on failure, which is more informative than anything we'd add.
        """
        ovf = Path(ovf)
        dest = Path(out) if out else ovf.parent
        dest.mkdir(parents=True, exist_ok=True)

        cmd = ["mumax3-convert", f"-{fmt}"]
        if fmt in ("ovf", "ovf2", "omf", "vtk"):
            cmd = ["mumax3-convert", f"-{fmt}", "binary"]
        if comp:
            cmd += ["-comp", comp]
        if extra:
            cmd += extra
        cmd += ["-o", str(dest), str(ovf)]

        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(
                f"mumax3-convert failed on {ovf.name}:\n{r.stderr.strip() or r.stdout.strip()}"
            )

        suffix = {"numpy": ".npy", "csv": ".csv", "json": ".json", "vtk": ".vts",
                  "png": ".png", "jpg": ".jpg", "gif": ".gif", "svg": ".svg",
                  "gplot": ".gplot", "dump": ".dump"}.get(fmt, "")
        produced = dest / (ovf.stem + suffix)
        if produced.exists():
            return produced
        # convert names some outputs by component; fall back to newest match
        cands = sorted(dest.glob(ovf.stem + "*"), key=lambda p: p.stat().st_mtime)
        if cands:
            return cands[-1]
        raise RuntimeError(f"mumax3-convert produced no output for {ovf.name}")

    # -- summary -----------------------------------------------------------

    def describe(self) -> dict:
        t = self.table
        prov = self.provenance
        return {
            "path": str(self.path),
            "table_rows": len(t) if t else 0,
            "table_columns": list(t.names) if t else [],
            "duration_s": (t.column("t")[-1] if t and len(t) and t.has("t") else None),
            "snapshots": {k: len(v) for k, v in self.ovf_groups().items()},
            "images": len(self.images),
            "version": prov.version,
            "commit": prov.commit,
            "backend": prov.backend,
            "timestamp": prov.timestamp,
            "provenance_complete": prov.complete,
        }
