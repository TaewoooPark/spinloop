#!/usr/bin/env bash
# install_engine.sh - put the mumax3-ultrafast engine on this machine.
#
# Downloads the published Apple Silicon release (a single ~4 MB binary),
# verifies its SHA-256, and installs it into a user-owned directory. Nothing is
# compiled, so no Go, no Homebrew and no Xcode Command Line Tools are needed.
#
#   install_engine.sh            install or upgrade
#   install_engine.sh --check    report what is installed vs available; no changes
#   install_engine.sh --force    reinstall even if up to date
#   install_engine.sh --prefix D install under D instead of the default
#
# Exit: 0 ready, 1 action needed (--check) or install failed, 2 unsupported host.
#
# The binary goes under the user's data directory rather than /usr/local/bin:
# it needs no privileges, it survives plugin updates, and it does not silently
# shadow another mumax3 the user may already rely on. Nothing is written to
# shell profiles -- the plugin finds the binary itself through MUMAX3_BIN.
set -uo pipefail

REPO="TaewoooPark/mumax3-ultrafast"
ASSET="mumax3-ultrafast-darwin-arm64.tar.gz"
DEFAULT_PREFIX="${XDG_DATA_HOME:-$HOME/.local/share}/spinloop"

PREFIX="$DEFAULT_PREFIX"
MODE="install"

while [ $# -gt 0 ]; do
  case "$1" in
    --check) MODE="check" ;;
    --force) MODE="force" ;;
    --prefix) PREFIX="${2:?--prefix needs a directory}"; shift ;;
    -h|--help) sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
  shift
done

BIN_DIR="$PREFIX/bin"
BIN="$BIN_DIR/mumax3"

say()  { printf '%s\n' "$*"; }
step() { printf '  %-14s %s\n' "$1" "$2"; }

# --- host --------------------------------------------------------------------

if [ "$(uname -s)" != "Darwin" ] || [ "$(uname -m)" != "arm64" ]; then
  say "This release is built for macOS on Apple Silicon."
  say "Host is $(uname -s)/$(uname -m) - nothing to install."
  say "On other platforms, build mumax3 from source instead."
  exit 2
fi

# --- what is already here ----------------------------------------------------

installed_version() {
  local exe="$1"
  [ -x "$exe" ] || return 1
  # The banner goes to stdout as '//mumax 3.12 [...]' followed by the commit.
  "$exe" -vet -v=true /dev/null 2>/dev/null \
    | sed -n 's|^//commit hash: *||p' | head -1
}

find_existing() {
  if [ -n "${MUMAX3_BIN:-}" ] && [ -x "${MUMAX3_BIN}" ]; then
    printf '%s' "$MUMAX3_BIN"; return
  fi
  if [ -x "$BIN" ]; then printf '%s' "$BIN"; return; fi
  command -v mumax3 2>/dev/null || true
}

EXISTING="$(find_existing)"
EXISTING_COMMIT=""
[ -n "$EXISTING" ] && EXISTING_COMMIT="$(installed_version "$EXISTING" || true)"

# --- what is available -------------------------------------------------------

latest_tag() {
  # No auth needed for a public release. gh is used when present because it
  # handles rate limiting; curl is the fallback so this works without gh.
  if command -v gh >/dev/null 2>&1; then
    gh release view --repo "$REPO" --json tagName -q .tagName 2>/dev/null && return
  fi
  /usr/bin/curl --fail --location --silent --show-error \
    "https://api.github.com/repos/$REPO/releases/latest" 2>/dev/null \
    | sed -n 's/.*"tag_name": *"\([^"]*\)".*/\1/p' | head -1
}

say "mumax3-ultrafast engine"
say "-----------------------"

TAG="$(latest_tag)"
if [ -z "$TAG" ]; then
  step "release" "could not reach GitHub"
  if [ -n "$EXISTING" ]; then
    step "installed" "$EXISTING (${EXISTING_COMMIT:-unknown build})"
    say ""
    say "Offline, but a usable engine is already present. Continuing with it."
    exit 0
  fi
  say ""
  say "No engine installed and the release could not be reached."
  say "Check the network, or build from source in a mumax3-ultrafast checkout:"
  say "    cd mumax3-ultrafast && make"
  exit 1
fi

step "release" "$TAG"
if [ -n "$EXISTING" ]; then
  step "installed" "$EXISTING"
  step "build" "${EXISTING_COMMIT:-unknown}"
else
  step "installed" "none"
fi

# Does the present binary have the batching and tuning API? This is the check
# that matters -- a version string does not carry the commit, and builds from
# before 2026-08-01 reject these identifiers at the vet gate.
probe_capabilities() {
  local exe="$1" missing=""
  local tmp; tmp="$(mktemp -d)"
  for knob in SpeculativeStep MinimizeOnGPU DemagExtrapolation; do
    printf 'SetGridSize(4,4,1)\nSetCellSize(4e-9,4e-9,4e-9)\n%s = true\n' "$knob" \
      > "$tmp/$knob.mx3"
    "$exe" -vet -v=false "$tmp/$knob.mx3" 2>&1 | grep -q ': OK' || missing="$missing $knob"
  done
  "$exe" -j 1 -vet /dev/null >/dev/null 2>&1 || missing="$missing -j"
  rm -rf "$tmp"
  printf '%s' "$missing"
}

