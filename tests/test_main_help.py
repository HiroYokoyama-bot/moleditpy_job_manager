"""``--help`` prints usage instead of opening a window."""

import sys

import pytest

pytest.importorskip("PySide6")

from job_manager import __main__ as entry  # noqa: E402


@pytest.mark.parametrize("flag", ["-h", "--help"])
def test_help_prints_usage_and_opens_nothing(monkeypatch, capsys, flag):
    def no_instance(*args, **kwargs):
        raise AssertionError("help must not claim or signal an instance")

    monkeypatch.setattr(entry.instances, "claim_or_defer", no_instance)
    monkeypatch.setattr(entry.instances, "claim_for_tray", no_instance)
    monkeypatch.setattr(entry, "_run", no_instance)
    monkeypatch.setattr(sys, "argv", ["__main__.py", "-m", flag])
    assert entry.main() == 0
    out = capsys.readouterr().out
    assert out.startswith("usage: moleditpy-job-manager")
    assert "moleditpy -r job_manager" in out
    out.encode("ascii")


# --- the script command line through the same entry point ------------------


def no_window(monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError("a command must not claim an instance or open a window")

    monkeypatch.setattr(entry.instances, "claim_or_defer", refuse)
    monkeypatch.setattr(entry.instances, "claim_for_tray", refuse)
    monkeypatch.setattr(entry, "_run", refuse)


@pytest.mark.parametrize(
    "argv",
    [
        ["submit", "h2o.inp", "--host", "box", "--command", "x"],
        ["wait", "JOB"],
        ["hosts"],
        ["--json", "jobs"],
        ["--url", "http://127.0.0.1:1", "ping"],
        ["--token=abc", "ping"],
    ],
)
def test_a_command_goes_to_the_api_client(monkeypatch, argv):
    from job_manager import api_client

    no_window(monkeypatch)
    seen = {}

    def fake(args, prog="moleditpy-job"):
        seen.update(args=list(args), prog=prog)
        return 7

    monkeypatch.setattr(api_client, "main", fake)
    monkeypatch.setattr(sys, "argv", ["__main__.py", *argv])
    assert entry.main() == 7  # its exit status, unchanged
    assert seen == {"args": argv, "prog": "moleditpy-job-manager"}


def test_window_flags_never_mean_a_command():
    commands = set(entry.cli_commands())
    assert {"submit", "wait", "download", "hosts", "ping"} <= commands
    gui = (
        set(entry.HOST_MONITOR_FLAGS)
        | set(entry.HELP_FLAGS)
        | {"--tray", "--after-pid", "--relaunch"}
    )
    assert not commands & gui
    for flags in (["-m"], ["--hosts"], ["host-monitor"], ["--host-monitor"], ["--tray"], []):
        assert not entry.is_cli(flags)


def test_a_command_help_is_the_command_lines(monkeypatch, capsys):
    no_window(monkeypatch)
    monkeypatch.setattr(sys, "argv", ["__main__.py", "submit", "--help"])
    with pytest.raises(SystemExit) as raised:
        entry.main()
    assert raised.value.code == 0
    assert capsys.readouterr().out.startswith("usage: moleditpy-job-manager submit")


def test_started_as_a_plugin_help_names_the_plugin_command(monkeypatch, capsys):
    no_window(monkeypatch)
    monkeypatch.setitem(sys.modules, "moleditpy.plugins.plugin_runner", object())
    monkeypatch.setattr(sys, "argv", ["job_manager", "--help"])
    assert entry.main() == 0
    out = capsys.readouterr().out
    assert out.startswith("usage: moleditpy -r job_manager [--host-monitor]")
    assert "moleditpy -r job_manager COMMAND" in out and "submit" in out
    monkeypatch.setattr(sys, "argv", ["job_manager", "wait", "--help"])
    with pytest.raises(SystemExit):
        entry.main()
    assert capsys.readouterr().out.startswith("usage: moleditpy -r job_manager wait")


def test_the_api_client_alone_keeps_its_installed_name(capsys):
    from job_manager import api_client

    with pytest.raises(SystemExit):
        api_client.main(["--help"])
    assert capsys.readouterr().out.startswith("usage: moleditpy-job ")
