from pathlib import Path

from hermes_voice.config import (
    apply_recommended_patch,
    available_presets,
    build_recommended_patch,
    deep_merge,
    list_backups,
    restore_config_backup,
)
from hermes_voice.enable import run_smoke


def test_build_recommended_patch_has_voice_block():
    patch = build_recommended_patch()
    assert patch["voice"]["auto_tts"] is True
    assert patch["stt"]["provider"] == "local"
    assert patch["tts"]["provider"] == "edge"


def test_build_recommended_patch_applies_preset():
    patch = build_recommended_patch(preset="podcast")
    assert patch["voice"]["silence_duration"] == 4
    assert patch["tts"]["edge"]["voice"] == "zh-CN-YunxiNeural"


def test_deep_merge_overwrites_scalars_and_merges_dicts():
    base = {
        "voice": {
            "auto_tts": False,
            "tts": {"provider": "edge", "edge": {"voice": "A"}},
        }
    }
    patch = {"voice": {"auto_tts": True, "tts": {"edge": {"voice": "B"}}}}
    merged = deep_merge(base, patch)
    assert merged["voice"]["auto_tts"] is True
    assert merged["voice"]["tts"]["provider"] == "edge"
    assert merged["voice"]["tts"]["edge"]["voice"] == "B"


def test_apply_recommended_patch_creates_backup_and_merges(tmp_path: Path):
    cfg = tmp_path / "config.yaml"
    cfg.write_text("voice:\n  auto_tts: false\nfoo: bar\n", encoding="utf-8")

    result = apply_recommended_patch(path=cfg)

    assert cfg.exists()
    text = cfg.read_text(encoding="utf-8")
    assert "auto_tts: true" in text
    assert "foo: bar" in text
    assert Path(result.backup_path).exists()
    assert any(Path(path).exists() for path in result.backup_paths)
    assert "voice" in result.changed_keys


def test_restore_config_backup_recovers_previous_version(tmp_path: Path):
    cfg = tmp_path / "config.yaml"
    original = "voice:\n  auto_tts: false\n"
    cfg.write_text(original, encoding="utf-8")
    result = apply_recommended_patch(path=cfg)

    restored = restore_config_backup(path=cfg)

    assert restored.restored is True
    assert restored.backup_path == result.backup_path
    assert cfg.read_text(encoding="utf-8") == original


def test_run_smoke_restores_after_verify(tmp_path: Path):
    cfg = tmp_path / "config.yaml"
    original = "voice:\n  auto_tts: false\n"
    cfg.write_text(original, encoding="utf-8")

    result = run_smoke(
        profile="default", runtime="current", preset="zh-assistant", path=cfg
    )

    assert result["verify_checks"]
    assert result["restore_ok"] is True
    assert cfg.read_text(encoding="utf-8") == original


def test_run_smoke_auto_fix_reports_actions(tmp_path: Path):
    cfg = tmp_path / "config.yaml"
    original = "voice:\n  auto_tts: false\n"
    cfg.write_text(original, encoding="utf-8")

    result = run_smoke(
        profile="default",
        runtime="current",
        preset="zh-assistant",
        path=cfg,
        auto_fix=True,
    )

    assert result["auto_fix"] is True
    assert isinstance(result["fix_actions"], list)
    assert result["restore_ok"] is True
    assert cfg.read_text(encoding="utf-8") == original


def test_list_backups_marks_single_backup_as_latest(tmp_path: Path):
    cfg = tmp_path / "config.yaml"
    cfg.write_text("voice:\n  auto_tts: false\n", encoding="utf-8")
    result = apply_recommended_patch(path=cfg)

    backups = list_backups(path=cfg)

    assert len(backups) >= 1
    target = next(item for item in backups if item.path == result.backup_path)
    assert target.is_latest is True


def test_restore_specific_backup_works_with_distinct_timestamp_names(tmp_path: Path):
    cfg = tmp_path / "config.yaml"
    cfg.write_text("voice:\n  auto_tts: false\nversion: one\n", encoding="utf-8")
    first = apply_recommended_patch(path=cfg)
    latest_link = cfg.with_name(cfg.name + ".bak")
    latest_link.unlink(missing_ok=True)
    Path(first.backup_path).unlink(missing_ok=True)
    cfg.write_text("voice:\n  auto_tts: false\nversion: two\n", encoding="utf-8")
    second = apply_recommended_patch(path=cfg)

    restored = restore_config_backup(
        path=cfg, backup_name=Path(second.backup_path).name
    )

    assert restored.restored is True
    assert restored.backup_path == second.backup_path
    assert "version: two" in cfg.read_text(encoding="utf-8")


def test_available_presets_include_defaults():
    presets = available_presets()
    assert "zh-assistant" in presets
    assert "podcast" in presets
    assert "low-latency" in presets
