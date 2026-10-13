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
    status: str                  # ok | failed | timeout | environment | skipped
    duration_s: float
    outdir: Path | None = None
    error: str = ""              # the engine's own last words
    log_tail: list = field(default_factory=list)
    warnings: list = field(default_factory=list)

    @property
    def output(self) -> OutputDir | None:
        if self.outdir and self.outdir.is_dir():
            try:
                return OutputDir(self.outdir)
            except NotADirectoryError:
                return None
        return None

    def summary(self) -> str:
        warn = "".join(f"\n          WARNING: {w}" for w in self.warnings)
        if self.status == "ok":
            return f"OK        {self.script.name}  ({self.duration_s:.1f}s){warn}"
        if self.status == "timeout":
            return f"TIMEOUT   {self.script.name}  (killed at {self.duration_s:.0f}s, with everything it started){warn}"
        if self.status == "skipped":
            return f"NOT RUN   {self.script.name}  ({self.error}){warn}"
        if self.status == "environment":
            return f"ENV       {self.script.name}  {self.error}{warn}"
        return f"FAILED    {self.script.name}  {self.error}{warn}"


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


# ---------------------------------------------------------------------------
# a sanity check on units, before anything runs
# ---------------------------------------------------------------------------

_NUM_ASSIGN = re.compile(r"^\s*([A-Za-z_]\w*)\s*:?=\s*([-+0-9.eE*/() \t]+?)\s*(//.*)?$")
_BEXT = re.compile(r"\bB_ext\s*=\s*vector\s*\((.*)\)", re.IGNORECASE)
_SAFE = re.compile(r"^[-+0-9.eE*/() \t]+$")
FIELD_LIMIT_T = 5.0


def _eval(expr: str, symbols: dict):
    """Evaluate a numeric expression made of numbers, known names and + - * / ( )."""
    expr = expr.strip()
    for name in sorted(symbols, key=len, reverse=True):
        expr = re.sub(rf"\b{re.escape(name)}\b", f"({symbols[name]!r})", expr, flags=re.IGNORECASE)
    if not expr or not _SAFE.match(expr):
        return None
    try:
        return float(eval(expr, {"__builtins__": {}}, {}))
    except Exception:
        return None


def field_warnings(script: str | Path) -> list[str]:
    """Applied-field components above FIELD_LIMIT_T. mumax3 takes fields in tesla; a component of 50 or 300 is
    almost always a value in mT typed where tesla were expected (50 mT is 0.05). Only constant fields are checked:
    an expression the checker cannot evaluate is skipped, never flagged."""
    try:
        text = Path(script).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    symbols, out = {}, []
    for n, line in enumerate(text.splitlines(), start=1):
        code = line.split("//", 1)[0]
        m = _NUM_ASSIGN.match(code)
        if m and m.group(1).lower() not in ("for", "if"):
            v = _eval(m.group(2), symbols)
            if v is not None:
                symbols[m.group(1)] = v
        b = _BEXT.search(code)
        if not b:
            continue
        depth, parts, cur = 0, [], ""
        for ch in b.group(1):
            if ch == "," and depth == 0:
                parts.append(cur); cur = ""
                continue
            depth += ch == "("
            depth -= ch == ")"
            cur += ch
        parts.append(cur)
        vals = [_eval(x, symbols) for x in parts[:3]]
        big = [v for v in vals if v is not None and abs(v) > FIELD_LIMIT_T]
        if big:
            out.append(f"line {n}: B_ext component {big[0]:g} T exceeds {FIELD_LIMIT_T:g} T. mumax3 fields are in "
                       f"tesla (50 mT = 0.05); check for a value in mT.")
    return out


# ---------------------------------------------------------------------------
# running, without leaving anything behind
# ---------------------------------------------------------------------------

def _win_descendants(root: int) -> list:
    """Every process below `root` (deepest last), from a Toolhelp snapshot: works without WMI or taskkill, which an
    SSH or service logon may not be allowed to use."""
    import ctypes
    from ctypes import wintypes

    class Entry(ctypes.Structure):
        _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD), ("th32ProcessID", wintypes.DWORD),
                    ("th32DefaultHeapID", ctypes.c_size_t), ("th32ModuleID", wintypes.DWORD),
                    ("cntThreads", wintypes.DWORD), ("th32ParentProcessID", wintypes.DWORD),
                    ("pcPriClassBase", ctypes.c_long), ("dwFlags", wintypes.DWORD), ("szExeFile", ctypes.c_wchar * 260)]

    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    k32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    k32.Process32FirstW.argtypes = k32.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(Entry)]
    k32.CloseHandle.argtypes = [wintypes.HANDLE]
    snap = k32.CreateToolhelp32Snapshot(0x2, 0)                  # TH32CS_SNAPPROCESS
    if not snap or snap == wintypes.HANDLE(-1).value:
        return []
    children = {}
    e = Entry()
    e.dwSize = ctypes.sizeof(Entry)
    ok = k32.Process32FirstW(snap, ctypes.byref(e))
    while ok:
        children.setdefault(e.th32ParentProcessID, []).append(e.th32ProcessID)
        ok = k32.Process32NextW(snap, ctypes.byref(e))
    k32.CloseHandle(snap)
    out, todo = [], [root]
    while todo:
        for c in children.get(todo.pop(), []):
            if c not in out and c != root:
                out.append(c)
                todo.append(c)
    return out


