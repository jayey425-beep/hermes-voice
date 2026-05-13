from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .doctor import apply_doctor_fixes, run_doctor
from .enable import (
    apply_enable_patch,
    build_enable_preview,
    inspect_voice_state,
    list_enable_backups,
    restore_enable_patch,
    run_smoke,
)
from .launcher import launch_chat
from .verify import run_verify, run_verify_full

console = Console()


def _print_fix_panel(checks) -> None:
    failing = [item for item in checks if not item.ok and item.hint]
    if not failing:
        return
    lines = []
    for item in failing[:6]:
        lines.append(f"- {item.name} [{item.source}]: {item.hint}")
    console.print(Panel.fit("\n".join(lines), title="suggested fixes"))


def _print_fix_actions(actions, title: str) -> None:
    if not actions:
        return
    fix_table = Table(title=title)
    fix_table.add_column("Check")
    fix_table.add_column("Action")
    fix_table.add_column("Result")
    for action in actions:
        result = f"skipped: {action.reason}" if action.skipped else f"exit {action.exit_code}: {action.reason}"
        fix_table.add_row(action.check_name, action.command or "manual", result)
    console.print(fix_table)


def print_doctor(runtime: str = "hermes", profile: str = "default", fix: bool = False) -> int:
    report = run_doctor(runtime=runtime, profile=profile)
    title = f"hermes-voice doctor ({report.runtime_label})"
    table = Table(title=title)
    table.add_column("Check")
    table.add_column("OK")
    table.add_column("Source")
    table.add_column("Detail")
    table.add_column("Hint")
    for item in report.checks:
        table.add_row(item.name, "yes" if item.ok else "no", item.source, item.detail, item.hint)
    console.print(table)
    console.print(
        Panel.fit(
            f"config: {report.config_path}\nhermes: {report.hermes_cli_path or 'missing'}\npython: {report.hermes_python_path or 'unresolved'}"
        )
    )
    _print_fix_panel(report.checks)
    if fix:
        actions = apply_doctor_fixes(runtime=runtime, profile=profile)
        _print_fix_actions(actions, "doctor --fix actions")
        rerun = run_doctor(runtime=runtime, profile=profile)
        console.print(Panel.fit(f"post-fix status: {'ok' if rerun.ok else 'still failing'}", title="doctor --fix summary"))
        return 0 if rerun.ok else 1
    return 0 if report.ok else 1


def print_inspect(profile: str = "default") -> None:
    state = inspect_voice_state(profile=profile)
    console.print(Panel.fit(str(state), title=f"voice config snapshot [{profile}]"))


def print_enable_preview(tts: str, stt: str, profile: str = "default", preset: str = "") -> None:
    preview = build_enable_preview(tts=tts, stt=stt, preset=preset)
    title = f"recommended patch [{profile}] ({preview['preset']}) (--dry-run)"
    body = preview["patch_yaml"] + "\navailable presets: " + ", ".join(preview["available_presets"])
    console.print(Panel(body, title=title))


def print_enable_apply(tts: str, stt: str, profile: str = "default", preset: str = "") -> None:
    result = apply_enable_patch(profile=profile, tts=tts, stt=stt, preset=preset)
    backups = "\n".join(result["backup_paths"])
    console.print(
        Panel.fit(
            f"profile: {profile}\npreset: {result['preset']}\napplied: {', '.join(result['changed_keys'])}\nconfig: {result['config_path']}\nbackups:\n{backups}",
            title="voice config applied",
        )
    )


def print_restore(profile: str = "default", backup_name: str | None = None, list_only: bool = False) -> int:
    if list_only:
        backups = list_enable_backups(profile=profile)
        table = Table(title=f"voice backups [{profile}]")
        table.add_column("Name")
        table.add_column("Latest")
        table.add_column("Path")
        for item in backups:
            table.add_row(item["name"], "yes" if item["is_latest"] else "no", item["path"])
        console.print(table)
        return 0

    result = restore_enable_patch(profile=profile, backup_name=backup_name)
    if result["restored"]:
        console.print(
            Panel.fit(
                f"profile: {profile}\nconfig: {result['config_path']}\nbackup: {result['backup_path']}",
                title="voice config restored",
            )
        )
        return 0
    console.print(
        Panel.fit(
            f"profile: {profile}\nconfig: {result['config_path']}\nbackup: {result['backup_path']}",
            title="voice backup not found",
        )
    )
    return 1


def print_verify(profile: str = "default", runtime: str = "hermes", full: bool = False) -> int:
    checks = run_verify_full(profile=profile, runtime=runtime) if full else run_verify()
    table = Table(title=f"hermes-voice verify{' --full' if full else ''}")
    table.add_column("Check")
    table.add_column("OK")
    table.add_column("Source")
    table.add_column("Detail")
    table.add_column("Hint")
    for item in checks:
        table.add_row(item.name, "yes" if item.ok else "no", item.source, item.detail, item.hint)
    console.print(table)
    _print_fix_panel(checks)
    return 0 if all(item.ok for item in checks) else 1


def print_smoke(profile: str = "default", runtime: str = "hermes", preset: str = "zh-assistant", auto_fix: bool = False) -> int:
    result = run_smoke(profile=profile, runtime=runtime, preset=preset, auto_fix=auto_fix)
    table = Table(title=f"hermes-voice smoke [{profile}] ({preset})")
    table.add_column("Step")
    table.add_column("OK")
    table.add_column("Detail")
    table.add_row("auto-fix", "yes" if auto_fix else "skipped", f"{len(result['fix_actions'])} actions" if auto_fix else "disabled")
    table.add_row("apply", "yes", result["applied"]["config_path"])
    table.add_row("verify", "yes" if result["verify_ok"] else "no", result["verify_error"] or f"{len(result['verify_checks'])} checks")
    table.add_row("restore", "yes" if result["restore_ok"] else "no", result["restored"]["backup_path"])
    console.print(table)
    if result["fix_actions"]:
        class _Action:
            def __init__(self, payload):
                self.check_name = payload["check_name"]
                self.command = payload["command"]
                self.skipped = payload["skipped"]
                self.reason = payload["reason"]
                self.exit_code = payload["exit_code"]
        _print_fix_actions([_Action(item) for item in result["fix_actions"]], "smoke auto-fix actions")
    if result["verify_checks"]:
        verify_table = Table(title="smoke verify details")
        verify_table.add_column("Check")
        verify_table.add_column("OK")
        verify_table.add_column("Source")
        verify_table.add_column("Detail")
        for item in result["verify_checks"]:
            verify_table.add_row(item.name, "yes" if item.ok else "no", item.source, item.detail)
        console.print(verify_table)
        _print_fix_panel(result["verify_checks"])
    return 0 if result["verify_ok"] and result["restore_ok"] else 1


def run_chat(args: list[str] | None = None) -> int:
    return launch_chat(extra_args=args or [])
