import sys

import pytest
from typer.testing import CliRunner

from romhop.cli import app

runner = CliRunner()


def test_gui_command_is_registered():
    result = runner.invoke(app, ["gui", "--help"])
    assert result.exit_code == 0
    assert "gui" in result.output.lower()


def test_gui_command_errors_cleanly_when_pyside_missing(monkeypatch):
    # Force the lazy import of the GUI package to fail.
    monkeypatch.setitem(sys.modules, "romhop.gui.app", None)
    result = runner.invoke(app, ["gui"])
    assert result.exit_code != 0
    assert "romhop[gui]" in result.output
