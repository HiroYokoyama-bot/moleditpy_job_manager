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
