"""Running mumax3.

Three things this does that `mumax3 file.mx3` does not:

1. Keeps the version banner on, so the output directory can later say which
   build produced it. Provenance you have to remember to enable is provenance
   you will not have.
2. Bounds the run. An unattended sweep must not hang on one bad parameter set.
3. Separates "the script is wrong" from "this machine cannot run it", so a
   caller looping on a failure does not loop forever against a missing GPU.

Batching goes through `-j`, which queues N inputs per GPU. On the measured M4
that is 2.53x aggregate for three minimize jobs -- the single largest easy win
for parameter sweeps, and invisible if you only look at one script.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

from .outdir import OutputDir

def _resolve_mumax() -> str:
    """Which mumax3 to use.

    Order matters. The plugin-installed engine outranks whatever is on PATH
    because it is a known, verified, current release, whereas a PATH entry is
    often an older build left over from a source checkout -- and an older build
    silently lacks `-j` and the tuning knobs. MUMAX3_BIN overrides everything,
    for anyone who means a specific binary.
    """
    explicit = os.environ.get("MUMAX3_BIN")
    if explicit:
        return explicit

    data = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    managed = Path(data) / "spinloop" / "bin" / "mumax3"
    if managed.is_file() and os.access(managed, os.X_OK):
        return str(managed)

    return "mumax3"


MUMAX = _resolve_mumax()

# Where the installer lives, so callers can tell the user how to fix a missing
# engine instead of only reporting that it is missing.
INSTALLER = Path(__file__).resolve().parents[2] / "scripts" / "install_engine.sh"

# Signatures of an environment failure rather than a bad script.
_ENV_PATTERNS = re.compile(
    r"Metal backend requires|failed to (init|create)|no such device|"
    r"cannot initialize|no CUDA|GPU not found",
    re.IGNORECASE,
)


@dataclass
class RunResult:
    script: Path
    ok: bool
    status: str                  # ok | failed | timeout | environment
    duration_s: float
    outdir: Path | None = None
    error: str = ""              # the engine's own last words
    log_tail: list = field(default_factory=list)

    @property
    def output(self) -> OutputDir | None:
        if self.outdir and self.outdir.is_dir():
            try:
                return OutputDir(self.outdir)
            except NotADirectoryError:
                return None
        return None

    def summary(self) -> str:
        if self.status == "ok":
            return f"OK        {self.script.name}  ({self.duration_s:.1f}s)"
        if self.status == "timeout":
            return f"TIMEOUT   {self.script.name}  (killed at {self.duration_s:.0f}s)"
        if self.status == "environment":
            return f"ENV       {self.script.name}  {self.error}"
        return f"FAILED    {self.script.name}  {self.error}"


def available() -> tuple[bool, str]:
    """Is mumax3 usable here? Returns (ok, explanation)."""
    if not (shutil.which(MUMAX) or (Path(MUMAX).is_file() and os.access(MUMAX, os.X_OK))):
        return False, (
            f"no mumax3 engine found. Install it with:\n"
            f"    {INSTALLER}\n"
            f"It downloads a verified 4 MB release - no compiler needed."
        )
    r = subprocess.run([MUMAX, "-test", "-v=false"], capture_output=True, text=True)
    if r.returncode != 0:
        return False, "mumax3 is installed but its GPU backend will not initialise"
    return True, "ready"


def default_outdir(script: Path) -> Path:
    """mumax3's own convention: foo.mx3 -> foo.out/"""
    return script.with_suffix(".out")


_supports_j: bool | None = None


def supports_parallel_queue() -> bool:
    """Does this build have `-j`?

    The flag arrived with the 2026-08 batching work. Older builds still run a
    list of inputs, just one at a time, so the caller can fall back rather than
    fail -- but it must know, or a batch silently produces nothing.
    """
    global _supports_j
    if _supports_j is None:
        r = subprocess.run([MUMAX, "-j", "1", "-vet", os.devnull],
                           capture_output=True, text=True)
        _supports_j = "not defined" not in (r.stderr + r.stdout)
    return _supports_j


def _classify(out: str, rc: int, timed_out: bool) -> tuple[str, str]:
    if timed_out:
        return "timeout", ""
    if rc == 0:
        return "ok", ""
    if _ENV_PATTERNS.search(out):
        first = next((l for l in out.splitlines() if _ENV_PATTERNS.search(l)), "")
        return "environment", first.strip()
    # The engine echoes statements as it runs; its complaint is the last thing
    # left once the echo and the Go stack are removed.
    lines = [
        l for l in out.splitlines()
        if l.strip()
        and not l.startswith("//")
        and not re.match(r"^(goroutine|created by|\[signal|exit status)", l)
        and not re.match(r"^(\s+|github\.com/|reflect\.|main\.|runtime\.|os\.|sync\.)", l)
    ]
    return "failed", (lines[-1].strip() if lines else f"exit status {rc}")


