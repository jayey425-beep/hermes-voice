from __future__ import annotations

import subprocess
import threading
import time
from pathlib import Path
from typing import Iterable

import typer

from .config import available_presets
from .report import (
    print_doctor,
    print_enable_apply,
    print_enable_preview,
    print_inspect,
    print_restore,
    print_smoke,
    print_verify,
)
from .utils import which

app = typer.Typer(
    help="A universal voice layer for Hermes instances, profiles, and gateways."
)

AUDIO_SUFFIXES = {".ogg", ".mp3", ".wav", ".m4a", ".aac", ".flac"}
DEFAULT_AUDIO_DIRS = [Path.home() / ".hermes" / "audio_cache", Path.cwd()]


def _iter_audio_files(paths: Iterable[Path]) -> dict[str, float]:
    files: dict[str, float] = {}
    for base in paths:
        if not base.exists() or not base.is_dir():
            continue
        for entry in base.rglob("*"):
            if not entry.is_file() or entry.suffix.lower() not in AUDIO_SUFFIXES:
                continue
            try:
                stat = entry.stat()
            except OSError:
                continue
            files[str(entry.resolve())] = stat.st_mtime
    return files


def _pick_player() -> list[str] | None:
    for candidate in ("afplay", "ffplay"):
        if which(candidate):
            return (
                [candidate, "-nodisp", "-autoexit"]
                if candidate == "ffplay"
                else [candidate]
            )
    return None


def _autoplay_new_audio(stop_event: threading.Event, verbose: bool = False) -> None:
    player = _pick_player()
    if player is None:
        if verbose:
            print("[hermes-voice] autoplay disabled: no afplay/ffplay found")
        return

    seen = _iter_audio_files(DEFAULT_AUDIO_DIRS)
    played: set[str] = set()

    while not stop_event.is_set():
        current = _iter_audio_files(DEFAULT_AUDIO_DIRS)
        candidates = []
        for path_str, mtime in current.items():
            previous = seen.get(path_str)
            if (previous is None or mtime > previous) and path_str not in played:
                candidates.append((mtime, path_str))
        candidates.sort()
        for _, path_str in candidates:
            try:
                subprocess.run([*player, path_str], check=False)
                played.add(path_str)
                if verbose:
                    print(f"[hermes-voice] played {path_str}")
            except Exception as exc:
                if verbose:
                    print(f"[hermes-voice] failed to play {path_str}: {exc}")
        seen = current
        stop_event.wait(0.6)


@app.command()
def doctor(
    runtime: str = typer.Option(
        "hermes", "--runtime", help="Check Hermes runtime or current process runtime."
    ),
    profile: str = typer.Option("default", help="Hermes profile name."),
    fix: bool = typer.Option(
        False, "--fix", help="Attempt safe automatic fixes for missing Python modules."
    ),
) -> None:
    """Inspect whether Hermes voice mode is ready on this machine."""
    if runtime not in {"hermes", "current"}:
        raise typer.BadParameter("runtime must be 'hermes' or 'current'")
    raise typer.Exit(print_doctor(runtime=runtime, profile=profile, fix=fix))


@app.command()
def inspect(
    profile: str = typer.Option("default", help="Hermes profile name."),
) -> None:
    """Print the current Hermes voice-related config snapshot."""
    print_inspect(profile=profile)


@app.command()
def enable(
    profile: str = typer.Option("default", help="Hermes profile name."),
    tts: str = typer.Option("edge", help="Recommended TTS provider."),
    stt: str = typer.Option("local", help="Recommended STT provider."),
    preset: str = typer.Option(
        "", help=f"Optional preset. Available: {', '.join(available_presets())}"
    ),
    dry_run: bool = typer.Option(
        True,
        "--dry-run/--apply",
        help="Preview by default; --apply writes backups and merges voice fields into config.",
    ),
) -> None:
    """Generate or apply a recommended voice config patch."""
    if preset and preset not in available_presets():
        raise typer.BadParameter(f"unknown preset: {preset}")
    if dry_run:
        print_enable_preview(tts=tts, stt=stt, profile=profile, preset=preset)
        return
    print_enable_apply(tts=tts, stt=stt, profile=profile, preset=preset)


@app.command()
def restore(
    profile: str = typer.Option("default", help="Hermes profile name."),
    backup: str = typer.Option(
        "",
        help="Specific backup filename to restore, e.g. config.yaml.bak.20260513-130501",
    ),
    list_backups: bool = typer.Option(
        False,
        "--list",
        help="List available backups for this profile instead of restoring.",
    ),
) -> None:
    """Restore the last config backup created by enable --apply."""
    raise typer.Exit(
        print_restore(
            profile=profile, backup_name=backup or None, list_only=list_backups
        )
    )


@app.command()
def verify(
    profile: str = typer.Option("default", help="Hermes profile name."),
    runtime: str = typer.Option(
        "hermes", "--runtime", help="Runtime to use when --full is enabled."
    ),
    full: bool = typer.Option(
        False, "--full", help="Run doctor + config + playback checks together."
    ),
) -> None:
    """Run local audio self-checks for the voice wrapper."""
    raise typer.Exit(print_verify(profile=profile, runtime=runtime, full=full))


@app.command()
def smoke(
    profile: str = typer.Option("default", help="Hermes profile name."),
    runtime: str = typer.Option(
        "hermes", "--runtime", help="Runtime to verify during smoke."
    ),
    preset: str = typer.Option(
        "zh-assistant",
        help=f"Preset to apply during smoke. Available: {', '.join(available_presets())}",
    ),
    auto_fix: bool = typer.Option(
        False, "--auto-fix", help="Run doctor auto-fix before smoke verification."
    ),
) -> None:
    """Apply a temporary voice preset, run full verification, then restore the latest backup."""
    if preset not in available_presets():
        raise typer.BadParameter(f"unknown preset: {preset}")
    raise typer.Exit(
        print_smoke(profile=profile, runtime=runtime, preset=preset, auto_fix=auto_fix)
    )


@app.command(
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True}
)
def chat(
    ctx: typer.Context,
    autoplay: bool = typer.Option(
        True,
        "--autoplay/--no-autoplay",
        help="Auto-play new TTS files created by Hermes during this session.",
    ),
    verbose_autoplay: bool = typer.Option(
        False,
        "--verbose-autoplay",
        help="Print autoplay events while Hermes is running.",
    ),
) -> None:
    """Launch Hermes as a voice-ready wrapper entrypoint."""
    stop_event = threading.Event()
    watcher: threading.Thread | None = None
    if autoplay:
        watcher = threading.Thread(
            target=_autoplay_new_audio, args=(stop_event, verbose_autoplay), daemon=True
        )
        watcher.start()
        time.sleep(0.1)

    proc: (
        subprocess.CompletedProcess[bytes] | subprocess.CompletedProcess[str] | None
    ) = None
    try:
        proc = subprocess.run(["hermes", *ctx.args])
    except FileNotFoundError:
        typer.echo("hermes-voice: 'hermes' command not found in PATH.", err=True)
        raise typer.Exit(127)
    finally:
        stop_event.set()
        if watcher is not None:
            watcher.join(timeout=1.0)
    raise typer.Exit(proc.returncode if proc is not None else 1)


if __name__ == "__main__":
    app()
