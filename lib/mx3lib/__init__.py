"""mx3lib - shared reading and analysis for the spinloop plugin skills.

Every skill that touches a result goes through here, so that "what is the
coercive field" means the same thing in mx3-run, mx3-tune and mx3-match.

    from mx3lib import OutputDir, physics, observe

    out = OutputDir("sim.out")
    loop = observe.hysteresis(out.table.column("B_extx"), out.table.column("mx"))
    print(loop.coercivity, loop.note)

Standard library only. mumax3-convert does the .ovf work; numpy is used only
if the caller asks for arrays.
"""

from .outdir import OutputDir, Provenance
from .table import Table
from . import observe, physics, run

__all__ = ["OutputDir", "Provenance", "Table", "observe", "physics", "run"]
__version__ = "0.1.0"
