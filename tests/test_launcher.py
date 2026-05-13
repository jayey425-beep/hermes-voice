from hermes_voice.launcher import build_chat_command


def test_build_chat_command_appends_args():
    cmd = build_chat_command(["--help"])
    assert cmd == ["hermes", "--help"]
