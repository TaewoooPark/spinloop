---
description: Install or upgrade the mumax3-ultrafast simulation engine, then check that everything this plugin needs is working. Downloads a verified 4 MB release — no compiler, Homebrew or Xcode needed. Run it once, or whenever a simulation says the engine is missing or out of date.
argument-hint: "[--check to report without changing anything]"
---

# Set up the simulation engine

Run this when the engine is missing, out of date, or you just installed the
plugin. It downloads the published Apple Silicon release, verifies its
checksum, and puts it somewhere the plugin can find.

## What to do

**1. Install (or report, with `--check`):**

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/install_engine.sh $ARGUMENTS
```

The script is idempotent — running it when everything is current prints
"already up to date" and changes nothing. It:

- refuses to run on anything but macOS on Apple Silicon
- verifies SHA-256 before installing, and refuses on a mismatch
- also checks GitHub's provenance attestation when `gh` is available
- installs into `~/.local/share/spinloop/bin/`, never `/usr/local`,
  never with `sudo`, and never edits shell profiles
- leaves any other `mumax3` on the user's PATH alone

Exit `0` ready, `1` something needs doing, `2` unsupported machine.

**2. Then confirm the whole toolchain:**

```bash
${CLAUDE_PLUGIN_ROOT}/skills/mx3-authoring/scripts/preflight.sh
```

This is the check that matters. It probes the *installed binary* for the
features the plugin relies on, rather than trusting a version string.

## What to tell the user

Report three things, in plain language:

1. **What happened** — installed, upgraded, or already fine.
2. **What now works that did not** — if the previous engine predated the
   batching work, say that parameter sweeps now run several at a time.
3. **Anything still missing**, honestly. In particular:
   - **`mumax3-convert` is not in the release.** Rendering `.ovf` snapshots to
     PNG needs it. Everything else — running, tables, hysteresis metrics,
     parameter search, convergence checks — works without it. To get it, build
     from a source checkout: `cd mumax3-ultrafast && make`.
   - If another `mumax3` is on PATH, say which one the plugin will use and how
     to override it (`MUMAX3_BIN`).

Do not tell the user to edit their shell profile unless they ask. The plugin
finds the engine on its own.

## If the install fails

| Symptom | Meaning |
|---|---|
| exit 2, "not Apple Silicon" | This release is arm64 macOS only. Build from source. |
| "could not reach GitHub" | Offline. If an engine is already present the plugin keeps using it. |
| "CHECKSUM MISMATCH" | Do not work around this. Report it — the download was corrupt or tampered with. |
| "backend will not start" | The binary installed but Metal will not initialise, usually a macOS version below the build target. |

## Keeping the API reference honest

The engine ships its own API. If `preflight.sh` reports that
`references/api-index.md` came from a different build, regenerate it from a
source checkout matching the installed release:

```bash
cd <mumax3-ultrafast checkout> && git checkout <release tag>
mkdir -p cmd/genapi
cp <plugin>/skills/mx3-authoring/scripts/gen_api_reference.go cmd/genapi/main.go
go run ./cmd/genapi -out <plugin>/skills/mx3-authoring/references/api-index.md
```

This needs Go, so it is optional — the capability probe in `preflight.sh`
already catches the case that actually breaks things, which is the reference
promising an identifier the engine will reject.
