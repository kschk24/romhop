from __future__ import annotations

import sys
from pathlib import Path

from romhop.gui import app as gui_app


def test_appimage_bootstrap_installs_when_absent(tmp_path, monkeypatch):
    import romhop.install_bootstrap as ib
    import romhop.gui.launcher_install as li

    calls = {}

    def fake_extract(src):
        calls["src"] = src
        return Path("/inst/romhop")

    monkeypatch.setattr(ib, "is_installed", lambda: False)
    monkeypatch.setattr(ib, "extract_and_install", fake_extract)
    monkeypatch.setattr(li, "install_linux", lambda exec_path: calls.setdefault("exec", exec_path))
    monkeypatch.setattr(ib, "launch_installed", lambda: calls.setdefault("launched", True))
    monkeypatch.setattr(sys, "executable", "/appdir/usr/bin/romhop/romhop")

    handled = gui_app._maybe_bootstrap(["romhop", "--appimage-bootstrap"])
    assert handled is True
    assert calls["src"] == Path("/appdir/usr/bin/romhop")
    assert calls["exec"] == "/inst/romhop"
    assert calls["launched"] is True


def test_appimage_bootstrap_skips_extract_when_installed(monkeypatch):
    import romhop.install_bootstrap as ib
    import romhop.gui.launcher_install as li

    calls = {}
    monkeypatch.setattr(ib, "is_installed", lambda: True)
    monkeypatch.setattr(ib, "extract_and_install", lambda src: calls.setdefault("extracted", True))
    monkeypatch.setattr(li, "install_linux", lambda exec_path: calls.setdefault("shortcut", True))
    monkeypatch.setattr(ib, "launch_installed", lambda: calls.setdefault("launched", True))

    handled = gui_app._maybe_bootstrap(["romhop", "--appimage-bootstrap"])
    assert handled is True
    assert "extracted" not in calls and "shortcut" not in calls
    assert calls["launched"] is True


def test_no_flag_is_not_handled():
    assert gui_app._maybe_bootstrap(["romhop"]) is False


def test_uninstall_dispatch_removes_and_exits(monkeypatch):
    import pytest
    import romhop.install_bootstrap as ib
    import romhop.gui.launcher_install as li

    calls = {}
    monkeypatch.setattr(li, "uninstall_linux", lambda: calls.setdefault("shortcut", True))
    monkeypatch.setattr(ib, "remove_install", lambda: calls.setdefault("app", True))
    with pytest.raises(SystemExit) as exc:
        gui_app._maybe_uninstall(["romhop", "--uninstall"])
    assert exc.value.code == 0
    assert calls == {"shortcut": True, "app": True}


def test_uninstall_dispatch_no_flag():
    assert gui_app._maybe_uninstall(["romhop"]) is False
