"""Standalone entry point when run as `python -m job_manager` or `python __main__.py`."""

from __future__ import annotations

import os
import sys
import textwrap

if __package__ is None or __package__ == "":
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
    pkg_name = os.path.basename(os.path.dirname(os.path.abspath(__file__)))
    __package__ = pkg_name

from . import PLUGIN_VERSION, get_service, instances
from . import shutdown as release_service
from .store import default_data_dir

HOST_MONITOR_FLAGS = ("--host-monitor", "--hosts", "host-monitor", "-m")
HELP_FLAGS = ("-h", "--help")

USAGE = """usage: moleditpy-job-manager [--host-monitor]
       moleditpy-job-manager COMMAND ...

Job Manager without the molecular editor: the Job Monitor, or with
--host-monitor (-m) the Host Monitor. A second launch brings the running
Job Manager to the front instead of starting another.

The same program runs as:
  python -m job_manager             from the folder that contains job_manager/
  moleditpy -r job_manager          the plugin installed in MoleditPy 5.3+

Given a command, it is the script command line instead, the same as
moleditpy-job. It talks to the Job Manager already running, whose Local API
must be switched on, and opens no window:
{commands}

Help on one command: COMMAND --help.
"""

#: Options of the command line that may come before its command.
CLI_OPTIONS = ("--url", "--token", "--json")


def _program() -> str:
    """How this was started, so help names a command that exists."""
    if "moleditpy.plugins.plugin_runner" in sys.modules:
        return "moleditpy -r job_manager"
    return "moleditpy-job-manager"


def cli_commands() -> tuple:
    """The script command line's commands, read from its own parser."""
    import argparse

    from .api_client import build_parser

    for action in build_parser()._actions:
        if isinstance(action, argparse._SubParsersAction):
            return tuple(action.choices)
    return ()


def is_cli(args) -> bool:
    """Whether *args* ask for the script command line rather than a window."""
    if not args:
        return False
    first = args[0]
    return first in cli_commands() or first.split("=", 1)[0] in CLI_OPTIONS


def _argument(args, name: str) -> str:
    if name in args[:-1]:
        return args[args.index(name) + 1]
    return ""


def main() -> int:
    args = sys.argv[1:]
    if is_cli(args):
        # Before Qt and the instance lock: a script submitting a job must not
        # bring the running Job Manager's window up, nor need a display.
        from .api_client import main as cli

        return cli(args, prog=_program())
    if any(arg in HELP_FLAGS for arg in args):
        # Before the instance lock: asking for help must not bring a running
        # Job Manager's window up, nor open one.
        print(
            USAGE.replace("moleditpy-job-manager", _program()).format(
                commands=textwrap.fill(
                    " ".join(cli_commands()),
                    76,
                    initial_indent="  ",
                    subsequent_indent="  ",
                    break_on_hyphens=False,
                )
            ),
            end="",
        )
        return 0
    data_dir = default_data_dir()
    tray_mode = "--tray" in args
    host_view = any(arg in HOST_MONITOR_FLAGS for arg in args)

    after_pid = 0
    if tray_mode:
        try:
            after_pid = int(_argument(args, "--after-pid") or 0)
        except ValueError:
            after_pid = 0
        # Before anything is built: a tray process with nothing to do should
        # not first read the job list, put an icon up and take it down again.
        lock = instances.claim_for_tray(data_dir, after_pid)
        if lock is None:
            return 0
    else:
        # One Job Manager at a time, when it is ours to choose: a launch beside
        # one already running -- or still starting -- brings that one's window
        # up instead of starting a second tracker. Before the QApplication, so
        # nothing flashes.
        action = instances.ACTION_SHOW_HOST_MONITOR if host_view else instances.ACTION_SHOW_MONITOR
        lock, running = instances.claim_or_defer(data_dir, action)
        if running is not None:
            print(
                f"Job Manager is already running (pid {running['pid']}, {running['role']}); "
                "its window has been brought up.",
                file=sys.stderr,
            )
            return 0
    try:
        return _run(args, data_dir, tray_mode, host_view, after_pid)
    finally:
        # Last, after the registration has gone: a launch waiting on the lock
        # must not find this process still listed when it gets it.
        if lock is not None:
            lock.release()


def _run(args, data_dir: str, tray_mode: bool, host_view: bool, after_pid: int) -> int:
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName(f"Job Manager {PLUGIN_VERSION}")

    # get_service(), not JobService(): it is the only thing that connects
    # job_finished to the notifier, so building the service directly ran a
    # standalone monitor with neither the desktop notification nor the chat
    # message a job ending is supposed to produce. There is no PluginContext
    # here, which the status-bar counter it also installs allows for.
    service = get_service()
    try:
        if tray_mode:
            # Started by MoleditPy, or a standalone monitor, as it closed: see
            # job_manager/handoff.py.
            import json

            from .standalone import run

            try:
                relaunch = [str(part) for part in json.loads(_argument(args, "--relaunch") or "[]")]
            except (ValueError, TypeError):
                relaunch = []
            return run(app, service, data_dir, relaunch, after_pid)

        from .standalone import run_monitor

        return run_monitor(app, service, data_dir, host_view)
    finally:
        # The module's own teardown, which also takes away the tray icon the
        # notifier put up and the badge on the task bar icon.
        release_service()


if __name__ == "__main__":
    sys.exit(main())
