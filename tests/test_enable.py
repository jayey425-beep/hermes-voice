from hermes_voice.enable import build_enable_preview


def test_enable_preview_contains_yaml():
    preview = build_enable_preview()
    assert "voice:" in preview["patch_yaml"]
    assert preview["patch"]["tts"]["provider"] == "edge"
