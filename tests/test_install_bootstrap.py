# tests/test_install_bootstrap.py
from __future__ import annotations

import os
from pathlib import Path

from romhop import install_bootstrap as ib


def test_install_dir_linux(tmp_path, monkeypatch):
    monkeypatch.setattr(os, "name", "posix")
    assert ib.install_dir(home=tmp_path) == tmp_path / ".local" / "lib" / "romhop"


def test_install_dir_windows(tmp_path, monkeypatch):
    monkeypatch.setattr(os, "name", "nt")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "AppData" / "Local"))
    assert ib.install_dir(home=tmp_path) == tmp_path / "AppData" / "Local" / "Programs" / "romhop"


def test_is_installed_false_then_true(tmp_path, monkeypatch):
    monkeypatch.setattr(os, "name", "posix")
    assert ib.is_installed(home=tmp_path) is False
    launcher = ib.install_dir(home=tmp_path) / "romhop"
    launcher.parent.mkdir(parents=True)
    launcher.write_text("#!/bin/sh\n")
    assert ib.is_installed(home=tmp_path) is True


def _fake_onedir(root: Path) -> Path:
    src = root / "onedir"
    (src / "_internal").mkdir(parents=True)
    (src / "romhop").write_text("#!/bin/sh\necho hi\n")
    (src / "_internal" / "data.bin").write_text("x")
    return src


def test_extract_and_install_copies_tree_and_returns_launcher(tmp_path, monkeypatch):
    monkeypatch.setattr(os, "name", "posix")
    src = _fake_onedir(tmp_path)
    launcher = ib.extract_and_install(src, home=tmp_path)
    assert launcher == ib.install_dir(home=tmp_path) / "romhop"
    assert launcher.exists()
    assert (ib.install_dir(home=tmp_path) / "_internal" / "data.bin").read_text() == "x"
    assert not (ib.install_dir(home=tmp_path).parent / "romhop.tmp").exists()


def test_extract_and_install_replaces_existing(tmp_path, monkeypatch):
    monkeypatch.setattr(os, "name", "posix")
    src = _fake_onedir(tmp_path)
    ib.extract_and_install(src, home=tmp_path)
    stale = ib.install_dir(home=tmp_path) / "stale.txt"
    stale.write_text("old")
    ib.extract_and_install(src, home=tmp_path)
    assert not stale.exists()


def test_extract_and_install_cleans_stale_tmp(tmp_path, monkeypatch):
    monkeypatch.setattr(os, "name", "posix")
    src = _fake_onedir(tmp_path)
    stale_tmp = ib.install_dir(home=tmp_path).parent / "romhop.tmp"
    stale_tmp.mkdir(parents=True)
    (stale_tmp / "leftover.bin").write_text("x")
    launcher = ib.extract_and_install(src, home=tmp_path)  # must not raise
    assert launcher.exists()


def test_launch_installed_execs_launcher(tmp_path, monkeypatch):
    monkeypatch.setattr(os, "name", "posix")
    src = _fake_onedir(tmp_path)
    ib.extract_and_install(src, home=tmp_path)
    calls = {}
    monkeypatch.setattr(os, "execv", lambda path, argv: calls.update(path=path, argv=argv))
    ib.launch_installed(home=tmp_path)
    expected = str(ib.install_dir(home=tmp_path) / "romhop")
    assert calls["path"] == expected
    assert calls["argv"] == [expected]


def test_remove_install(tmp_path, monkeypatch):
    monkeypatch.setattr(os, "name", "posix")
    src = _fake_onedir(tmp_path)
    ib.extract_and_install(src, home=tmp_path)
    assert ib.is_installed(home=tmp_path) is True
    assert ib.remove_install(home=tmp_path) is True
    assert ib.is_installed(home=tmp_path) is False


def test_remove_install_noop_when_absent(tmp_path, monkeypatch):
    monkeypatch.setattr(os, "name", "posix")
    assert ib.remove_install(home=tmp_path) is False


def test_cli_link_path_linux(tmp_path, monkeypatch):
    monkeypatch.setattr(os, "name", "posix")
    assert ib.cli_link_path(home=tmp_path) == tmp_path / ".local" / "bin" / "romhop"


def test_link_cli_creates_symlink_to_installed_launcher(tmp_path, monkeypatch):
    monkeypatch.setattr(os, "name", "posix")
    src = _fake_onedir(tmp_path)
    ib.extract_and_install(src, home=tmp_path)
    link = ib.link_cli(home=tmp_path)
    assert link == tmp_path / ".local" / "bin" / "romhop"
    assert link.is_symlink()
    assert link.resolve() == ib.installed_launcher(home=tmp_path).resolve()


def test_link_cli_replaces_existing_link(tmp_path, monkeypatch):
    monkeypatch.setattr(os, "name", "posix")
    src = _fake_onedir(tmp_path)
    ib.extract_and_install(src, home=tmp_path)
    ib.link_cli(home=tmp_path)
    ib.link_cli(home=tmp_path)  # idempotent, no error
    assert ib.cli_link_path(home=tmp_path).is_symlink()


def test_unlink_cli_removes_symlink(tmp_path, monkeypatch):
    monkeypatch.setattr(os, "name", "posix")
    src = _fake_onedir(tmp_path)
    ib.extract_and_install(src, home=tmp_path)
    ib.link_cli(home=tmp_path)
    ib.unlink_cli(home=tmp_path)
    assert not ib.cli_link_path(home=tmp_path).exists()


def test_unlink_cli_noop_when_absent(tmp_path, monkeypatch):
    monkeypatch.setattr(os, "name", "posix")
    ib.unlink_cli(home=tmp_path)  # no error
