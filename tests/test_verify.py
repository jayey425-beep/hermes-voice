from hermes_voice.verify import run_verify, run_verify_full


def test_verify_returns_checks():
    checks = run_verify()
    assert any(item.name == "player_available" for item in checks)
    assert any(item.name == "tone_generated" for item in checks)


def test_verify_full_includes_doctor_and_next_step():
    checks = run_verify_full(profile="default")
    names = [item.name for item in checks]
    assert "hermes_cli" in names
    assert "voice_config_present" in names
    assert "player_available" in names
    assert "failure_scope" in names
    assert "next_step" in names
