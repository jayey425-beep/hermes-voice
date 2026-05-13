from __future__ import annotations

import subprocess
from typing import Sequence


def build_chat_command(extra_args: Sequence[str] | None = None) -> list[str]:
    cmd = ["hermes"]
    if extra_args:
        cmd.extend(extra_args)
    return cmd


def launch_chat(extra_args: Sequence[str] | None = None) -> int:
    cmd = build_chat_command(extra_args)
    proc = subprocess.run(cmd)
    return proc.returncode
