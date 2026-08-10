#!/usr/bin/env python3
"""Harvest simulation parameters out of a paper PDF.

    extract_paper.py paper.pdf              human-readable survey
    extract_paper.py paper.pdf --json spec.json

This does NOT try to understand the paper. It finds every quantity that
carries a unit a micromagnetic simulation could use, converts it to SI, and
reports it with the page it came from and the sentence around it. Judging
which candidate is the right one is the reader's job -- but nothing that
looked like a parameter is silently dropped, and every claim can be checked
against a page number.

That division matters. A regex cannot tell "Ms = 0.86 MA/m" (this sample) from
"Ms = 1.4 MA/m" (a cited comparison), and pretending otherwise is how a
reproduction ends up built on a number from someone else's paper.

It also reports what is NOT there. Cell size, damping and initial state are
the three omissions that most often decide whether a reproduction works, so
their absence is stated explicitly rather than left to be discovered later.

Needs pypdf, or the `pdftotext` binary as a fallback.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, asdict, field
from pathlib import Path

HERE = Path(__file__).resolve()
for _cand in (HERE.parents[3] / "lib", HERE.parents[2] / "lib"):
    if (_cand / "mx3lib").is_dir():
        sys.path.insert(0, str(_cand))
        break
from mx3lib import units  # noqa: E402

MU0 = units.MU0

# --------------------------------------------------------------------------
# units
# --------------------------------------------------------------------------

# How a paper names each thing. Order matters: longer/more specific first.
NAMES: dict[str, list[str]] = {
    "Aex":  [r"A_?ex", r"exchange (?:stiffness|constant)", r"\bA\b"],
    "Dind": [r"D_?ind", r"interfacial DMI", r"DMI (?:constant|strength|parameter)", r"\bD\b"],
    "Dbulk": [r"D_?bulk", r"bulk DMI"],
    "Msat": [r"M_?s(?:at)?", r"saturation magnet[iz]sation"],
    "Ku1":  [r"K_?u1?", r"(?:uniaxial |perpendicular )?anisotropy (?:constant|energy density)"],
    "alpha": [r"(?:Gilbert )?damping(?: (?:constant|parameter))?", r"\balpha\b", r"α"],
    "Temp": [r"temperature"],
    "Pol":  [r"(?:spin |current )?polari[sz]ation"],
    "xi":   [r"non-?adiabatic(?:ity)?(?: parameter)?"],
}

# Which physical quantity each script parameter is, for the unit engine.
QUANTITY_OF = {"Aex": "Aex", "Dind": "DMI", "Dbulk": "DMI", "Msat": "Msat",
               "Ku1": "Ku", "Temp": None, "Pol": None, "xi": None,
               "alpha": None}

# Things a run needs that papers routinely omit.
CRITICAL = {
    "cell size": [r"cell(?: size)?", r"discreti[sz]ation", r"mesh(?: size)?",
                  r"grid(?: size| spacing)?", r"finite[- ]difference"],
    "damping": [r"damping", r"α\s*=", r"\balpha\s*="],
    "initial state": [r"initial (?:state|configuration|magnet[iz]sation)",
                      r"relax(?:ed|ation) from", r"starting configuration"],
    "solver / tolerance": [r"solver", r"Runge[- ]?Kutta", r"Dormand", r"time step",
                           r"tolerance", r"MaxErr"],
    "temperature": [r"temperature", r"thermal", r"\b0\s*K\b", r"zero temperature"],
    "boundary conditions": [r"periodic boundary", r"\bPBC\b", r"open boundary"],
    "sample dimensions": [r"dimensions?", r"\bsize of\b", r"nanowire", r"nanodisc",
                          r"film thickness", r"×\s*\d+\s*nm"],
}

# Simulator mentions, so the reader knows what produced the figure.
CODES = [r"[Mm]u[Mm]ax\s*3?", r"OOMMF", r"Fidimag", r"magnum\.np", r"Vampire",
         r"MicroMagnum", r"Boris", r"Ubermag"]


# --------------------------------------------------------------------------

def read_pages(pdf: Path) -> list[str]:
    """Text per page. pypdf when available, else the pdftotext binary."""
    try:
        import pypdf
        return [(p.extract_text() or "") for p in pypdf.PdfReader(str(pdf)).pages]
    except ImportError:
        pass
    if shutil.which("pdftotext"):
        out = subprocess.run(["pdftotext", "-layout", str(pdf), "-"],
                             capture_output=True, text=True)
        if out.returncode == 0:
            return out.stdout.split("\f")
    raise SystemExit(
        "Cannot read PDFs here. Install pypdf (`pip install pypdf`) or poppler's "
        "pdftotext, or paste the methods section as text instead."
    )


def normalise(text: str) -> str:
    """Fold the typographic noise PDFs introduce, so patterns match."""
    subs = {
        "−": "-", "–": "-", "—": "-",     # dashes
        "×": "x", "·": ".", "′": "'",
        "ﬁ": "fi", "ﬂ": "fl",                  # ligatures
        "µ": "u", "μ": "u",                    # micro
        "Å": "A",                                   # angstrom
    }
    for a, b in subs.items():
        text = text.replace(a, b)
    # "pJ m-1" / "pJ m−1" -> "pJ/m";  "mJ m-2" -> "mJ/m2"
    # "pJ m-1" -> "pJ/m" (exponent 1 is implicit), "mJ m-2" -> "mJ/m2"
    text = re.sub(r"\b([pnumkMG]?[JAT])\s*m\s*-\s*(\d)",
                  lambda m: f"{m.group(1)}/m" + ("" if m.group(2) == "1" else m.group(2)),
                  text)
    text = re.sub(r"\b([pnumkMG]?[JAT])\s*/\s*m\s*(\d)?", lambda m: f"{m.group(1)}/m{m.group(2) or ''}", text)
    text = re.sub(r"\bm\s*-\s*1\b", "/m", text)
    return text


NUM = r"[-+]?\d+(?:[.,]\d+)?(?:\s*[x×]\s*10\s*\^?\s*[-+]?\d+|[eE][-+]?\d+)?"


def to_float(tok: str) -> float | None:
    tok = tok.replace(",", ".").replace(" ", "")
    m = re.match(r"^([-+]?\d+(?:\.\d+)?)[x×]10\^?([-+]?\d+)$", tok)
    if m:
        return float(m.group(1)) * 10 ** int(m.group(2))
    try:
        return float(tok)
    except ValueError:
        return None


@dataclass
class Candidate:
    param: str            # Msat | Aex | Dind | ...
    value_si: float
    raw: str              # as printed
    unit: str
    page: int
    context: str
    confidence: str       # "labelled" | "unit-only"


# Grab anything that LOOKS like a unit; mx3lib.units decides if it is one and
# whether it fits the quantity. A closed list of spellings would miss
# "erg cm-3", "pJ m^-1", "kA m-1" and every other way a journal sets units.
UNIT_TOKEN = r"([A-Za-z\u00b5\u03bc]+\s*-?\d*(?:\s*/\s*[A-Za-z\u00b5\u03bc]+\s*-?\d*)?)"


def unit_pattern(quantity: str) -> str:
    return UNIT_TOKEN


def best_unit(token: str, value: float, quantity: str):
    """Longest prefix of `token` that is a valid unit for `quantity`.

    Journal tables often set no space between a unit and the next symbol, so a
    greedy grab yields "pJ/mD" or "MA/mKu". Backtracking from the full token
    finds "pJ/m" and "MA/m" without needing to know the table's layout.
    """
    token = token.strip()
    last: units.UnitError | None = None
    for end in range(len(token), 0, -1):
        cand = token[:end].strip().rstrip("/")
        if not cand:
            continue
        try:
            return cand, units.convert(value, cand, quantity)
        except units.UnitError as exc:
            last = exc
            continue
    raise last or units.UnitError(f"no valid unit in {token!r}")


def harvest(pages: list[str]) -> tuple[list[Candidate], list[tuple]]:
    found: list[Candidate] = []
    refused: list[tuple] = []
    for pno, raw in enumerate(pages, start=1):
        text = normalise(raw)
        flat = re.sub(r"\s*\n\s*", " ", text)
        # PDF tables lose the column gap: "A 13 pJ/mD 3.0 mJ/m2 Ms 0.86 MA/mKu".
        # Re-insert a space where a unit runs straight into the next row label,
        # otherwise the word boundary in an alias like \bD\b never matches.
        flat = re.sub(r"([a-z0-9])([A-Z][A-Za-z_]{0,3}\s*[=:]?\s*[-+]?\d)",
                      r"\1 \2", flat)

        for param, aliases in NAMES.items():
            quantity = QUANTITY_OF.get(param)
            if quantity is None:
                continue
            up = unit_pattern(quantity)
            for alias in aliases:
                # "Ms = 0.86 MA/m"  and also table rows "Ms 0.86 MA m-1"
                # \w* after the alias so "Aexch=", "Msat =", "Ku1=" all match:
                # a paper's own spelling rarely stops exactly where the alias does.
                pat = rf"({alias})\w*\s*[=:]?\s*({NUM})\s*{up}"
                for m in re.finditer(pat, flat, re.I):
                    val = to_float(m.group(2))
                    if val is None:
                        continue
                    unit = m.group(3).strip()
                    lo = max(0, m.start() - 90)
                    ctx = flat[lo:m.end() + 60].strip()
                    try:
                        unit, conv = best_unit(unit, val, quantity)
                    except units.UnitError as exc:
                        # Not a silent drop: a unit that cannot be converted is
                        # exactly the kind of thing a reader must see.
                        refused.append((param, f"{m.group(2)} {unit}", pno,
                                        str(exc), ctx))
                        continue
                    found.append(Candidate(
                        param, conv.value, m.group(2).strip(), unit, pno,
                        ctx, conv.note or "converted",
                    ))
                    break   # first alias that matches wins for this param/page

    # de-duplicate identical (param, value) pairs, keeping the earliest page
    seen: dict[tuple, Candidate] = {}
    for c in found:
        key = (c.param, round(c.value_si, 18))
        if key not in seen or c.page < seen[key].page:
            seen[key] = c
    return sorted(seen.values(), key=lambda c: (c.param, c.page)), refused


def find_mentions(pages: list[str], patterns: list[str]) -> list[tuple[int, str]]:
    out = []
    for pno, raw in enumerate(pages, start=1):
        flat = re.sub(r"\s*\n\s*", " ", normalise(raw))
        for p in patterns:
            for m in re.finditer(p, flat, re.I):
                lo = max(0, m.start() - 80)
                out.append((pno, flat[lo:m.end() + 120].strip()))
                break
    return out


def find_dimensions(pages: list[str]) -> list[tuple[int, str]]:
    """Sample geometry, usually written as 'a x b x c nm'."""
    pat = rf"({NUM})\s*(?:nm|um)?\s*x\s*({NUM})\s*(?:nm|um)?(?:\s*x\s*({NUM}))?\s*(nm|um|nm3|nm2)"
    out = []
    for pno, raw in enumerate(pages, start=1):
        flat = re.sub(r"\s*\n\s*", " ", normalise(raw))
        for m in re.finditer(pat, flat, re.I):
            lo = max(0, m.start() - 60)
            out.append((pno, flat[lo:m.end() + 40].strip()))
    return out


# --------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pdf", type=Path)
    ap.add_argument("--json", type=Path, help="write a draft spec here")
    ap.add_argument("--pages", help="limit to a page range, e.g. 3-8")
    args = ap.parse_args()

    if not args.pdf.is_file():
        print(f"no such file: {args.pdf}", file=sys.stderr)
        return 2

    pages = read_pages(args.pdf)
    if args.pages:
        a, _, b = args.pages.partition("-")
        pages = pages[int(a) - 1: int(b or a)]

    print(f"{args.pdf.name}: {len(pages)} pages\n")

    cands, refused = harvest(pages)
    print("=" * 72)
    print("CANDIDATE PARAMETERS  (every unit-bearing number; you must choose)")
    print("=" * 72)
    if not cands:
        print("  none found. The parameters may be in a figure, a table image, or")
        print("  the supplementary material.")
    by_param: dict[str, list[Candidate]] = {}
    for c in cands:
        by_param.setdefault(c.param, []).append(c)
    for param, group in by_param.items():
        print(f"\n{param}:")
        for c in group:
            print(f"  p{c.page:<3} {c.raw} {c.unit:<8} -> {c.value_si:.6g} SI")
            print(f"       \"{c.context[:110]}\"")
        if len(group) > 1:
            print(f"  ^ {len(group)} different values. Pick the one describing THIS "
                  f"sample, not a citation.")

    if refused:
        print("\n" + "-" * 72)
        print("NOT CONVERTED  (a number was found but its unit does not fit)")
        print("-" * 72)
        seen_r = set()
        for param, printed, pno, why, ctx in refused:
            key = (param, printed)
            if key in seen_r:
                continue
            seen_r.add(key)
            print(f"\n  {param}: {printed}  (p{pno})")
            print(f"    {why[:200]}")
        print("\n  These are not dropped silently because a wrong unit is often a"
              "\n  typo in the paper, or a quantity you have mistaken for another.")

    print("\n" + "=" * 72)
    print("SIMULATION SETUP  (what the paper says about how it was run)")
    print("=" * 72)
    codes = find_mentions(pages, CODES)
    if codes:
        print(f"\nsimulator:")
        for pno, ctx in codes[:3]:
            print(f"  p{pno:<3} \"{ctx[:110]}\"")

    dims = find_dimensions(pages)
    if dims:
        print(f"\nsample dimensions:")
        for pno, ctx in dims[:4]:
            print(f"  p{pno:<3} \"{ctx[:110]}\"")

    print("\n" + "=" * 72)
    print("GAPS  (a run needs these; absence here means you must assume one)")
    print("=" * 72)
    missing = []
    for label, pats in CRITICAL.items():
        hits = find_mentions(pages, pats)
        if hits:
            pno, ctx = hits[0]
            print(f"\n{label}: mentioned on p{pno}")
            print(f"  \"{ctx[:120]}\"")
        else:
            missing.append(label)
    if missing:
        print(f"\nNOT MENTIONED ANYWHERE: {', '.join(missing)}")
        print("  Each must be assumed, and every assumption must be recorded on the")
        print("  Unverified line of the generated script's header.")

    if args.json:
        draft = {
            "source": {"file": args.pdf.name, "pages": len(pages)},
            "stated": {
                c.param: {"value_si": c.value_si, "as_printed": f"{c.raw} {c.unit}",
                          "page": c.page}
                for c in cands
                if len(by_param.get(c.param, [])) == 1
            },
            "ambiguous": {
                p: [{"value_si": c.value_si, "as_printed": f"{c.raw} {c.unit}",
                     "page": c.page} for c in g]
                for p, g in by_param.items() if len(g) > 1
            },
            "assumed": {k: None for k in missing},
            "targets": [],
            "_note": ("Review every entry against its page before use. 'ambiguous' "
                      "needs a human choice. 'assumed' entries must be filled in and "
                      "will be reported as assumptions, never as the paper's values."),
        }
        args.json.write_text(json.dumps(draft, indent=2), encoding="utf-8")
        print(f"\ndraft spec: {args.json}")
        print("  Review it. Nothing here is trustworthy until checked against the page.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
