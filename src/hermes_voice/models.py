from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str
    hint: str = ""
    source: str = "generic"


@dataclass
class DoctorReport:
    hermes_cli_path: str | None
    config_path: str
    hermes_python_path: str | None = None
    runtime_label: str = "current"
    checks: list[CheckResult] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(item.ok for item in self.checks)

    @property
    def failed_checks(self) -> list[CheckResult]:
        return [item for item in self.checks if not item.ok]


@dataclass
class VoiceConfigSnapshot:
    path: str
    raw: dict[str, Any]
    voice: dict[str, Any]
    stt: dict[str, Any]
    tts: dict[str, Any]