def run_one(script: str | Path, outdir: str | Path | None = None,
            timeout: float | None = 1800, force: bool = True,
            extra: list | None = None) -> RunResult:
    """Run one .mx3 and return where the results landed.

    timeout is in seconds; None waits forever. force overwrites an existing
    output directory, matching mumax3's -f.
    """
    script = Path(script)
    dest = Path(outdir) if outdir else default_outdir(script)

    cmd = [MUMAX, "-http", ""]          # no web GUI: this is not interactive
    if force:
        cmd.append("-f")
    cmd += ["-o", str(dest)]
    if extra:
        cmd += extra
    cmd.append(str(script))
    # note: -v is left at its default (true) on purpose, so the banner with the
    # build and commit hash is written into log.txt.

    started = time.time()
    timed_out = False
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        rc, out = proc.returncode, (proc.stdout or "") + (proc.stderr or "")
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        rc = -1
        out = ((exc.stdout or b"").decode(errors="replace")
               if isinstance(exc.stdout, bytes) else (exc.stdout or ""))
    except FileNotFoundError:
        return RunResult(script, False, "environment", 0.0, None,
                         f"{MUMAX!r} is not on PATH")
    duration = time.time() - started

    status, error = _classify(out, rc, timed_out)
    tail = [l for l in out.splitlines() if l.strip()][-15:]
    return RunResult(
        script=script,
        ok=(status == "ok"),
        status=status,
        duration_s=duration,
        outdir=dest if dest.is_dir() else None,
        error=error,
        log_tail=tail,
    )


def run_batch(scripts: list, jobs: int = 3, timeout: float | None = 3600,
              force: bool = True) -> list[RunResult]:
    """Run several inputs through one `mumax3 -j N` invocation.

    Queueing N per GPU is where the fork's batch speed-up lives. `-failfast` is
    deliberately NOT passed: in a sweep, one impossible parameter set must not
    discard the points that did work.

    Because the batch shares one process, a per-script duration is not
    available; each result carries the batch wall time divided by nothing --
    it is reported on the batch, not the point.
    """
    scripts = [Path(s) for s in scripts]
    if not scripts:
        return []

    cmd = [MUMAX, "-http", ""]
    if supports_parallel_queue():
        cmd += ["-j", str(jobs)]
    # Older builds have no -j but still accept a list of inputs and work
    # through them one at a time, so the batch still completes -- just without
    # the concurrency win. Callers can check supports_parallel_queue() if they
    # want to say so.
    if force:
        cmd.append("-f")
    cmd += [str(s) for s in scripts]

    started = time.time()
    timed_out = False
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        rc, out = proc.returncode, (proc.stdout or "") + (proc.stderr or "")
    except subprocess.TimeoutExpired as exc:
        timed_out, rc = True, -1
        out = ((exc.stdout or b"").decode(errors="replace")
               if isinstance(exc.stdout, bytes) else (exc.stdout or ""))
    except FileNotFoundError:
        return [RunResult(s, False, "environment", 0.0, None,
                          f"{MUMAX!r} is not on PATH") for s in scripts]
    elapsed = time.time() - started

    if _ENV_PATTERNS.search(out):
        first = next((l for l in out.splitlines() if _ENV_PATTERNS.search(l)), "")
        return [RunResult(s, False, "environment", elapsed, None, first.strip())
                for s in scripts]

    # Judge each script by whether its own output directory came out intact.
    results = []
    for s in scripts:
        dest = default_outdir(s)
        ok = dest.is_dir() and (dest / "log.txt").is_file()
        if ok and timed_out:
            status = "ok"
        elif timed_out:
            status = "timeout"
        elif ok:
            status = "ok"
        else:
            status = "failed"
        results.append(RunResult(
            script=s,
            ok=(status == "ok"),
            status=status,
            duration_s=elapsed,
            outdir=dest if dest.is_dir() else None,
            error="" if status == "ok" else _script_error(out, s),
            log_tail=[],
        ))
    if rc != 0 and all(r.ok for r in results):
        # batch reported failure but every directory exists: surface it anyway
        for r in results:
            r.error = r.error or f"batch exited {rc}"
    return results


def _script_error(batch_output: str, script: Path) -> str:
    """Pull the complaint belonging to one script out of a batch log."""
    name = script.name
    lines = batch_output.splitlines()
    for i, l in enumerate(lines):
        if name in l:
            for follow in lines[i:i + 6]:
                if re.search(r"error|panic|failed|invalid|undefined", follow, re.I):
                    return follow.strip()
    return "no output directory produced"


# ---------------------------------------------------------------------------
# time estimates, from the fork's measured performance curve
# ---------------------------------------------------------------------------

# Measured on an M4 MacBook Air: throughput per cell peaks near 256^2, and at
# and below 128^2 a fixed 172-187 us per evaluation dominates, where a wider
# GPU cannot help. These are used only to warn before a long wait, never to
# decide anything.
_FIXED_OVERHEAD_S = 180e-6


def estimate_runtime(cells: int, steps: int) -> float:
    """Very rough wall-clock estimate, in seconds.

    Deliberately crude: it exists to say "this is minutes, not hours" before
    someone walks away, not to predict. Below 128^2 the fixed per-evaluation
    cost dominates and the cell count barely matters.
    """
    per_eval = max(_FIXED_OVERHEAD_S, cells * 1.2e-9)
    return per_eval * steps


def sizing_advice(nx: int, ny: int, nz: int = 1) -> str:
    """What the measured curve implies for a mesh this size."""
    cells = nx * ny * nz
    inplane = nx * ny
    if inplane < 128 * 128:
        return (
            f"{nx}x{ny} is in the latency-bound regime: a fixed ~180 us per "
            f"evaluation dominates, so a faster GPU or a bigger mesh will not "
            f"help. To get more done, run several parameter sets at once with "
            f"-j rather than making this one run bigger."
        )
    if inplane <= 256 * 256:
        return f"{nx}x{ny} is near the throughput peak (~256^2) for this backend."
    if cells > 80e6:
        return (
            f"{cells/1e6:.0f}M cells is close to the measured ceiling (83.9M "
            f"succeeded, 104.9M did not). Expect heavy memory pressure."
        )
    return f"{nx}x{ny} is above the throughput peak; cost grows with cell count."
