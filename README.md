# hermes-voice

A universal voice layer for Hermes instances, profiles, and gateways.

## What it is

`hermes-voice` is a thin wrapper around Hermes Agent's built-in voice capabilities.
It does not replace Hermes audio I/O internals. Instead, it helps you:

- inspect whether a Hermes runtime is actually voice-ready
- generate safe config patches for voice mode
- apply voice settings with backup + restore
- verify local playback and STT/TTS dependencies
- run a smoke test that restores config after verification

## Why this exists

Hermes already has strong built-in voice features. The hard part is making them dependable across:

- multiple Hermes profiles
- local wrappers / launchers
- gateways and future external integrations
- macOS machines with slightly different Python environments

`hermes-voice` provides a small operational layer around that.

## Commands

### doctor

Check whether a runtime is voice-capable.

```bash
hermes-voice doctor
hermes-voice doctor --runtime hermes
hermes-voice doctor --runtime current
```

Sources in output tell you where a failure lives:

- `hermes-runtime`
- `wrapper-runtime`
- `system`
- `profile-config`
- `environment`

Use automatic fix mode for safe Python dependency installs:

```bash
hermes-voice doctor --runtime hermes --fix
hermes-voice doctor --runtime current --fix
```

`doctor --fix` behavior:

- installs missing Python modules when a direct `pip install <module>` is considered safe
- skips non-Python checks
- skips known-bad `faster_whisper` installs on wrapper Python 3.14 and explains why
- reruns doctor and shows a post-fix summary

If `faster_whisper` is missing under the wrapper runtime on Python 3.14, the tool now treats it as a compatibility-class issue, not a simple missing-package issue. Expect guidance like:

```text
/Users/jayey/hermes-voice/.venv/bin/python -m pip install faster_whisper |
faster_whisper may fail on Python 3.14 because PyAV/av wheels are unavailable;
prefer Hermes runtime or create a Python 3.12/3.13 wrapper venv.
```

### inspect

Inspect the current voice-related config snapshot for a profile.

```bash
hermes-voice inspect
hermes-voice inspect --profile demo
```

### enable

Preview or apply a recommended voice patch.

```bash
hermes-voice enable --dry-run
hermes-voice enable --apply
hermes-voice enable --apply --profile demo
hermes-voice enable --apply --preset zh-assistant
hermes-voice enable --apply --preset podcast
hermes-voice enable --apply --preset low-latency
```

Available presets:

- `zh-assistant`
- `podcast`
- `low-latency`

`--apply` behavior:

- creates a timestamped backup before writing
- updates only the voice-related fields
- keeps unrelated config keys intact

### restore

List backups or restore a previous config version.

```bash
hermes-voice restore --list
hermes-voice restore
hermes-voice restore --backup config.yaml.bak.20260513-130501
hermes-voice restore --profile demo --list
```

Behavior:

- `restore --list` shows available timestamped backups and marks the latest one
- `restore` restores the latest backup by default
- `restore --backup <name>` restores a specific backup version
- profile-specific configs restore from their own backup chain

### verify

Run local verification checks.

```bash
hermes-voice verify
hermes-voice verify --full
hermes-voice verify --full --runtime hermes
hermes-voice verify --full --runtime current
```

Checks include:

- local playback command availability
- WAV synthesis/playback roundtrip
- Hermes doctor checks when `--full` is enabled
- profile voice config presence when `--full` is enabled
- a `failure_scope` summary to show whether the failure is inside the selected runtime

### smoke

Apply a temporary preset, verify, then restore the config.

```bash
hermes-voice smoke
hermes-voice smoke --runtime hermes
hermes-voice smoke --runtime current
hermes-voice smoke --preset podcast
hermes-voice smoke --auto-fix
```

Behavior:

- optionally runs `doctor --fix` first when `--auto-fix` is enabled
- applies the selected preset to the target profile
- runs `verify --full`
- always attempts to restore the latest backup at the end
- reports apply / verify / restore status separately
- shows verify details and suggested fixes if verification fails
- shows auto-fix actions before verification when enabled

When `--auto-fix` is used on `--runtime current` with wrapper Python 3.14:

- `faster_whisper` is classified as a compatibility issue
- the tool records a skipped auto-fix action instead of looping on a doomed install
- smoke still proceeds to apply / verify / restore so you can see the full picture

## Typical flows

### Check the real Hermes runtime

```bash
hermes-voice doctor --runtime hermes
hermes-voice verify --full --runtime hermes
```

### Check the wrapper runtime separately

```bash
hermes-voice doctor --runtime current
hermes-voice verify --full --runtime current
```

### Safely test a new preset and revert

```bash
hermes-voice smoke --preset zh-assistant
```

### Try safe dependency repair before smoke

```bash
hermes-voice smoke --runtime hermes --auto-fix
hermes-voice smoke --runtime current --auto-fix
```

## Development

```bash
cd /Users/jayey/hermes-voice
. .venv/bin/activate
pytest -q
```

Current test status during development:

- unit tests passing
- smoke path validated with automatic restore
- runtime-specific failure classification verified
- doctor auto-fix behavior verified for safe install vs skip cases

## Notes

- Hermes runtime and wrapper runtime may differ.
- A failure in `current` does not necessarily mean Hermes itself is broken.
- On this machine, Hermes runtime has passed `faster_whisper` checks while the wrapper runtime may fail due to Python 3.14 + PyAV compatibility.
- For that case, prefer `--runtime hermes` or rebuild the wrapper venv with Python 3.12/3.13.
