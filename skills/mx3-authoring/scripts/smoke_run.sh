#!/usr/bin/env bash
# smoke_run.sh - catch runtime-only failures without paying for the real run.
#
# vet compiles, lint reads units. Neither can see a region index that was never
# defined, a shape that clips the geometry to nothing, or an OVF path that does
# not exist -- those only appear once the engine builds the world.
#
# This makes a shrunken copy of the script (coarse grid, negligible run time),
# runs it, and reports whether the engine got through world construction.
# The original is never modified and its output directory is never touched.
#
# Worth running when the script uses regions, shapes, LoadFile, or custom
# field terms. Not worth it for a plain uniform-film run that lint already
# cleared.
#
# Usage: smoke_run.sh FILE.mx3 [grid]      (default grid 16)
# Exit:  0 ran clean, 1 runtime failure, 2 environment problem, 3 inconclusive
#        (timed out - loop-heavy script; raise SMOKE_TIMEOUT or skip).
set -uo pipefail

# Resolve the engine: an explicit MUMAX3_BIN, then the plugin-installed
# release, then PATH. The plugin-installed one outranks PATH because a PATH
# entry is often an older source build that silently lacks -j and the knobs.
_managed="${XDG_DATA_HOME:-$HOME/.local/share}/spinloop/bin/mumax3"
if [ -n "${MUMAX3_BIN:-}" ]; then
  MUMAX="$MUMAX3_BIN"
elif [ -x "$_managed" ]; then
  MUMAX="$_managed"
else
  MUMAX="mumax3"
fi
SRC="${1:-}"
GRID="${2:-16}"

if [ -z "$SRC" ] || [ ! -f "$SRC" ]; then
  echo "usage: smoke_run.sh FILE.mx3 [grid]" >&2
  exit 2
fi
if ! command -v "$MUMAX" >/dev/null 2>&1; then
  echo "ENV: '$MUMAX' not on PATH" >&2
  exit 2
fi

work=$(mktemp -d "${TMPDIR:-/tmp}/mx3-smoke.XXXXXX")
trap 'rm -rf "$work"' EXIT
tiny="$work/smoke.mx3"

# Shrink the script. Done in Python, not awk: the awk on macOS is BWK awk,
# which supports neither \b nor \1 backreferences, so the substitutions fail
# silently and the "smoke" run quietly becomes the full simulation.
#
#   SetGridSize / SetMesh cell counts -> GRID (z kept, usually 1)
#   Run / Steps / RunWhile            -> negligible
#   AutoSave / AutoSnapshot / table   -> cadence 0 (disabled)
#   Expect / ExpectV / ExpectB        -> removed: reference values do not hold
#                                        on a shrunken grid, and a failed
#                                        assertion here would mean nothing
python3 - "$SRC" "$GRID" > "$tiny" <<'PY'
import re, sys

src, grid = sys.argv[1], sys.argv[2]
text = open(src, encoding="utf-8", errors="replace").read()
I = re.IGNORECASE


def head2(m):
    """Replace the first two arguments (cell counts) with the smoke grid."""
    name, args = m.group(1), m.group(2)
    parts, depth, cur = [], 0, ""
    for ch in args:
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append(cur)
            cur = ""
        else:
            cur += ch
    parts.append(cur)
    if len(parts) >= 2:
        parts[0], parts[1] = f" {grid}", f" {grid}"
    return f"{name}({','.join(parts)})"


text = re.sub(r"(SetGridSize|SetMesh)\s*\(([^()]*(?:\([^()]*\)[^()]*)*)\)",
              head2, text, flags=I)
text = re.sub(r"(?<![\w.])Run\s*\([^()]*\)", "Run(1e-13)", text, flags=I)
text = re.sub(r"(?<![\w.])Steps\s*\([^()]*\)", "Steps(1)", text, flags=I)
text = re.sub(r"(?<![\w.])RunWhile\s*\([^()]*(?:\([^()]*\)[^()]*)*\)",
              "Steps(1)", text, flags=I)
text = re.sub(r"(?<![\w.])(AutoSave|AutoSnapshot)\s*\(([^,()]*),[^()]*\)",
              lambda m: f"{m.group(1)}({m.group(2)}, 0)", text, flags=I)
text = re.sub(r"(?<![\w.])TableAutoSave\s*\([^()]*\)", "TableAutoSave(0)",
              text, flags=I)
text = re.sub(r"(?<![\w.])Expect[VB]?\s*\([^()]*(?:\([^()]*\)[^()]*)*\)",
              "", text, flags=I)

sys.stdout.write(text)
PY

# Bound each relaxer. This alone is not enough: a sweep script relaxes inside a
# loop, so a per-call guard multiplies by the iteration count.
{
  echo ""
  echo "// -- injected by smoke_run.sh --"
  echo "RelaxWallClockTime = 2"
  echo "MinimizeWallClockTime = 2"
} >> "$tiny"

# Hard overall bound. macOS ships no coreutils `timeout`, so supervise by hand
# with a watchdog. Polling `kill -0` in a loop does NOT work: a finished child
# stays a zombie until it is waited on, and `kill -0` succeeds on zombies, so
# the loop would never exit and every run would look like a timeout.
LIMIT="${SMOKE_TIMEOUT:-60}"
"$MUMAX" -v=false -http "" -o "$work/out" "$tiny" > "$work/log" 2>&1 &
pid=$!
( sleep "$LIMIT"; kill -9 "$pid" 2>/dev/null ) >/dev/null 2>&1 &
watchdog=$!

wait "$pid"
rc=$?
kill -9 "$watchdog" 2>/dev/null
wait "$watchdog" 2>/dev/null
out=$(cat "$work/log")

# 128+SIGKILL: the watchdog fired.
if [ "$rc" -eq 137 ]; then
  echo "INCONCLUSIVE  $SRC"
  echo "      still running after ${LIMIT}s at ${GRID}x${GRID}; killed."
  echo "      Nothing was proved either way. Expected for scripts that relax"
  echo "      inside a loop (parameter sweeps, hysteresis): shrinking the grid"
  echo "      does not reduce the iteration count."
  echo "      Raise the bound with SMOKE_TIMEOUT=300, or skip the smoke stage"
  echo "      for loop-heavy scripts and rely on vet + lint."
  exit 3
fi

if [ "$rc" -eq 0 ]; then
  echo "PASS  $SRC (smoke: ${GRID}x${GRID} grid)"
  exit 0
fi

if printf '%s' "$out" | grep -qiE 'Metal backend requires|failed to (init|create)|no such device'; then
  echo "ENV: GPU backend unavailable" >&2
  printf '%s\n' "$out" | head -10 >&2
  exit 2
fi

echo "FAIL  $SRC (smoke: ${GRID}x${GRID} grid)"
echo "      the script compiles but the engine could not run it:"

# mumax3 echoes each executed statement, then reports the failure, then may
# dump a Go stack. Since the echo always precedes the failure, the last
# surviving line after stripping logs and stack frames IS the error. Filtering
# the echo by prefix does not work: real messages start with engine function
# names too ("SetGeom: geometry completely empty").
diag=$(printf '%s\n' "$out" \
  | grep -vE '^//' \
  | grep -vE '^(goroutine|created by|\[signal|exit status)' \
  | grep -vE '^(\s+|github\.com/|reflect\.|main\.|runtime\.|os\.|sync\.)' \
  | grep -vE '^\s*$')

printf '%s\n' "$diag" | tail -3 | sed 's/^/      /'
echo
echo "NOTE: the grid was shrunk to ${GRID}x${GRID}; a failure that depends on"
echo "      the real mesh size will not reproduce here."
exit 1
