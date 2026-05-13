from hermes_voice.doctor import apply_doctor_fixes, build_fix_suggestion, is_python314_wrapper, run_doctor, runtime_source_label


def test_doctor_returns_report():
    report = run_doctor()
    assert report.config_path.endswith("config.yaml")
    assert report.runtime_label == "Hermes runtime [default]"
    assert any(item.name == "hermes_cli" for item in report.checks)
    assert any(item.name == "runtime_python" for item in report.checks)


def test_runtime_source_label():
    assert runtime_source_label("hermes") == "hermes-runtime"
    assert runtime_source_label("current") == "wrapper-runtime"


def test_is_python314_wrapper_detects_path():
    assert is_python314_wrapper("/tmp/python3.14", "current") is True
    assert is_python314_wrapper("/tmp/python3.12", "current") is False


def test_build_fix_suggestion_for_python_module():
    hint = build_fix_suggestion("py:faster_whisper", "current", "/Users/jayey/hermes-voice/.venv/bin/python3.14")
    assert "pip install faster_whisper" in hint
    assert "wrapper-runtime" in hint
    assert "Python 3.12/3.13 wrapper venv" in hint


def test_current_runtime_doctor_marks_python314_faster_whisper_hint():
    report = run_doctor(runtime="current")
    target = next(item for item in report.checks if item.name == "py:faster_whisper")
    if not target.ok:
        assert "Python 3.12/3.13 wrapper venv" in target.hint


def test_apply_doctor_fixes_skips_python314_wrapper_faster_whisper():
    actions = apply_doctor_fixes(runtime="current")
    target = next((item for item in actions if item.check_name == "py:faster_whisper"), None)
    if target is not None:
        assert target.skipped is True
        assert "Python 3.12/3.13 wrapper venv" in target.reason
