#!/usr/bin/env python3
"""A lab notebook for a folder of simulations.

    notebook.py scan .                      what is in this folder, and when
    notebook.py note "Hc converged at 4nm"  record a conclusion
    notebook.py show                        the notebook so far
    notebook.py open                        what is still unresolved

Research on one sample runs over weeks. Without a record, every session starts
by re-deriving what was already settled, and the person least able to reload
that context is the one who did not write the scripts.

`scan` reads the output directories themselves - each carries the script that
produced it and the build that ran it - so the history is reconstructed from
evidence rather than from memory. Notes and open questions are the part a
person adds.

Everything lives in one file, MX3-NOTEBOOK.md, next to the simulations. It is
plain markdown so it can be read, edited and committed without this tool.
"""

from __future__ import annotations

import argparse
import datetime
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
for cand in (HERE.parents[3] / "lib", HERE.parents[2] / "lib"):
    if (cand / "mx3lib").is_dir():
        sys.path.insert(0, str(cand))
        break

from mx3lib import OutputDir  # noqa: E402

NAME = "MX3-NOTEBOOK.md"
RUNS = "## Runs"
NOTES = "## Notes"
OPEN = "## Open questions"


def notebook_path(root: Path) -> Path:
    return root / NAME


def load(path: Path) -> dict:
    if not path.is_file():
        return {RUNS: [], NOTES: [], OPEN: []}
    section, out = None, {RUNS: [], NOTES: [], OPEN: []}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip() in (RUNS, NOTES, OPEN):
            section = line.strip()
            continue
        if section and line.strip().startswith("-"):
            if line.strip() == "- (none yet)":   # placeholder, not an entry
                continue
            out[section].append(line.rstrip())
    return out


def save(path: Path, data: dict, title: str) -> None:
    parts = [f"# {title}", "",
             "Written by mx3-log. Plain markdown - edit or commit it freely.", ""]
    for sec in (RUNS, NOTES, OPEN):
        parts.append(sec)
        parts.append("")
        parts.extend(data[sec] or ["- (none yet)"])
        parts.append("")
    path.write_text("\n".join(parts) + "\n", encoding="utf-8")


def stamp() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")


def summarise_run(out: OutputDir) -> str:
    d = out.describe()
    prov = out.provenance
    script = prov.script or ""
    # the lines that define what was simulated, not the whole echo
    keys = []
    for pat in (r"SetGridSize\([^)]*\)", r"SetCellSize\([^)]*\)",
                r"Msat\s*=\s*\S+", r"Aex\s*=\s*\S+", r"Ku1\s*=\s*\S+",
                r"Dind\s*=\s*\S+", r"alpha\s*=\s*\S+"):
        m = re.search(pat, script)
        if m:
            keys.append(m.group(0))
    when = prov.timestamp or "unknown time"
    bad = ""
    t = out.table
    if t and t.nan_columns():
        bad = "  **DIVERGED (NaN)**"
    return (f"- `{out.path.name}` — {when}, {d['table_rows']} rows, "
            f"{sum(d['snapshots'].values())} snapshots{bad}\n"
            f"  - {'; '.join(keys) if keys else 'script not recorded'}")


def cmd_scan(args) -> int:
    root = Path(args.root)
    found = OutputDir.find(root)
    if not found:
        print(f"no mumax3 output directories under {root}")
        return 1
    nb = notebook_path(root)
    data = load(nb)
    known = {re.search(r"`([^`]+)`", e).group(1)
             for e in data[RUNS] if re.search(r"`([^`]+)`", e)}
    added = 0
    for out in found:
        if out.path.name in known:
            continue
        data[RUNS].append(summarise_run(out))
        added += 1
    save(nb, data, args.title or f"Simulation notebook — {root.resolve().name}")
    print(f"{len(found)} run(s) under {root}; {added} newly recorded")
    print(f"notebook: {nb}")
    return 0


def cmd_note(args) -> int:
    root = Path(args.root)
    nb = notebook_path(root)
    data = load(nb)
    section = OPEN if args.open else NOTES
    data[section].append(f"- [{stamp()}] {args.text}")
    save(nb, data, args.title or f"Simulation notebook — {root.resolve().name}")
    print(f"recorded under {section.lstrip('# ')}: {args.text}")
    return 0


def cmd_resolve(args) -> int:
    root = Path(args.root)
    nb = notebook_path(root)
    data = load(nb)
    hits = [i for i, e in enumerate(data[OPEN]) if args.text.lower() in e.lower()]
    if not hits:
        print(f"no open question matching {args.text!r}")
        return 1
    for i in reversed(hits):
        q = data[OPEN].pop(i)
        body = q.split("] ", 1)[-1]
        data[NOTES].append(f"- [{stamp()}] RESOLVED: {body}"
                           + (f" — {args.answer}" if args.answer else ""))
    save(nb, data, args.title or f"Simulation notebook — {root.resolve().name}")
    print(f"resolved {len(hits)} question(s)")
    return 0


def cmd_show(args) -> int:
    nb = notebook_path(Path(args.root))
    if not nb.is_file():
        print(f"no notebook yet at {nb}. Run `notebook.py scan {args.root}` first.")
        return 1
    print(nb.read_text(encoding="utf-8"))
    return 0


def cmd_open(args) -> int:
    nb = notebook_path(Path(args.root))
    data = load(nb)
    if not data[OPEN]:
        print("nothing open.")
        return 0
    print("Still unresolved:")
    for e in data[OPEN]:
        print(" ", e.lstrip("- "))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=".", help="folder holding the simulations")
    ap.add_argument("--title")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("scan", help="record every run found under root")
    s.set_defaults(fn=cmd_scan)

    s = sub.add_parser("note", help="record a conclusion")
    s.add_argument("text")
    s.add_argument("--open", action="store_true", help="file it as an open question")
    s.set_defaults(fn=cmd_note)

    s = sub.add_parser("resolve", help="close an open question")
    s.add_argument("text", help="substring of the question")
    s.add_argument("--answer")
    s.set_defaults(fn=cmd_resolve)

    s = sub.add_parser("show", help="print the notebook")
    s.set_defaults(fn=cmd_show)

    s = sub.add_parser("open", help="list unresolved questions")
    s.set_defaults(fn=cmd_open)

    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
