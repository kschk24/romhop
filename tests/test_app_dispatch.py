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
    monkeypatch.setattr(ib, "link_cli", lambda: None)
    monkeypatch.setattr(sys, "executable", "/appdir/usr/bin/romhop/romhop")

    handled = gui_app._maybe_bootstrap(["romhop", "--appimage-bootstrap"])
    assert handled is True
    assert calls["src"] == Path("/appdir/usr/bin/romhop")
    assert calls["exec"] == "/inst/romhop"
    assert calls["launched"] is True


def test_appimage_bootstrap_upgrades_headlessly_when_installed(tmp_path, monkeypatch):
    """Upgrade path: always extracts new version, skips desktop shortcut and execv."""
    import sys
    import romhop.install_bootstrap as ib
    import romhop.gui.launcher_install as li

    calls = {}
    monkeypatch.setattr(ib, "is_installed", lambda: True)
    monkeypatch.setattr(ib, "extract_and_install", lambda src: calls.setdefault("extracted", True) or (tmp_path / "romhop"))
    monkeypatch.setattr(li, "install_linux", lambda exec_path: calls.setdefault("shortcut", True))
    monkeypatch.setattr(ib, "launch_installed", lambda: calls.setdefault("launched", True))
    monkeypatch.setattr(ib, "link_cli", lambda: None)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "romhop" / "romhop"))

    handled = gui_app._maybe_bootstrap(["romhop", "--appimage-bootstrap"])
    assert handled is True
    assert calls.get("extracted") is True   # always extracts on upgrade
    assert "shortcut" not in calls          # no desktop shortcut on upgrade
    assert "launched" not in calls          # no execv on upgrade; exits cleanly


def test_no_flag_is_not_handled():
    assert gui_app._maybe_bootstrap(["romhop"]) is False


def test_wants_tray_detects_flag():
    assert gui_app._wants_tray(["romhop", "--tray"]) is True
    assert gui_app._wants_tray(["romhop"]) is False


def test_apply_autostart_registers_when_flag_turns_on(monkeypatch):
    from dataclasses import replace
    from romhop import config
    from romhop.gui import autostart

    calls = []
    monkeypatch.setattr(autostart, "set_enabled", lambda v: calls.append(v))
    old = config.default_settings()
    new = replace(old, start_on_login=True)
    gui_app._apply_autostart(old, new)
    assert calls == [True]


def test_apply_autostart_unregisters_when_flag_turns_off(monkeypatch):
    from dataclasses import replace
    from romhop import config
    from romhop.gui import autostart

    calls = []
    monkeypatch.setattr(autostart, "set_enabled", lambda v: calls.append(v))
    old = replace(config.default_settings(), start_on_login=True)
    new = replace(old, start_on_login=False)
    gui_app._apply_autostart(old, new)
    assert calls == [False]


def test_apply_autostart_noop_when_unchanged(monkeypatch):
    from romhop import config
    from romhop.gui import autostart

    calls = []
    monkeypatch.setattr(autostart, "set_enabled", lambda v: calls.append(v))
    s = config.default_settings()
    gui_app._apply_autostart(s, s)
    assert calls == []


def test_apply_autostart_swallows_errors(monkeypatch):
    from dataclasses import replace
    from romhop import config
    from romhop.gui import autostart

    def boom(_v):
        raise OSError("registry locked")

    monkeypatch.setattr(autostart, "set_enabled", boom)
    old = config.default_settings()
    new = replace(old, start_on_login=True)
    # Best-effort: a failing OS write must not propagate out of save.
    gui_app._apply_autostart(old, new)


def test_uninstall_dispatch_removes_and_exits(monkeypatch):
    import pytest
    import romhop.config as config
    import romhop.install_bootstrap as ib
    import romhop.gui.launcher_install as li

    calls = {}
    monkeypatch.setattr(gui_app, "_prompt_purge_user_data", lambda: False)
    monkeypatch.setattr(gui_app, "_notify_uninstalled", lambda: calls.setdefault("notify", True))
    monkeypatch.setattr(config, "purge_user_data", lambda: calls.setdefault("purge", True))
    monkeypatch.setattr(li, "uninstall_linux", lambda: calls.setdefault("shortcut", True))
    monkeypatch.setattr(ib, "remove_install", lambda: calls.setdefault("app", True))
    with pytest.raises(SystemExit) as exc:
        gui_app._maybe_uninstall(["romhop", "--uninstall"])
    assert exc.value.code == 0
    # No purge when the user declines the opt-in prompt; user still gets feedback.
    assert calls == {"shortcut": True, "app": True, "notify": True}


def test_uninstall_dispatch_purges_when_confirmed(monkeypatch):
    import pytest
    import romhop.config as config
    import romhop.install_bootstrap as ib
    import romhop.gui.launcher_install as li

    calls = {}
    monkeypatch.setattr(gui_app, "_prompt_purge_user_data", lambda: True)
    monkeypatch.setattr(gui_app, "_notify_uninstalled", lambda: None)
    monkeypatch.setattr(config, "purge_user_data", lambda: calls.setdefault("purge", True))
    monkeypatch.setattr(li, "uninstall_linux", lambda: None)
    monkeypatch.setattr(ib, "remove_install", lambda: None)
    with pytest.raises(SystemExit):
        gui_app._maybe_uninstall(["romhop", "--uninstall"])
    assert calls.get("purge") is True


def test_uninstall_dispatch_no_flag():
    assert gui_app._maybe_uninstall(["romhop"]) is False
