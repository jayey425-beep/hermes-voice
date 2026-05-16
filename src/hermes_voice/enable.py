from __future__ import annotations

from .config import (
    apply_recommended_patch,
    available_presets,
    build_recommended_patch,
    list_backups,
    render_patch_yaml,
    restore_config_backup,
)
from .doctor import apply_doctor_fixes
from .verify import run_verify_full


def build_enable_preview(
    tts: str = "edge", stt: str = "local", preset: str = ""
) -> dict[str, object]:
    patch = build_recommended_patch(tts=tts, stt=stt, preset=preset)
    patch_yaml = render_patch_yaml(tts=tts, stt=stt, preset=preset)
    return {
        "patch": patch,
        "patch_yaml": patch_yaml,
        "preset": preset or "custom",
        "available_presets": available_presets(),
    }


def apply_enable_patch(
    profile: str = "default", tts: str = "edge", stt: str = "local", preset: str = ""
) -> dict[str, object]:
    result = apply_recommended_patch(profile=profile, tts=tts, stt=stt, preset=preset)
    return {
        "config_path": result.config_path,
        "backup_path": result.backup_path,
        "backup_paths": result.backup_paths,
        "changed_keys": result.changed_keys,
        "patch": result.applied_patch,
        "preset": preset or "custom",
    }


def restore_enable_patch(
    profile: str = "default", backup_name: str | None = None
) -> dict[str, object]:
    result = restore_config_backup(profile=profile, backup_name=backup_name)
    return {
        "config_path": result.config_path,
        "backup_path": result.backup_path,
        "restored": result.restored,
    }


def list_enable_backups(profile: str = "default") -> list[dict[str, object]]:
    return [
        {"path": item.path, "name": item.name, "is_latest": item.is_latest}
        for item in list_backups(profile=profile)
    ]


def run_smoke(
    profile: str = "default",
    runtime: str = "hermes",
    preset: str = "zh-assistant",
    path=None,
    auto_fix: bool = False,
) -> dict[str, object]:
    fix_actions = (
        apply_doctor_fixes(runtime=runtime, profile=profile) if auto_fix else []
    )
    apply_result = apply_recommended_patch(path=path, profile=profile, preset=preset)
    verify_checks = []
    verify_ok = False
    verify_error = ""
    try:
        verify_checks = run_verify_full(profile=profile, runtime=runtime)
        verify_ok = all(item.ok for item in verify_checks)
    except Exception as exc:
        verify_error = str(exc)
    restore_result = restore_config_backup(path=path, profile=profile)
    return {
        "profile": profile,
        "preset": preset,
        "auto_fix": auto_fix,
        "fix_actions": [
            {
                "check_name": action.check_name,
                "source": action.source,
                "command": action.command,
                "skipped": action.skipped,
                "reason": action.reason,
                "exit_code": action.exit_code,
                "output": action.output,
            }
            for action in fix_actions
        ],
        "applied": {
            "config_path": apply_result.config_path,
            "backup_path": apply_result.backup_path,
            "backup_paths": apply_result.backup_paths,
            "changed_keys": apply_result.changed_keys,
            "patch": apply_result.applied_patch,
        },
        "verify_checks": verify_checks,
        "verify_ok": verify_ok,
        "verify_error": verify_error,
        "restored": {
            "config_path": restore_result.config_path,
            "backup_path": restore_result.backup_path,
            "restored": restore_result.restored,
        },
        "restore_ok": bool(restore_result.restored),
    }


def inspect_voice_state(profile: str = "default") -> dict[str, object]:
    from .config import snapshot

    state = snapshot(profile=profile)
    return {
        "path": state.path,
        "voice": state.voice,
        "stt": state.stt,
        "tts": state.tts,
    }
