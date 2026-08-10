#!/usr/bin/env bash
# preflight.sh - report what this machine can actually verify.
#
# Run once at the start of a session. The point is to know, before writing any
# .mx3, whether the compile gate is available: if it is not, the workflow
# degrades to reference-only and that has to be stated to the user rather than
# discovered after presenting unverified code.
#
# Exit: 0 fully capable, 1 degraded (reference-only), 2 usage error.
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
status=0

say() { printf '%-12s %s\n' "$1" "$2"; }

echo "mx3-authoring preflight"
echo "-----------------------"

# --- platform --------------------------------------------------------------
os=$(uname -s)
arch=$(uname -m)
if [ "$os" = "Darwin" ] && [ "$arch" = "arm64" ]; then
  say "platform" "OK        macOS/$arch"
else
  say "platform" "WARN      $os/$arch - mumax3-ultrafast targets macOS on Apple Silicon"
  status=1
fi

# --- binary ----------------------------------------------------------------
if command -v "$MUMAX" >/dev/null 2>&1; then
  bin=$(command -v "$MUMAX")
  say "mumax3" "OK        $bin"
else
  say "mumax3" "MISSING   not on PATH (set MUMAX3_BIN to override)"
  echo
  echo "DEGRADED: no compile gate available."
  echo "  You can still consult references/, but you cannot claim any .mx3 is"
  echo "  verified. Say so explicitly in the report."
  exit 1
fi

# --- is it a Metal build, and how new? -------------------------------------
# The version banner is the reliable signal; -ultrafast-probe only exists in
# recent builds, so its absence means "older fork", not "not the fork".
banner=$("$MUMAX" -vet -v=true /dev/null 2>&1 | head -6)
if printf '%s' "$banner" | grep -q 'backend=Metal'; then
  ver=$(printf '%s' "$banner" | sed -n '1s|^//||p')
  say "backend" "OK        Metal - $ver"
  mem=$(printf '%s' "$banner" | sed -n 's/.*recommended working set \([0-9]*MB\).*/\1/p')
  [ -n "$mem" ] && say "memory" "OK        recommended working set $mem"
else
  say "backend" "WARN      not a Metal build"
  echo "             Fork-only knobs (SpeculativeStep, MinimizeOnGPU,"
  echo "             DemagExtrapolation) do not exist upstream - do not emit them."
  status=1
fi

# --- capability probe ------------------------------------------------------
# Version strings are a poor proxy. Ask the binary directly whether it resolves
# the fork-only identifiers, by vetting a script that names them. This is the
# only check that matches what the compile gate will actually accept.
probe_dir=$(mktemp -d "${TMPDIR:-/tmp}/mx3-preflight.XXXXXX")
trap 'rm -rf "$probe_dir"' EXIT
missing=""
for knob in SpeculativeStep MinimizeOnGPU DemagExtrapolation; do
  printf 'SetGridSize(4,4,1)\nSetCellSize(4e-9,4e-9,4e-9)\n%s = true\n' "$knob" \
    > "$probe_dir/$knob.mx3"
  if ! "$MUMAX" -vet -v=false "$probe_dir/$knob.mx3" 2>&1 | grep -q ': OK'; then
    missing="$missing $knob"
  fi
done
if [ -z "$missing" ]; then
  say "fork knobs" "OK        SpeculativeStep, MinimizeOnGPU, DemagExtrapolation"
else
  say "fork knobs" "MISSING  $missing"
  echo "             This binary predates those commits (2026-08-01). Emitting"
  echo "             them will fail the vet gate. Either avoid them, or rebuild:"
  echo "               cd <mumax3-ultrafast checkout> && make"
  echo "             Then regenerate references/api-index.md from that tree."
  status=1
fi

idx="$(dirname "$0")/../references/api-index.md"
if [ -f "$idx" ]; then
  # Strip the Go toolchain out of both banners before comparing. It records who
  # compiled the binary, not what the API is: a locally regenerated index and a
  # downloaded release will always disagree on it, and a warning that can never
  # be cleared just teaches people to ignore warnings.
  strip_go() { sed 's/ go[0-9][^ ]*(gc)//'; }
  stamped=$(sed -n 's/^ *ENGINE: *//p' "$idx" | head -1 | strip_go)
  running=$(printf '%s' "$banner" | sed -n '1s|^//||p' | strip_go)
  if [ -n "$stamped" ] && [ "$stamped" != "$running" ]; then
    say "index" "WARN      generated from a different engine build"
    echo "             index:   $stamped"
    echo "             running: $running"
  else
    # The version string carries no commit hash, so a match here does NOT
    # prove the two builds agree. The capability probe above is the real test.
    say "index" "INFO      version string matches (no commit in banner)"
  fi
fi

# --- can it actually initialise the GPU? -----------------------------------
if "$MUMAX" -test -v=false >/dev/null 2>&1; then
  say "gpu" "OK        backend initialises"
else
  say "gpu" "FAIL      backend will not initialise"
  echo "             -vet links the engine and calls cuda.Init() first, so"
  echo "             compile checking needs a working Metal device."
  status=1
fi

# --- python for the linter -------------------------------------------------
if command -v python3 >/dev/null 2>&1; then
  say "python3" "OK        $(python3 --version 2>&1)"
else
  say "python3" "MISSING   lint_mx3.py cannot run"
  status=1
fi

echo
if [ "$status" -eq 0 ]; then
  echo "READY: vet + lint both available."
else
  echo "DEGRADED: some checks unavailable - report which, do not paper over it."
fi
exit "$status"
