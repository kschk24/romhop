from __future__ import annotations

import pytest

from romhop import frozen_dispatch as fd


@pytest.mark.parametrize(
    "argv,expected",
    [
        (["romhop"], False),                       # bare launch -> GUI
        (["romhop", "--appimage-bootstrap"], False),
        (["romhop", "--uninstall"], False),
        (["romhop", "--smoke-exit"], False),
        (["romhop", "download"], True),            # CLI subcommand
        (["romhop", "login"], True),
        (["romhop", "config", "show"], True),
        (["romhop", "--help"], True),              # help is a CLI concern
        (["romhop", "gui"], True),                 # explicit gui subcommand -> CLI dispatch
    ],
)
def test_is_cli_invocation(argv, expected):
    assert fd.is_cli_invocation(argv) is expected


def test_main_routes_to_cli(monkeypatch):
    called = {}
    monkeypatch.setattr(fd, "_attach_console_windows", lambda: called.setdefault("attach", True))

    import romhop.cli as cli

    monkeypatch.setattr(cli, "app", lambda: called.setdefault("cli", True))
    fd.main(["romhop", "download"])
    assert called.get("cli") is True
    assert called.get("attach") is True


def test_main_routes_to_gui(monkeypatch):
    called = {}

    import romhop.gui.app as app

    monkeypatch.setattr(app, "run", lambda: called.setdefault("gui", True))
    fd.main(["romhop"])
    assert called.get("gui") is True
