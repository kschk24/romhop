from __future__ import annotations

import logging
import re
from pathlib import Path

import pytest

from romhop.logging_setup import RedactionFilter, configure_logging


@pytest.fixture(autouse=True)
def clean_root_handlers():
    """Remove romhop-managed handlers before/after each test."""
    root = logging.getLogger()
    yield
    for h in list(root.handlers):
        if getattr(h, "_romhop_managed", False):
            root.removeHandler(h)
            h.close()


def test_file_handler_created(tmp_path, monkeypatch):
    monkeypatch.setattr("platformdirs.user_log_dir", lambda *_: str(tmp_path))
    configure_logging()
    log_path = tmp_path / "romhop.log"
    logging.getLogger("romhop.test").info("hello file")
    assert log_path.exists()
    assert "hello file" in log_path.read_text()


def test_default_level_is_info(tmp_path, monkeypatch):
    monkeypatch.setattr("platformdirs.user_log_dir", lambda *_: str(tmp_path))
    configure_logging()
    assert logging.getLogger().level == logging.INFO


def test_verbose_bumps_to_debug(tmp_path, monkeypatch):
    monkeypatch.setattr("platformdirs.user_log_dir", lambda *_: str(tmp_path))
    configure_logging(verbose=True)
    assert logging.getLogger().level == logging.DEBUG


def test_debug_setting_bumps_to_debug(tmp_path, monkeypatch):
    monkeypatch.setattr("platformdirs.user_log_dir", lambda *_: str(tmp_path))
    configure_logging(debug=True)
    assert logging.getLogger().level == logging.DEBUG


def test_verbose_adds_stderr_handler(tmp_path, monkeypatch):
    import sys
    monkeypatch.setattr("platformdirs.user_log_dir", lambda *_: str(tmp_path))
    configure_logging(verbose=True)
    root = logging.getLogger()
    stream_handlers = [
        h for h in root.handlers
        if getattr(h, "_romhop_managed", False) and isinstance(h, logging.StreamHandler)
        and not isinstance(h, logging.handlers.RotatingFileHandler)
    ]
    assert stream_handlers


def test_no_stderr_handler_by_default(tmp_path, monkeypatch):
    import logging.handlers
    monkeypatch.setattr("platformdirs.user_log_dir", lambda *_: str(tmp_path))
    configure_logging()
    root = logging.getLogger()
    stream_handlers = [
        h for h in root.handlers
        if getattr(h, "_romhop_managed", False) and isinstance(h, logging.StreamHandler)
        and not isinstance(h, logging.handlers.RotatingFileHandler)
    ]
    assert not stream_handlers


# RedactionFilter tests

def _make_record(msg: str, args=None) -> logging.LogRecord:
    r = logging.LogRecord("test", logging.INFO, "", 0, msg, args or (), None)
    return r


def test_redact_token_in_message():
    f = RedactionFilter(token="supersecret123", romm_url="")
    r = _make_record("token=supersecret123 in request")
    f.filter(r)
    assert "supersecret123" not in r.msg
    assert "***" in r.msg


def test_redact_bearer_token():
    f = RedactionFilter(token="mytoken", romm_url="")
    r = _make_record("Authorization: Bearer mytoken sent")
    f.filter(r)
    assert "mytoken" not in r.msg


def test_redact_host():
    f = RedactionFilter(token="", romm_url="http://romm.example.com/")
    r = _make_record("connecting to romm.example.com now")
    f.filter(r)
    assert "romm.example.com" not in r.msg
    assert "<romm-host>" in r.msg


def test_redact_home(tmp_path):
    home = str(Path.home())
    f = RedactionFilter(token="", romm_url="")
    r = _make_record(f"path={home}/games/rom.sfc")
    f.filter(r)
    assert home not in r.msg
    assert "~" in r.msg


def test_redact_args_tuple():
    f = RedactionFilter(token="tok", romm_url="")
    r = _make_record("sending %s", ("tok",))
    f.filter(r)
    assert "tok" not in r.args


def test_no_false_positive_redaction():
    f = RedactionFilter(token="", romm_url="")
    r = _make_record("ordinary log message")
    f.filter(r)
    assert r.msg == "ordinary log message"


def test_reconfigure_replaces_handlers(tmp_path, monkeypatch):
    monkeypatch.setattr("platformdirs.user_log_dir", lambda *_: str(tmp_path))
    configure_logging()
    before = sum(
        1 for h in logging.getLogger().handlers if getattr(h, "_romhop_managed", False)
    )
    configure_logging()
    after = sum(
        1 for h in logging.getLogger().handlers if getattr(h, "_romhop_managed", False)
    )
    assert after == before  # reconfigure, not accumulate
