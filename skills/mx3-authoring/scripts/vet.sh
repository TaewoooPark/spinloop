#!/usr/bin/env bash
# vet.sh - the compile gate for generated .mx3 files.
#
# Wraps `mumax3 -vet`, which compiles a script (parse, name resolution,
# argument count) without running it. Normalises the output and, crucially,
# separates "your code is wrong" from "this machine cannot check it" so a
# calling agent does not sit in a repair loop against a broken environment.
#
# Usage: vet.sh FILE.mx3 [...]
#
# Exit codes:
#   0  every file compiled
#   1  at least one file failed to compile   -> fix the code
#   2  environment problem                   -> stop editing, report to the user
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

if [ $# -eq 0 ]; then
  echo "usage: vet.sh FILE.mx3 [...]" >&2
  exit 2
fi

if ! command -v "$MUMAX" >/dev/null 2>&1; then
  cat >&2 <<EOF
ENV: '$MUMAX' not found on PATH.
     Install mumax3-ultrafast, or set MUMAX3_BIN to the binary.
     Without it, .mx3 cannot be compile-checked - say so rather than
     presenting unverified code as verified.
EOF
  exit 2
fi

for f in "$@"; do
  if [ ! -f "$f" ]; then
    echo "ENV: no such file: $f" >&2
    exit 2
  fi
done

# -v=false suppresses the version banner; mumax3 still emits '//' log lines.
raw=$("$MUMAX" -vet -v=false "$@" 2>&1)
rc=$?

# GPU/backend failures surface as a panic or an init error, not as a per-file
# verdict. Detect that before trusting the exit code.
if printf '%s' "$raw" | grep -qiE 'panic:|no such device|failed to (init|create)|Metal backend requires|cannot initialize'; then
  {
    echo "ENV: mumax3 could not initialise its GPU backend."
    echo "     -vet links the engine and calls cuda.Init() before compiling,"
    echo "     so it needs a working Metal device - it is not a CPU-only lint."
    echo "--- output ---"
    printf '%s\n' "$raw" | head -20
  } >&2
  exit 2
fi

# Keep only the per-file verdict lines mumax3 prints as "<file> : <verdict>".
verdicts=$(printf '%s\n' "$raw" | grep -E '^[^ ]+ : ' || true)

if [ -z "$verdicts" ]; then
  {
    echo "ENV: no verdict lines from mumax3 -vet (unexpected output)."
    echo "--- output ---"
    printf '%s\n' "$raw" | head -20
  } >&2
  exit 2
fi

fail=0
while IFS= read -r line; do
  file=${line%% : *}
  verdict=${line#* : }
  if [ "$verdict" = "OK" ]; then
    echo "PASS  $file"
  else
    echo "FAIL  $file"
    echo "      $verdict"
    fail=1
  fi
done <<<"$verdicts"

if [ "$fail" -ne 0 ]; then
  exit 1
fi

# A zero exit with all-OK verdicts is the only success path.
if [ "$rc" -ne 0 ]; then
  echo "ENV: all files reported OK but mumax3 exited $rc." >&2
  exit 2
fi
exit 0
