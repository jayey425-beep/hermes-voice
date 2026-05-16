from __future__ import annotations

import os
import platform
import json
import subprocess
import sys
from dataclasses import dataclass

from .config import snapshot
from .models import CheckResult, DoctorReport
from .utils import (
    current_python_path,
    hermes_config_path,
    hermes_python_path,
    module_exists_in_python,
    which,
)

VOICE_PY_MODULES = ["sounddevice", "numpy", "edge_tts", "faster_whisper"]
SYSTEM_COMMANDS = ["ffmpeg", "ffplay", "afplay", "hermes"]
ENV_KEYS = [
    "GROQ_API_KEY",
    "VOICE_TOOLS_OPENAI_KEY",
    "ELEVENLABS_API_KEY",
    "MISTRAL_API_KEY",
    "XAI_API_KEY",
    "HERMES_LOCAL_STT_COMMAND",
]

PYTHON314_AV_NOTE = (
    "faster_whisper may fail on Python 3.14 because PyAV/av wheels are unavailable; "
    "prefer Hermes runtime or create a Python 3.12/3.13 wrapper venv."
)

MIC_PERMISSION_HINT = (
    "Grant microphone permission to the terminal app, then restart the terminal. "
    "On macOS: System Settings > Privacy & Security > Microphone."
)

SOUNDDEVICE_INPUT_SCRIPT = (
    "import json, sounddevice as sd; "
    "devices = sd.query_devices(); "
    "inputs = [{'name': d.get('name', ''), 'channels': int(d.get('max_input_channels', 0))} "
    "for d in devices if int(d.get('max_input_channels', 0)) > 0]; "
    "print(json.dumps({'default': list(sd.default.device), 'inputs': inputs}))"
)


@dataclass
class FixAction:
    check_name: str
    source: str
    command: str
    skipped: bool
    reason: str
    exit_code: int | None = None
    output: str = ""


def runtime_source_label(runtime: str) -> str:
    return "hermes-runtime" if runtime == "hermes" else "wrapper-runtime"


def is_python314_wrapper(python_path: str | None, runtime: str) -> bool:
    if runtime != "current" or not python_path:
        return False
    if "3.14" in python_path:
        return True
    return sys.version_info[:2] == (3, 14) and python_path == current_python_path()


def build_fix_suggestion(
    check_name: str, runtime: str, python_path: str | None, detail: str = ""
) -> str:
    source = runtime_source_label(runtime)
    pip_python = python_path or ("python3" if runtime == "hermes" else "python")
    if check_name.startswith("py:"):
        mod = check_name.split(":", 1)[1]
        base = f"[{source}] {pip_python} -m pip install {mod}"
        if mod == "faster_whisper" and is_python314_wrapper(python_path, runtime):
            return base + f" | {PYTHON314_AV_NOTE}"
        return base
    if check_name.startswith("cmd:"):
        cmd = check_name.split(":", 1)[1]
        return f"[{source}] Install or expose '{cmd}' on PATH"
    if check_name == "runtime_python":
        return f"[{source}] Ensure the runtime interpreter is resolvable: {detail or pip_python}"
    if check_name == "voice_config_present":
        return "Run 'hermes-voice enable --dry-run' to generate a recommended patch."
    return detail


def _module_fix_command(
    check_name: str, runtime: str, python_path: str | None
) -> str | None:
    if not check_name.startswith("py:"):
        return None
    mod = check_name.split(":", 1)[1]
    pip_python = python_path or ("python3" if runtime == "hermes" else "python")
    return f"{pip_python} -m pip install {mod}"


def check_microphone_input(python_path: str | None, source: str) -> CheckResult:
    if not python_path:
        return CheckResult(
            name="microphone_input",
            ok=False,
            detail="runtime python unresolved",
            hint="Fix runtime_python first.",
            source=source,
        )

    proc = subprocess.run(
        [python_path, "-c", SOUNDDEVICE_INPUT_SCRIPT],
        capture_output=True,
        text=True,
        timeout=20,
    )
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "sounddevice query failed").strip()
        return CheckResult(
            name="microphone_input",
            ok=False,
            detail=detail,
            hint=MIC_PERMISSION_HINT,
            source=source,
        )

    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        payload = {"default": "unknown", "inputs": []}
    inputs = payload.get("inputs", [])
    default = payload.get("default", "unknown")
    if not inputs:
        return CheckResult(
            name="microphone_input",
            ok=False,
            detail=f"0 input devices visible; default={default}",
            hint=MIC_PERMISSION_HINT,
            source=source,
        )
    names = ", ".join(f"{item['name']} ({item['channels']}ch)" for item in inputs[:4])
    return CheckResult(
        name="microphone_input",
        ok=True,
        detail=f"{len(inputs)} input device(s): {names}; default={default}",
        hint="",
        source=source,
    )


