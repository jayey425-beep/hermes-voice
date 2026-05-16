from hermes_voice.models import CheckResult, DoctorReport
from hermes_voice.verify import _classify_verify_results, run_verify, run_verify_full


def test_verify_returns_checks():
    checks = run_verify()
    assert any(item.name == "microphone_input" for item in checks)
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


def test_verify_full_dedupes_duplicate_checks(monkeypatch):
    duplicate = CheckResult(
        name="microphone_input",
        ok=False,
        detail="0 input devices visible",
        hint="Grant microphone permission.",
        source="wrapper-runtime",
    )
    monkeypatch.setattr(
        "hermes_voice.verify.run_doctor",
        lambda runtime, profile: DoctorReport(
            hermes_cli_path="/tmp/hermes",
            config_path="/tmp/config.yaml",
            hermes_python_path="/tmp/python",
            runtime_label="Wrapper runtime [default]",
            checks=[duplicate],
        ),
    )
    monkeypatch.setattr(
        "hermes_voice.verify.run_verify",
        lambda: [
            duplicate,
            CheckResult(
                name="player_available",
                ok=True,
                detail="/usr/bin/afplay",
                hint="",
                source="system",
            ),
        ],
    )

    checks = run_verify_full(profile="default", runtime="current")

    assert sum(1 for item in checks if item.name == "microphone_input") == 1


def test_classify_verify_results_dedupes_repeated_hints():
    result = _classify_verify_results(
        [
            CheckResult(
                "microphone_input",
                False,
                "missing",
                "Grant microphone permission.",
                "wrapper-runtime",
            ),
            CheckResult(
                "tone_playback", False, "failed", "Grant audio device access.", "system"
            ),
            CheckResult(
                "microphone_input",
                False,
                "missing",
                "Grant microphone permission.",
                "wrapper-runtime",
            ),
        ],
        runtime="current",
    )

    assert result.name == "failure_scope"
    assert result.hint.count("Grant microphone permission.") == 1