def _win_terminate(pid: int) -> None:
    import ctypes
    from ctypes import wintypes
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.OpenProcess.restype = wintypes.HANDLE
    k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    k32.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
    k32.CloseHandle.argtypes = [wintypes.HANDLE]
    h = k32.OpenProcess(0x0001, False, pid)                       # PROCESS_TERMINATE
    if h:
        k32.TerminateProcess(h, 1)
        k32.CloseHandle(h)


def _kill_tree(proc: subprocess.Popen) -> None:
    """End a process and everything it started. mumax3 given several inputs starts a child per input, and on
    Windows killing the parent alone leaves those children running on the GPU."""
    if proc.poll() is not None:
        return
    if os.name == "nt":
        try:
            below = _win_descendants(proc.pid)
            _win_terminate(proc.pid)                              # the parent first, so it starts nothing new
            for pid in reversed(below):
                _win_terminate(pid)
        except (OSError, AttributeError, ValueError):
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True)
    else:
        import signal
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError, OSError):
            pass
    try:
        proc.kill()
    except OSError:
        pass


def _execute(cmd: list, timeout: float | None) -> tuple[int, str, bool]:
    """Run cmd in its own process group; on timeout end the whole group. Returns (rc, output, timed_out)."""
    kw = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == "nt" else {"start_new_session": True}
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                            encoding="utf-8", errors="replace", **kw)
    try:
        out, _ = proc.communicate(timeout=timeout)
        return proc.returncode, out or "", False
    except subprocess.TimeoutExpired:
        _kill_tree(proc)
        try:
            out, _ = proc.communicate(timeout=30)
        except subprocess.TimeoutExpired:
            out = ""
        return -1, out or "", True


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

    timeout is in seconds; None waits forever. On timeout the engine and
    anything it started are ended. force overwrites an existing output
    directory, matching mumax3's -f.
    """
    script = Path(script)
    dest = Path(outdir) if outdir else default_outdir(script)
    warnings = field_warnings(script)

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
    try:
        rc, out, timed_out = _execute(cmd, timeout)
    except FileNotFoundError:
        return RunResult(script, False, "environment", 0.0, None,
                         f"{MUMAX!r} is not on PATH", warnings=warnings)
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
        warnings=warnings,
    )


def run_batch(scripts: list, jobs: int = 3, timeout: float | None = 3600,
              force: bool = True) -> list[RunResult]:
    """Run several inputs. timeout bounds the whole batch, not each script.

    With `-j` (mumax3-ultrafast) the inputs go through one `mumax3 -j N`
    invocation, which is where the batch speed-up lives. `-failfast` is
    deliberately NOT passed: in a sweep, one impossible parameter set must not
    discard the points that did work.

    Without `-j` (upstream mumax3) the inputs run one after another, each in
    its own process, so that every script gets its own status and duration and
    nothing outlives the batch: a script is not started once the time left
    cannot cover the slowest script so far, and a running one is ended, with
    everything it started, when the batch time is up. Scripts that were not
    run are reported as NOT RUN, so the caller can start them in a new call.
    """
    scripts = [Path(s) for s in scripts]
    if not scripts:
        return []

    if not supports_parallel_queue():
        results, started, slowest = [], time.time(), 0.0
        for s in scripts:
            left = None if timeout is None else timeout - (time.time() - started)
            if left is not None and (left <= 0 or left < slowest):
                results.append(RunResult(s, False, "skipped", 0.0, None,
                                         f"batch time {timeout:.0f} s would be exceeded; run it in another call",
                                         warnings=field_warnings(s)))
                continue
            r = run_one(s, timeout=left, force=force)
            slowest = max(slowest, r.duration_s)
            results.append(r)
            if r.status == "environment":
                for rest in scripts[len(results):]:
                    results.append(RunResult(rest, False, "environment", 0.0, None, r.error))
                break
        return results

    cmd = [MUMAX, "-http", "", "-j", str(jobs)]
    if force:
        cmd.append("-f")
    cmd += [str(s) for s in scripts]

    started = time.time()
    try:
        rc, out, timed_out = _execute(cmd, timeout)
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
        status = "ok" if ok else ("timeout" if timed_out else "failed")
        results.append(RunResult(
            script=s,
            ok=(status == "ok"),
            status=status,
            duration_s=elapsed,
            outdir=dest if dest.is_dir() else None,
            error="" if status == "ok" else _script_error(out, s),
            log_tail=[],
            warnings=field_warnings(s),
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
