from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from .models import VoiceConfigSnapshot
from .utils import hermes_config_path

DEFAULT_ENABLE_PATCH: dict[str, Any] = {
    "voice": {
        "record_key": "ctrl+b",
        "auto_tts": True,
        "beep_enabled": True,
        "silence_threshold": 200,
        "silence_duration": 3.0,
    },
    "stt": {
        "enabled": True,
        "provider": "local",
        "local": {"model": "base"},
    },
    "tts": {
        "provider": "edge",
        "edge": {"voice": "zh-CN-XiaoxiaoNeural"},
    },
}

PRESET_PATCHES: dict[str, dict[str, Any]] = {
    "zh-assistant": {
        "voice": {
            "record_key": "ctrl+b",
            "auto_tts": True,
            "beep_enabled": True,
            "silence_threshold": 180,
            "silence_duration": 2.5,
        },
        "stt": {
            "enabled": True,
            "provider": "local",
            "local": {"model": "base", "language": "zh"},
        },
        "tts": {
            "provider": "edge",
            "edge": {"voice": "zh-CN-XiaoxiaoNeural"},
        },
    },
    "podcast": {
        "voice": {
            "record_key": "ctrl+b",
            "auto_tts": True,
            "beep_enabled": False,
            "silence_threshold": 140,
            "silence_duration": 4.0,
        },
        "stt": {
            "enabled": True,
            "provider": "local",
            "local": {"model": "small", "language": "zh"},
        },
        "tts": {
            "provider": "edge",
            "edge": {"voice": "zh-CN-YunxiNeural"},
        },
    },
    "low-latency": {
        "voice": {
            "record_key": "ctrl+b",
            "auto_tts": True,
            "beep_enabled": False,
            "silence_threshold": 240,
            "silence_duration": 1.2,
        },
        "stt": {
            "enabled": True,
            "provider": "local",
            "local": {"model": "tiny", "language": "zh"},
        },
        "tts": {
            "provider": "edge",
            "edge": {"voice": "zh-CN-XiaoxiaoNeural"},
        },
    },
}


@dataclass
class ApplyResult:
    config_path: str
    backup_path: str
    backup_paths: list[str]
    changed_keys: list[str]
    applied_patch: dict[str, Any]


@dataclass
class RestoreResult:
    config_path: str
    backup_path: str
    restored: bool


@dataclass
class BackupInfo:
    path: str
    name: str
    is_latest: bool


def load_config(path: Path | None = None, profile: str = "default") -> dict[str, Any]:
    cfg_path = path or hermes_config_path(profile=profile)
    if not cfg_path.exists():
        return {}
    data = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def snapshot(path: Path | None = None, profile: str = "default") -> VoiceConfigSnapshot:
    cfg_path = path or hermes_config_path(profile=profile)
    raw = load_config(cfg_path, profile=profile)
    return VoiceConfigSnapshot(
        path=str(cfg_path),
        raw=raw,
        voice=raw.get("voice", {}) or {},
        stt=raw.get("stt", {}) or {},
        tts=raw.get("tts", {}) or {},
    )


def deep_merge(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def available_presets() -> list[str]:
    return sorted(PRESET_PATCHES.keys())


def build_recommended_patch(tts: str = "edge", stt: str = "local", preset: str = "") -> dict[str, Any]:
    if preset:
        if preset not in PRESET_PATCHES:
            raise ValueError(f"unknown preset: {preset}")
        patch = deep_merge({}, PRESET_PATCHES[preset])
    else:
        patch = deep_merge({}, DEFAULT_ENABLE_PATCH)
        patch["tts"]["provider"] = tts
        patch["stt"]["provider"] = stt
        if tts != "edge":
            patch["tts"].setdefault(tts, {})
        if stt != "local":
            patch["stt"].setdefault(stt, {})
    return patch


def render_patch_yaml(tts: str = "edge", stt: str = "local", preset: str = "") -> str:
    return yaml.safe_dump(build_recommended_patch(tts=tts, stt=stt, preset=preset), sort_keys=False, allow_unicode=True)


def backup_path_for_config(cfg_path: Path) -> Path:
    return cfg_path.with_name(cfg_path.name + ".bak")


def timestamped_backup_path_for_config(cfg_path: Path, stamp: str | None = None) -> Path:
    stamp = stamp or datetime.now().strftime("%Y%m%d-%H%M%S")
    return cfg_path.with_name(cfg_path.name + f".bak.{stamp}")


def list_backups(path: Path | None = None, profile: str = "default") -> list[BackupInfo]:
    cfg_path = path or hermes_config_path(profile=profile)
    latest = backup_path_for_config(cfg_path)
    pattern = cfg_path.name + ".bak*"
    backups = sorted(cfg_path.parent.glob(pattern), key=lambda p: p.name, reverse=True)
    return [BackupInfo(path=str(item), name=item.name, is_latest=item == latest) for item in backups if item.is_file()]


def apply_recommended_patch(
    path: Path | None = None,
    profile: str = "default",
    tts: str = "edge",
    stt: str = "local",
    preset: str = "",
) -> ApplyResult:
    cfg_path = path or hermes_config_path(profile=profile)
    cfg_path.parent.mkdir(parents=True, exist_ok=True)

    before_text = cfg_path.read_text(encoding="utf-8") if cfg_path.exists() else ""
    latest_backup_path = backup_path_for_config(cfg_path)
    stamped_backup_path = timestamped_backup_path_for_config(cfg_path)
    latest_backup_path.write_text(before_text, encoding="utf-8")
    stamped_backup_path.write_text(before_text, encoding="utf-8")

    base = load_config(cfg_path, profile=profile)
    patch = build_recommended_patch(tts=tts, stt=stt, preset=preset)
    merged = deep_merge(base, patch)
    cfg_path.write_text(yaml.safe_dump(merged, sort_keys=False, allow_unicode=True), encoding="utf-8")

    return ApplyResult(
        config_path=str(cfg_path),
        backup_path=str(latest_backup_path),
        backup_paths=[str(latest_backup_path), str(stamped_backup_path)],
        changed_keys=sorted(patch.keys()),
        applied_patch=patch,
    )


def restore_config_backup(path: Path | None = None, profile: str = "default", backup_name: str | None = None) -> RestoreResult:
    cfg_path = path or hermes_config_path(profile=profile)
    backup_path = cfg_path.parent / backup_name if backup_name else backup_path_for_config(cfg_path)
    if not backup_path.exists():
        return RestoreResult(config_path=str(cfg_path), backup_path=str(backup_path), restored=False)
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(backup_path.read_text(encoding="utf-8"), encoding="utf-8")
    return RestoreResult(config_path=str(cfg_path), backup_path=str(backup_path), restored=True)
