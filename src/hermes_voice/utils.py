from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


def hermes_home(profile: str = "default") -> Path:
    base = Path.home() / ".hermes"
    if profile == "default":
        return base
    return base / "profiles" / profile


def hermes_config_path(profile: str = "default") -> Path:
    return hermes_home(profile) / "config.yaml"


def which(cmd: str) -> str | None:
    return shutil.which(cmd)


def hermes_python_path() -> str | None:
    hermes_cli = which("hermes")
    if not hermes_cli:
        return None

    try:
        first_line = Path(hermes_cli).read_text(encoding="utf-8").splitlines()[0]
    except Exception:
        first_line = ""

    if first_line.startswith("#!"):
        interpreter = first_line[2:].strip()
        if interpreter:
            return interpreter

    resolved = str(Path(hermes_cli).resolve())
    if resolved.endswith("/bin/hermes"):
        candidate = resolved[: -len("/bin/hermes")] + "/bin/python"
        if Path(candidate).exists():
            return candidate
        candidate3 = resolved[: -len("/bin/hermes")] + "/bin/python3"
        if Path(candidate3).exists():
            return candidate3

    return sys.executable


def current_python_path() -> str:
    return sys.executable


def module_exists_in_python(
    python_path: str, module_name: str, timeout: int = 45
) -> bool:
    try:
        proc = subprocess.run(
            [
                python_path,
                "-c",
                f"import importlib.util; raise SystemExit(0 if importlib.util.find_spec({module_name!r}) else 1)",
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return proc.returncode == 0
    except Exception:
        return False
