"""Units, including the ones magnetism papers actually use.

mumax3 takes bare SI. Papers do not. A single methods section can mix SI,
Gaussian-cgs and hybrids -- "Ms = 1400 emu/cm3", "4*pi*Ms = 17.6 kG",
"Hk = 2.5 kOe", "A = 1.3 micro-erg/cm", "mu0*Ms = 1.76 T" -- and every one of
those has to become A/m, J/m or T before it reaches a script.

This does it by dimensional analysis rather than a lookup table, so a spelling
nobody anticipated ("pJ m^-1", "erg cm-3", "kA/m") still converts, and a unit
that is wrong for the quantity is caught instead of silently accepted.

Two things it refuses to guess, because guessing produces a plausible wrong
number rather than an error:

  * A magnetisation quoted in tesla or gauss. That is mu0*Ms or 4*pi*Ms, not
    Ms, and which one depends on the convention. Ask for the intended reading.
  * emu on its own, or per gram, or Bohr magnetons per formula unit. These are
    moments, not magnetisations; converting needs a volume or a density the
    paper may not give.

Reference values: 1 emu/cm3 = 1 kA/m, 1 Oe = 1000/(4*pi) A/m, mu0*(1 Oe) =
0.1 mT, 1 erg/cm3 = 0.1 J/m3, 1 erg/cm = 1e-5 J/m, 1 erg/cm2 = 1e-3 J/m2.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

MU0 = 4e-7 * math.pi          # T*m/A

# Dimensions as (length, mass, time, current) exponents.
Dim = tuple[int, int, int, int]

PREFIX = {
    "y": 1e-24, "z": 1e-21, "a": 1e-18, "f": 1e-15, "p": 1e-12, "n": 1e-9,
    "u": 1e-6, "µ": 1e-6, "μ": 1e-6, "m": 1e-3, "c": 1e-2, "d": 1e-1,
    "da": 1e1, "h": 1e2, "k": 1e3, "M": 1e6, "G": 1e9, "T": 1e12, "P": 1e15,
}

# base token -> (factor to SI, dimensions)
BASE: dict[str, tuple[float, Dim]] = {
    "m":   (1.0,   (1, 0, 0, 0)),
    "g":   (1e-3,  (0, 1, 0, 0)),
    "s":   (1.0,   (0, 0, 1, 0)),
    "A":   (1.0,   (0, 0, 0, 1)),
    "K":   (1.0,   (0, 0, 0, 0)),      # temperature, treated as scalar here
    "J":   (1.0,   (2, 1, -2, 0)),
    "erg": (1e-7,  (2, 1, -2, 0)),
    "N":   (1.0,   (1, 1, -2, 0)),
    "T":   (1.0,   (0, 1, -2, -1)),    # tesla
    "G":   (1e-4,  (0, 1, -2, -1)),    # gauss
    "Oe":  (1e3 / (4 * math.pi), (-1, 0, 0, 1)),   # oersted, as an H field
    "emu": (1e-3,  (2, 0, 0, 1)),      # magnetic moment: erg/G = 1e-3 A m^2
    "eV":  (1.602176634e-19, (2, 1, -2, 0)),
}

# Prefixes apply to every base unit: kOe, kG, keV and micro-erg all occur in
# the literature. (Nothing here collides: 'G' resolves to gauss as a whole
# token before the giga- prefix is ever tried, and no base unit begins with a
# prefix letter that would shadow another.)

# What a quantity must come out as.
QUANTITY_DIM: dict[str, Dim] = {
    "Msat":   (-1, 0, 0, 1),      # A/m
    "Aex":    (1, 1, -2, 0),      # J/m
    "DMI":    (0, 1, -2, 0),      # J/m^2
    "Ku":     (-1, 1, -2, 0),     # J/m^3
    "field":  (0, 1, -2, -1),     # T
    "Hfield": (-1, 0, 0, 1),      # A/m
    "length": (1, 0, 0, 0),
    "time":   (0, 0, 1, 0),
    "energy": (2, 1, -2, 0),
    "current_density": (-2, 0, 0, 1),
    "moment": (2, 0, 0, 1),       # A m^2
}

QUANTITY_SI = {
    "Msat": "A/m", "Aex": "J/m", "DMI": "J/m2", "Ku": "J/m3", "field": "T",
    "Hfield": "A/m", "length": "m", "time": "s", "energy": "J",
    "current_density": "A/m2", "moment": "A m2",
}


class UnitError(ValueError):
    """Raised when a unit cannot be converted without more information."""


@dataclass
class Converted:
    value: float          # in SI
    si_unit: str
    note: str = ""        # how it was interpreted, when that was not obvious


# ---------------------------------------------------------------------------
# parsing
# ---------------------------------------------------------------------------

def _normalise(u: str) -> str:
    u = u.strip()
    for a, b in (("·", " "), ("⋅", " "), ("×", " "),
                 ("−", "-"), ("–", "-"), ("^", ""), ("**", "")):
        u = u.replace(a, b)
    # superscript digits and minus
    sup = {"⁰": "0", "¹": "1", "²": "2", "³": "3",
           "⁴": "4", "⁵": "5", "⁶": "6", "⁷": "7",
           "⁸": "8", "⁹": "9", "⁻": "-"}
    u = "".join(sup.get(c, c) for c in u)
    u = re.sub(r"\s*/\s*", "/", u)
    u = re.sub(r"\s+", " ", u)
    return u


def _split_token(tok: str) -> tuple[str, int]:
    """'cm3' -> ('cm', 3); 'm-2' -> ('m', -2); 'nm' -> ('nm', 1)."""
    m = re.match(r"^([A-Za-zµμ]+)\s*(-?\d+)?$", tok)
    if not m:
        raise UnitError(f"cannot parse unit token {tok!r}")
    return m.group(1), int(m.group(2) or 1)


def _resolve(sym: str) -> tuple[float, Dim]:
    """A symbol, possibly prefixed, to (factor, dims)."""
    if sym in BASE:
        return BASE[sym]
    for p, mult in sorted(PREFIX.items(), key=lambda kv: -len(kv[0])):
        if sym.startswith(p) and len(sym) > len(p):
            rest = sym[len(p):]
            if rest in BASE:
                f, d = BASE[rest]
                return f * mult, d
    raise UnitError(f"unknown unit {sym!r}")


def parse_unit(unit: str) -> tuple[float, Dim]:
    """Any unit string to (factor to SI, dimensions).

        parse_unit("emu/cm3")  -> (1000.0, (-1,0,0,1))
        parse_unit("pJ/m")     -> (1e-12,  (1,1,-2,0))
        parse_unit("erg cm-3") -> (0.1,    (-1,1,-2,0))
    """
    u = _normalise(unit)
    if not u:
        raise UnitError("empty unit")

    numer, _, denom = u.partition("/")
    factor = 1.0
    dims = [0, 0, 0, 0]

    for part, sign in ((numer, 1), (denom, -1)):
        for tok in part.split():
            if not tok:
                continue
            sym, exp = _split_token(tok)
            f, d = _resolve(sym)
            exp *= sign
            factor *= f ** exp
            for i in range(4):
                dims[i] += d[i] * exp

    return factor, tuple(dims)  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# conversion, with the magnetism-specific ambiguities handled explicitly
# ---------------------------------------------------------------------------

def convert(value: float, unit: str, quantity: str,
            reading: str | None = None) -> Converted:
    """Convert `value unit` into the SI unit mumax3 wants for `quantity`.

    `reading` resolves an ambiguity the unit alone cannot:
        "mu0Ms"  - the number is mu0*Ms in tesla       -> Ms = value/mu0
        "4piMs"  - the number is 4*pi*Ms in gauss      -> Ms = value/(4*pi) kA/m
        "B"      - a field written in Oe/G means mu0*H -> tesla
        "H"      - a field written in Oe/G means H     -> A/m
    """
    if quantity not in QUANTITY_DIM:
        raise UnitError(f"unknown quantity {quantity!r}; "
                        f"known: {', '.join(sorted(QUANTITY_DIM))}")

    factor, dims = parse_unit(unit)
    want = QUANTITY_DIM[quantity]
    si = QUANTITY_SI[quantity]

    if dims == want:
        return Converted(value * factor, si)

    # --- magnetisation quoted as a flux density -------------------------
    if quantity == "Msat" and dims == QUANTITY_DIM["field"]:
        tesla = value * factor
        if reading == "mu0Ms":
            return Converted(tesla / MU0, si,
                             f"read as mu0*Ms = {tesla:g} T -> Ms = {tesla/MU0:.4g} A/m")
        if reading == "4piMs":
            # Gaussian: 4*pi*Ms in gauss; Ms[emu/cm3] = value_G/(4*pi)
            emu = (tesla / 1e-4) / (4 * math.pi)
            return Converted(emu * 1e3, si,
                             f"read as 4*pi*Ms = {tesla/1e-4:g} G -> "
                             f"Ms = {emu:.4g} emu/cm3 = {emu*1e3:.4g} A/m")
        raise UnitError(
            f"a magnetisation given in {unit} is ambiguous: it is either "
            f"mu0*Ms (SI, tesla) or 4*pi*Ms (Gaussian, gauss). "
            f"mu0*Ms reading -> {tesla/MU0:.4g} A/m; "
            f"4*pi*Ms reading -> {(tesla/1e-4)/(4*math.pi)*1e3:.4g} A/m. "
            f"Pass reading='mu0Ms' or reading='4piMs' once you know which the "
            f"paper means."
        )

    # --- field quoted as H (Oe, A/m) when tesla was wanted, or vice versa --
    if quantity == "field" and dims == QUANTITY_DIM["Hfield"]:
        h = value * factor              # A/m
        return Converted(h * MU0, "T",
                         f"H = {h:.4g} A/m converted as mu0*H = {h*MU0:.4g} T")
    if quantity == "Hfield" and dims == QUANTITY_DIM["field"]:
        b = value * factor              # T
        return Converted(b / MU0, "A/m",
                         f"B = {b:.4g} T converted as H = B/mu0 = {b/MU0:.4g} A/m")

    # --- moments that need a volume or density --------------------------
    if quantity == "Msat" and dims == QUANTITY_DIM["moment"]:
        raise UnitError(
            f"{unit} is a magnetic moment, not a magnetisation. Divide by the "
            f"sample volume to get A/m -- the paper must state the volume, or "
            f"the film thickness and area."
        )
    if quantity == "Msat" and dims == (0, -1, 0, 1):    # A m^2 / kg  (emu/g)
        raise UnitError(
            f"{unit} is a mass magnetisation. Multiply by the mass density to "
            f"reach A/m; the paper must give the density."
        )

    raise UnitError(
        f"{unit} has the wrong dimensions for {quantity} "
        f"(got {dims}, need {want} = {si}). Either the unit was misread or the "
        f"paper is quoting a different quantity."
    )


def describe(unit: str) -> str:
    """One line saying what a unit is, for reporting."""
    try:
        factor, dims = parse_unit(unit)
    except UnitError as exc:
        return str(exc)
    for q, d in QUANTITY_DIM.items():
        if d == dims:
            return f"{unit} = {factor:g} {QUANTITY_SI[q]}  ({q})"
    return f"{unit} = {factor:g} SI, dimensions {dims} (no mumax3 quantity)"


# Quick self-check of the conversions people get wrong. Run this file directly.
_CASES = [
    (1.0, "emu/cm3", "Msat", 1e3),
    (1400, "emu/cm3", "Msat", 1.4e6),
    (800, "kA/m", "Msat", 8e5),
    (13, "pJ/m", "Aex", 13e-12),
    (1.3e-6, "erg/cm", "Aex", 1.3e-11),
    (3.0, "mJ/m2", "DMI", 3e-3),
    (3.0, "erg/cm2", "DMI", 3e-3),
    (0.4, "MJ/m3", "Ku", 4e5),
    (4e6, "erg/cm3", "Ku", 4e5),
    (1.0, "mT", "field", 1e-3),
    (100, "Oe", "field", 1e-2),
    (1.0, "kOe", "field", 0.1),
    (1e12, "A/m2", "current_density", 1e12),
    (1, "MA/cm2", "current_density", 1e10),
]

if __name__ == "__main__":
    bad = 0
    for val, unit, q, want in _CASES:
        got = convert(val, unit, q).value
        ok = math.isclose(got, want, rel_tol=1e-9)
        bad += not ok
        print(f"{'ok ' if ok else 'BAD'} {val:>8g} {unit:<10} as {q:<16} "
              f"-> {got:.6g} {QUANTITY_SI[q]}" + ("" if ok else f"   want {want:g}"))
    for val, unit, q, reading in ((1.76, "T", "Msat", "mu0Ms"),
                                  (17.6, "kG", "Msat", "4piMs")):
        c = convert(val, unit, q, reading=reading)
        print(f"ok  {val:>8g} {unit:<10} as {q:<16} -> {c.value:.6g} A/m  ({c.note})")
    try:
        convert(1.76, "T", "Msat")
    except UnitError as exc:
        print(f"ok  ambiguity refused: {str(exc)[:70]}...")
        bad += 0
    else:
        print("BAD ambiguous magnetisation was silently converted")
        bad += 1
    raise SystemExit(1 if bad else 0)
