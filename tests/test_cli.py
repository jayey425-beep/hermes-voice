import subprocess
import tempfile
from pathlib import Path

from typer.testing import CliRunner

from hermes_voice.cli import _iter_audio_files, _pick_player, app

runner = CliRunner()


def test_app_imports() -> None:
    assert app is not None


def test_iter_audio_files_discovers_nested_audio_files() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        nested = root / "cache" / "tts"
        nested.mkdir(parents=True)
        audio = nested / "reply.wav"
        audio.write_bytes(b"wav")

        files = _iter_audio_files([root])

    assert str(audio.resolve()) in files


def test_pick_player_prefers_afplay(monkeypatch) -> None:
    monkeypatch.setattr(
        "hermes_voice.cli.which",
        lambda cmd: f"/usr/bin/{cmd}" if cmd == "afplay" else None,
    )

    assert _pick_player() == ["afplay"]


def test_pick_player_falls_back_to_ffplay(monkeypatch) -> None:
    monkeypatch.setattr(
        "hermes_voice.cli.which",
        lambda cmd: "/usr/local/bin/ffplay" if cmd == "ffplay" else None,
    )

    assert _pick_player() == ["ffplay", "-nodisp", "-autoexit"]


def test_chat_returns_hermes_exit_code(monkeypatch) -> None:
    class DummyThread:
        def __init__(self, target=None, args=(), daemon=None):
            self.target = target
            self.args = args

        def start(self) -> None:
            return None

        def join(self, timeout=None) -> None:
            return None

    monkeypatch.setattr("hermes_voice.cli.threading.Thread", DummyThread)
    monkeypatch.setattr("hermes_voice.cli.time.sleep", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        "hermes_voice.cli.subprocess.run",
        lambda cmd, **kwargs: subprocess.CompletedProcess(cmd, 7),
    )

    result = runner.invoke(app, ["chat", "--autoplay", "--", "--help"])

    assert result.exit_code == 7


def test_chat_handles_missing_hermes_command(monkeypatch) -> None:
    class DummyThread:
        def __init__(self, target=None, args=(), daemon=None):
            self.target = target
            self.args = args

        def start(self) -> None:
            return None

        def join(self, timeout=None) -> None:
            return None

    def fake_run(cmd, **kwargs):
        if cmd and cmd[0] == "hermes":
            raise FileNotFoundError("hermes")
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr("hermes_voice.cli.threading.Thread", DummyThread)
    monkeypatch.setattr("hermes_voice.cli.time.sleep", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("hermes_voice.cli.subprocess.run", fake_run)

    result = runner.invoke(app, ["chat", "--autoplay"])

    assert result.exit_code == 127
    assert "command not found" in result.stderr