NEEDS_UPGRADE=0
if [ -n "$EXISTING" ]; then
  MISSING="$(probe_capabilities "$EXISTING")"
  if [ -n "$MISSING" ]; then
    step "missing" "$MISSING"
    NEEDS_UPGRADE=1
  else
    step "features" "batching and tuning API present"
  fi
fi

if [ "$MODE" = "check" ]; then
  say ""
  if [ -z "$EXISTING" ]; then
    say "No engine installed. Run this script without --check to install it."
    exit 1
  fi
  if [ "$NEEDS_UPGRADE" -eq 1 ]; then
    say "An engine is installed but predates the batching and tuning work."
    say "Run this script without --check to upgrade to $TAG."
    exit 1
  fi
  say "Ready."
  exit 0
fi

if [ -n "$EXISTING" ] && [ "$NEEDS_UPGRADE" -eq 0 ] && [ "$MODE" != "force" ]; then
  say ""
  say "Already up to date. Use --force to reinstall."
  exit 0
fi

# --- download ----------------------------------------------------------------

WORK="$(mktemp -d "${TMPDIR:-/tmp}/mumax3-install.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT

BASE="https://github.com/$REPO/releases/download/$TAG"
say ""
step "downloading" "$ASSET ($TAG)"

if ! /usr/bin/curl --fail --location --retry 3 --silent --show-error \
      -o "$WORK/$ASSET" "$BASE/$ASSET"; then
  say "Download failed. The release may not carry an Apple Silicon asset."
  exit 1
fi
if ! /usr/bin/curl --fail --location --retry 3 --silent --show-error \
      -o "$WORK/$ASSET.sha256" "$BASE/$ASSET.sha256"; then
  say "Could not fetch the checksum. Refusing to install an unverified binary."
  exit 1
fi

# --- verify ------------------------------------------------------------------

EXPECTED="$(awk '{print $1; exit}' "$WORK/$ASSET.sha256")"
ACTUAL="$(shasum -a 256 "$WORK/$ASSET" | awk '{print $1}')"
if [ -z "$EXPECTED" ] || [ "$EXPECTED" != "$ACTUAL" ]; then
  say "CHECKSUM MISMATCH - refusing to install."
  say "  expected $EXPECTED"
  say "  got      $ACTUAL"
  exit 1
fi
step "checksum" "verified"

# Provenance attestation, when the GitHub CLI is available. Not required: the
# checksum comes from the same release, so this adds signer identity, not
# integrity.
if command -v gh >/dev/null 2>&1; then
  if gh attestation verify "$WORK/$ASSET" --repo "$REPO" >/dev/null 2>&1; then
    step "attestation" "verified against $REPO"
  else
    step "attestation" "not verified (checksum still matched)"
  fi
fi

# --- install -----------------------------------------------------------------

tar -xzf "$WORK/$ASSET" -C "$WORK" || { say "Could not unpack the archive."; exit 1; }
if [ ! -f "$WORK/mumax3" ]; then
  say "The archive did not contain a mumax3 binary."
  exit 1
fi

mkdir -p "$BIN_DIR" "$PREFIX/share"
# Install atomically so a failure never leaves a half-written binary in place.
cp "$WORK/mumax3" "$BIN.new" && chmod +x "$BIN.new" && mv -f "$BIN.new" "$BIN"
for doc in LICENSE NOTICE THIRD_PARTY_NOTICES.md; do
  [ -f "$WORK/$doc" ] && cp "$WORK/$doc" "$PREFIX/share/$doc"
done
printf '%s\n' "$TAG" > "$PREFIX/share/VERSION"
step "installed" "$BIN"

# --- prove it runs -----------------------------------------------------------

if ! "$BIN" -test -v=false >/dev/null 2>&1; then
  say ""
  say "The binary installed but its GPU backend will not start."
  say "That is usually a macOS version below the build target. Details:"
  "$BIN" -test 2>&1 | head -5 | sed 's/^/    /'
  exit 1
fi
step "gpu" "backend starts"

MISSING="$(probe_capabilities "$BIN")"
if [ -n "$MISSING" ]; then
  step "features" "still missing:$MISSING (release is older than expected)"
else
  step "features" "batching and tuning API present"
fi

# --- report ------------------------------------------------------------------

say ""
say "Ready. The plugin finds this automatically."
say ""
say "To use it from your own terminal as well, either:"
say "    export MUMAX3_BIN=$BIN"
say "  or add it to PATH:"
say "    export PATH=\"$BIN_DIR:\$PATH\""

if ! command -v mumax3-convert >/dev/null 2>&1; then
  say ""
  say "Note: the release ships the engine only, not mumax3-convert, so"
  say "rendering .ovf snapshots to PNG is unavailable. Everything else --"
  say "running, tables, loop metrics, tuning, convergence -- works without it."
  say "To get it, build from a source checkout:"
  say "    cd mumax3-ultrafast && make"
fi

if [ -n "$EXISTING" ] && [ "$EXISTING" != "$BIN" ]; then
  say ""
  say "Another mumax3 is on your PATH at $EXISTING."
  say "It was left alone. The plugin prefers the one it installed;"
  say "set MUMAX3_BIN to override."
fi
exit 0
