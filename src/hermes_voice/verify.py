from __future__ import annotations

import subprocess
import tempfile
import wave
from pathlib import Path

from .doctor import run_doctor, runtime_source_label
from .models import CheckResult
from .utils import which


def _write_test_tone(path: Path, seconds: int = 1, sample_rate: int = 16000) -> None:
    frames = sample_rate * seconds
    amplitude = 12000
    frequency = 440.0
    with wave.open(str(path), "w") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        for i in range(frames):
            value = int(amplitude * __import__("math").sin(2 * __import__("math").pi * frequency * i / sample_rate))
            wav.writeframesraw(value.to_bytes(2, byteorder="little", signed=True))


def _classify_verify_results(results: list[CheckResult], runtime: str) -> CheckResult:
    failing = [item for item in results if not item.ok]
    source = runtime_source_label(runtime)
    if not failing:
        return CheckResult(
            name="failure_scope",
            ok=True,
            detail=f"all checks passed in {source}",
            hint="",
            source=source,
        )

    sources = sorted({item.source for item in failing if item.source})
    if source in sources:
        detail = f"failure is inside {source}"
    else:
        detail = f"failure is outside {source}: {', '.join(sources)}"
    hints = [item.hint for item in failing if item.hint]
    return CheckResult(
        name="failure_scope",
        ok=False,
        detail=detail,
        hint=" | ".join(hints[:3]),
        source=source,
    )


def run_verify() -> list[CheckResult]:
    results: list[CheckResult] = []

    player = which("afplay") or which("ffplay")
    results.append(CheckResult(
        name="player_available",
        ok=player is not None,
        detail=player or "missing",
        hint="Install ffmpeg or use macOS afplay.",
        source="system",
    ))

    with tempfile.TemporaryDirectory(prefix="hermes-voice-") as tmpdir:
        wav_path = Path(tmpdir) / "verify-tone.wav"
        _write_test_tone(wav_path)
        results.append(CheckResult(
            name="tone_generated",
            ok=wav_path.exists(),
            detail=str(wav_path),
            hint="",
            source="system",
        ))

        if player:
            cmd = [player, str(wav_path)]
            if Path(player).name == "ffplay":
                cmd = [player, "-nodisp", "-autoexit", "-loglevel", "error", str(wav_path)]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            ok = proc.returncode == 0
            detail = "playback ok" if ok else ((proc.stderr or proc.stdout or "playback failed").strip())
            results.append(CheckResult(
                name="tone_playback",
                ok=ok,
                detail=detail,
                hint="Grant audio device access or inspect the player error output.",
                source="system",
            ))

    return results


def run_verify_full(profile: str = "default", runtime: str = "hermes") -> list[CheckResult]:
    results: list[CheckResult] = []
    doctor = run_doctor(runtime=runtime, profile=profile)
    results.extend(doctor.checks)
    results.extend(run_verify())
    results.append(_classify_verify_results(results, runtime=runtime))
    results.append(CheckResult(
        name="next_step",
        ok=True,
        detail=f"Run 'hermes -p {profile}' then '/voice on' to test the interactive loop.",
        hint="Use '/voice tts' if you only want spoken output first.",
        source="next-step",
    ))
    return results
