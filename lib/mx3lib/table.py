"""mumax3's table.txt.

The format is one header line and then tab-separated floats:

    # t (s)	mx ()	my ()	mz ()	B_extx (T)	...
    0	-0.41669297	0.023299504	0.2079666	0	...

Columns carry their unit in parentheses, and the names are whatever the script
asked for with TableAdd. Empty parentheses mean dimensionless.

Lookup is deliberately forgiving. A researcher asks for "mz"; the header may
say "mz ()". A goal-seeking loop asks for "ext_dwspeed"; the header says
"ext_dwspeed (m/s)". Neither should have to know.
"""

from __future__ import annotations

import math
from pathlib import Path


class Table:
    def __init__(self, names: list[str], units: list[str], rows: list[list[float]]):
        self.names = names
        self.units = units
        self.rows = rows

    # -- construction ------------------------------------------------------

    @classmethod
    def read(cls, path: str | Path) -> "Table":
        path = Path(path)
        names: list[str] = []
        units: list[str] = []
        rows: list[list[float]] = []

        with path.open(encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.rstrip("\n")
                if not line.strip():
                    continue
                if line.startswith("#"):
                    if names:  # only the first header line matters
                        continue
                    for field in line.lstrip("#").split("\t"):
                        field = field.strip()
                        if not field:
                            continue
                        if "(" in field and field.endswith(")"):
                            nm, _, un = field.rpartition("(")
                            names.append(nm.strip())
                            units.append(un.rstrip(")").strip())
                        else:
                            names.append(field)
                            units.append("")
                    continue
                vals = []
                for tok in line.split("\t"):
                    tok = tok.strip()
                    if not tok:
                        continue
                    try:
                        vals.append(float(tok))
                    except ValueError:
                        vals.append(math.nan)
                if vals:
                    rows.append(vals)

        return cls(names, units, rows)

    # -- access ------------------------------------------------------------

    def __len__(self) -> int:
        return len(self.rows)

    def _index(self, name: str) -> int:
        """Resolve a column name: exact, then case-insensitive, then prefix."""
        if name in self.names:
            return self.names.index(name)
        low = name.lower()
        lowered = [n.lower() for n in self.names]
        if low in lowered:
            return lowered.index(low)
        hits = [i for i, n in enumerate(lowered) if n.startswith(low)]
        if len(hits) == 1:
            return hits[0]
        if len(hits) > 1:
            raise KeyError(
                f"ambiguous column {name!r}: matches {[self.names[i] for i in hits]}"
            )
        raise KeyError(f"no column {name!r}; table has {self.names}")

    def has(self, name: str) -> bool:
        try:
            self._index(name)
            return True
        except KeyError:
            return False

    def column(self, name: str) -> list[float]:
        i = self._index(name)
        return [r[i] if i < len(r) else math.nan for r in self.rows]

    def unit(self, name: str) -> str:
        return self.units[self._index(name)]

    def last(self, name: str) -> float:
        col = self.column(name)
        if not col:
            raise ValueError(f"column {name!r} is empty")
        return col[-1]

    def as_dict(self) -> dict[str, list[float]]:
        return {n: self.column(n) for n in self.names}

    # -- health ------------------------------------------------------------

    def nan_columns(self) -> list[str]:
        """Columns containing a NaN or infinity.

        A NaN here is the usual signature of a diverged run: the solver blew up
        and every subsequent row is poisoned.
        """
        bad = []
        for n in self.names:
            col = self.column(n)
            if any(math.isnan(v) or math.isinf(v) for v in col):
                bad.append(n)
        return bad

    def first_bad_row(self) -> int | None:
        """Index of the first row holding a NaN/inf, or None. Tells you when a
        run went wrong, which is usually more useful than that it did."""
        for i, r in enumerate(self.rows):
            if any(math.isnan(v) or math.isinf(v) for v in r):
                return i
        return None

    def to_csv(self, path: str | Path) -> Path:
        path = Path(path)
        header = ",".join(
            f"{n} ({u})" if u else n for n, u in zip(self.names, self.units)
        )
        lines = [header]
        for r in self.rows:
            lines.append(",".join(repr(v) for v in r))
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return path
