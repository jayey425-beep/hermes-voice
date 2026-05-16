# hermes-voice

> A universal voice layer for Hermes instances, profiles, and gateways.

[![CI](https://github.com/jayey425-beep/hermes-voice/actions/workflows/ci.yml/badge.svg)](https://github.com/jayey425-beep/hermes-voice/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](pyproject.toml)

---

## Quick Start

```bash
# Install
pip install git+https://github.com/jayey425-beep/hermes-voice.git

# Check if Hermes is voice-ready
hermes-voice doctor

# Run a smoke test (apply preset → verify → auto-restore)
hermes-voice smoke
```

> **Prerequisite**: [Hermes Agent](https://hermes-agent.nousresearch.com) must be installed and on your `PATH`.

---

## Installation

### From GitHub (recommended for users)

```bash
pip install git+https://github.com/jayey425-beep/hermes-voice.git
```

Or with [pipx](https://pipx.pypa.io) to keep it isolated:

```bash
pipx install git+https://github.com/jayey425-beep/hermes-voice.git
```

### Local development

```bash
git clone https://github.com/jayey425-beep/hermes-voice.git
cd hermes-voice
make install-dev
# or: pip install -e .
```

### Verify it's installed

```bash
hermes-voice --help
```

---

## Commands

| Command | Description |
|---|---|
| `doctor` | Check whether a Hermes runtime is voice-ready |
| `inspect` | View current voice-related config snapshot |
| `enable` | Preview or apply a voice config patch |
| `restore` | List backups or restore a previous config |
| `verify` | Run local audio self-checks |
| `smoke` | Apply temp preset → full verify → auto-restore |
| `chat` | Launch Hermes with auto-play of TTS audio |

### doctor

Check a runtime's voice readiness:

```bash
hermes-voice doctor                    # check the main Hermes runtime
hermes-voice doctor --runtime current   # check the current process runtime
hermes-voice doctor --fix               # attempt auto-fixes for missing deps
```

Sources in output pinpoint where a failure lives:
- `hermes-runtime`
- `wrapper-runtime`
- `system`
- `profile-config`
- `environment`

### inspect

See current voice config for a profile:

```bash
hermes-voice inspect
hermes-voice inspect --profile demo
```

### enable

Apply a recommended voice config patch with preset support:

```bash
hermes-voice enable --dry-run                                 # preview changes (default)
hermes-voice enable --apply                                    # write changes
hermes-voice enable --apply --profile demo
hermes-voice enable --apply --preset zh-assistant               # Chinese voice assistant
hermes-voice enable --apply --preset podcast
hermes-voice enable --apply --preset low-latency
```

`--apply` behavior:
- Creates a timestamped backup before writing
- Updates only voice-related config fields
- Keeps unrelated config keys intact

### restore

```bash
hermes-voice restore --list          # list available backups
hermes-voice restore                 # restore latest backup
hermes-voice restore --backup config.yaml.bak.20260513-130501  # specific version
```

### verify

Run local audio self-checks:

```bash
hermes-voice verify                  # quick check
hermes-voice verify --full           # full: doctor + config + playback roundtrip
hermes-voice verify --full --runtime hermes
hermes-voice verify --full --runtime current
```

Checks include:
- Microphone input device visibility
- Local playback command availability
- WAV synthesis/playback roundtrip
- Hermes doctor checks (with `--full`)
- Profile voice config presence (with `--full`)
- `failure_scope` summary showing where the failure lives

### smoke

Safely test a voice preset without permanent changes:

```bash
hermes-voice smoke                                     # zh-assistant preset, auto-restore
hermes-voice smoke --preset podcast
hermes-voice smoke --runtime hermes --auto-fix          # fix deps first
hermes-voice smoke --runtime current --auto-fix
```

`smoke` always:
1. (optionally) runs `doctor --fix` when `--auto-fix` is enabled
2. Applies the selected preset
3. Runs `verify --full`
4. Restores the latest backup
5. Reports apply / verify / restore status separately

### chat

Launch Hermes with auto-play of newly created TTS files:

```bash
hermes-voice chat                           # launch Hermes + auto-play TTS
hermes-voice chat --no-autoplay             # launch Hermes only
hermes-voice chat --verbose-autoplay
hermes-voice chat -- --help                 # pass flags to Hermes itself
```

Watches `~/.hermes/audio_cache` and current directory for new audio files.
Auto-plays `.ogg`, `.mp3`, `.wav`, `.m4a`, `.aac`, `.flac` files.
Prefers `afplay` on macOS, falls back to `ffplay`.

---

## Typical workflows

```bash
# 1. First-time setup — check if voice is ready
hermes-voice doctor --runtime hermes

# 2. Apply a Chinese voice assistant preset
hermes-voice enable --apply --preset zh-assistant

# 3. Verify everything works
hermes-voice verify --full --runtime hermes

# 4. Start chatting
hermes-voice chat
```

```bash
# Safe testing flow — no permanent changes
hermes-voice doctor --fix
hermes-voice smoke --preset podcast --auto-fix
```

---

## Development

```bash
git clone https://github.com/jayey425-beep/hermes-voice.git
cd hermes-voice
make install-dev
make test
```

### Project structure

```
hermes-voice/
├── src/hermes_voice/
│   ├── cli.py         # CLI entry point (Typer)
│   ├── config.py      # Config read/backup/restore
│   ├── doctor.py      # Voice readiness diagnostics
│   ├── enable.py      # Config patching
│   ├── models.py      # Data models
│   ├── report.py      # Output formatting (Rich)
│   ├── utils.py       # Helpers
│   └── verify.py      # Local audio self-tests
├── tests/
│   ├── test_cli.py    # CLI chat / audio tests
│   ├── test_config.py
│   ├── test_doctor.py
│   ├── test_enable.py
│   └── test_verify.py
├── Makefile
├── pyproject.toml
└── README.md
```

---

## Notes

- **Hermes runtime vs wrapper runtime** may differ on the same machine.
- A failure in `current` does not necessarily mean Hermes itself is broken.
- `faster_whisper` may fail on Python 3.14 due to PyAV wheel availability — prefer Python 3.12/3.13 for the wrapper.

## License

[MIT](LICENSE)