def snapshot_exists(path: str) -> bool:
    return os.path.exists(path)


def run_doctor(runtime: str = "hermes", profile: str = "default") -> DoctorReport:
    cfg = snapshot(profile=profile)
    hermes_cli = which("hermes")
    hermes_python = hermes_python_path() if hermes_cli else None
    active_python = hermes_python if runtime == "hermes" else current_python_path()
    runtime_label = (
        f"{'Hermes runtime' if runtime == 'hermes' else 'Wrapper runtime'} [{profile}]"
    )
    source = runtime_source_label(runtime)

    report = DoctorReport(
        hermes_cli_path=hermes_cli,
        config_path=str(hermes_config_path(profile=profile)),
        hermes_python_path=active_python,
        runtime_label=runtime_label,
    )

    report.checks.append(
        CheckResult(
            name="hermes_cli",
            ok=report.hermes_cli_path is not None,
            detail=report.hermes_cli_path or "hermes not found in PATH",
            hint="Install Hermes Agent or add the hermes CLI to PATH.",
            source="system",
        )
    )
    report.checks.append(
        CheckResult(
            name="config_file",
            ok=snapshot_exists(report.config_path),
            detail=report.config_path,
            hint="Run hermes once to generate config.yaml for this profile if missing.",
            source="profile-config",
        )
    )
    report.checks.append(
        CheckResult(
            name="runtime_python",
            ok=bool(active_python),
            detail=active_python or "unable to resolve runtime interpreter",
            hint=build_fix_suggestion(
                "runtime_python",
                runtime,
                active_python,
                active_python or "unable to resolve runtime interpreter",
            ),
            source=source,
        )
    )

    for cmd in SYSTEM_COMMANDS:
        found = which(cmd)
        report.checks.append(
            CheckResult(
                name=f"cmd:{cmd}",
                ok=found is not None,
                detail=found or "missing",
                hint=build_fix_suggestion(f"cmd:{cmd}", runtime, active_python),
                source="system",
            )
        )

    for mod in VOICE_PY_MODULES:
        ok = module_exists_in_python(active_python, mod) if active_python else False
        detail = "installed" if ok else "missing"
        if (
            not ok
            and mod == "faster_whisper"
            and is_python314_wrapper(active_python, runtime)
        ):
            detail = "missing (likely Python 3.14/PyAV incompatibility in wrapper venv)"
        report.checks.append(
            CheckResult(
                name=f"py:{mod}",
                ok=ok,
                detail=detail,
                hint=build_fix_suggestion(f"py:{mod}", runtime, active_python),
                source=source,
            )
        )

    sounddevice_ok = any(
        item.name == "py:sounddevice" and item.ok for item in report.checks
    )
    if sounddevice_ok:
        report.checks.append(check_microphone_input(active_python, source))

    env_present = [key for key in ENV_KEYS if os.getenv(key)]
    report.checks.append(
        CheckResult(
            name="voice_env",
            ok=True,
            detail=", ".join(env_present)
            if env_present
            else "no cloud voice env keys set",
            hint="Local STT/TTS can still work without cloud keys.",
            source="environment",
        )
    )

    voice_enabled = bool(cfg.voice)
    report.checks.append(
        CheckResult(
            name="voice_config_present",
            ok=voice_enabled,
            detail="voice block present"
            if voice_enabled
            else "voice block missing or empty",
            hint=build_fix_suggestion("voice_config_present", runtime, active_python),
            source="profile-config",
        )
    )
    report.checks.append(
        CheckResult(
            name="platform",
            ok=True,
            detail=f"{platform.system()} {platform.release()}",
            hint="",
            source="system",
        )
    )
    return report


def apply_doctor_fixes(
    runtime: str = "hermes", profile: str = "default"
) -> list[FixAction]:
    report = run_doctor(runtime=runtime, profile=profile)
    actions: list[FixAction] = []
    python_path = report.hermes_python_path
    for check in report.failed_checks:
        command = _module_fix_command(check.name, runtime, python_path)
        if not command:
            actions.append(
                FixAction(
                    check.name, check.source, "", True, "no automatic fix available"
                )
            )
            continue
        if check.name == "py:faster_whisper" and is_python314_wrapper(
            python_path, runtime
        ):
            actions.append(
                FixAction(check.name, check.source, command, True, PYTHON314_AV_NOTE)
            )
            continue
        proc = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=600
        )
        actions.append(
            FixAction(
                check_name=check.name,
                source=check.source,
                command=command,
                skipped=False,
                reason="applied" if proc.returncode == 0 else "pip install failed",
                exit_code=proc.returncode,
                output=(proc.stdout + "\n" + proc.stderr).strip(),
            )
        )
    return actions
