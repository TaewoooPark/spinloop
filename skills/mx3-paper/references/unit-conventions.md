# Units, as papers actually write them

mumax3 takes bare SI. Magnetism papers do not: SI, Gaussian-cgs and hybrids
appear side by side, sometimes in one sentence. Conversion is handled by
`lib/mx3lib/units.py` through dimensional analysis, so an unanticipated
spelling still converts and a unit that is wrong for the quantity is refused
rather than silently accepted.

```bash
mx3 convert 1400 emu/cm3 Msat     ->  1.4e+06 A/m
mx3 convert 1.3e-6 erg/cm Aex     ->  1.3e-11 J/m
mx3 convert 2.5 kOe field         ->  0.25 T
mx3 convert 4e6 erg/cm3 Ku        ->  4e+05 J/m3
```

## The conversions

| Quantity | Paper writes | mumax3 wants | Factor |
|---|---|---|---|
| Ms | emu/cm³ (= emu/cc) | A/m | ×10³ |
| Ms | kA/m, MA/m | A/m | ×10³, ×10⁶ |
| A | pJ/m | J/m | ×10⁻¹² |
| A | erg/cm, µerg/cm | J/m | ×10⁻⁵ |
| D | mJ/m² | J/m² | ×10⁻³ |
| D | erg/cm² | J/m² | ×10⁻³ |
| Ku | MJ/m³, kJ/m³ | J/m³ | ×10⁶, ×10³ |
| Ku | erg/cm³ | J/m³ | ×10⁻¹ |
| B | mT, kOe, G | T | ×10⁻³, ×10⁻¹, ×10⁻⁴ |
| H | Oe | A/m | ×10³/4π = 79.577 |
| J | MA/cm² | A/m² | ×10¹⁰ |

Prefixes work on every unit, so `kOe`, `µerg/cm` and `kA/m` need no special
case. So do exponent spellings: `pJ m^-1`, `erg cm-3`, `mJ m⁻²`.

## The two that must not be guessed

**A magnetisation quoted in tesla or gauss.** That number is not Ms.

- SI convention: the paper means **µ₀Ms**, so `Ms = value / µ₀`.
  1.76 T → 1.401×10⁶ A/m.
- Gaussian convention: the paper means **4πMs** in gauss, so
  `Ms[emu/cm³] = value_G / 4π`. 17.6 kG → 1401 emu/cm³ → 1.401×10⁶ A/m.

The two differ in general. `mx3 convert` refuses the bare case and prints both
readings; pass `--reading mu0Ms` or `--reading 4piMs` once the paper's
convention is clear. A phrase like "4πMs = 17.6 kG" or an SI-throughout methods
section usually settles it.

**A moment rather than a magnetisation.** `emu`, `emu/g`, `µB per formula unit`
and `J/T` are moments. Reaching A/m needs a volume, a density or a unit-cell
volume that the paper may not give. These are refused with an explanation
instead of converted on a guess.

## Traps seen in real papers

- **`J/T` written for Ms.** J/T is a moment (A·m²); a magnetisation needs
  J/(T·m³). Seen in arXiv:2404.17388, where `M_S = 1.77×10⁶ J/T` is
  dimensionally a moment but numerically an A/m value for EuO. The extractor
  refuses it and shows the sentence, which is the right outcome: the reader
  decides, not a regex.
- **Ku quoted as Keff.** If the paper already subtracted shape anisotropy,
  feeding it to `Ku1` while `EnableDemag = true` subtracts it twice. See
  `simulator-conventions.md`.
- **Kc for cubic anisotropy.** `Kc1` in mumax3, not `Ku1`; a negative value is
  normal and meaningful.
- **Run-together PDF tables.** `A 13 pJ/mD 3.0 mJ/m2` has no space between the
  unit and the next row label. The extractor re-inserts it and backtracks to
  the longest valid unit, so `pJ/mD` resolves to `pJ/m`.

## Checking a conversion

Convert, then sanity-check against a closed form:

```bash
mx3 convert 1400 emu/cm3 Msat        # -> 1.4e6 A/m
mx3 physics --Ms 1.4e6 --A 30e-12    # exchange length 4.9 nm
```

If the exchange length comes out at nanometres, the magnitudes are right. If it
comes out at microns or picometres, a conversion is off by orders of magnitude.
