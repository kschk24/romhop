from pathlib import Path

from romhop.gui import covers
from romhop.romm_client import Rom


class FakeClient:
    def __init__(self, data=b"PNGDATA", fail=False):
        self.data = data
        self.fail = fail
        self.calls = 0

    def download_cover(self, url_cover):
        self.calls += 1
        if self.fail:
            raise RuntimeError("network down")
        return self.data


def _rom(rom_id=1, url_cover="/assets/covers/1.png"):
    return Rom(id=rom_id, name="Sonic", platform_slug="genesis",
               fs_name="Sonic.md", fs_name_no_ext="Sonic",
               file_names=["Sonic.md"], url_cover=url_cover)


def test_get_cover_fetches_then_caches(tmp_path, monkeypatch):
    monkeypatch.setattr(covers, "cache_dir", lambda: tmp_path)
    client = FakeClient()
    p = covers.get_cover(_rom(), client)
    assert p is not None and Path(p).exists()
    # Second call serves from disk; no extra fetch.
    p2 = covers.get_cover(_rom(), client)
    assert p2 == p
    assert client.calls == 1


def test_get_cover_returns_none_when_no_url(tmp_path, monkeypatch):
    monkeypatch.setattr(covers, "cache_dir", lambda: tmp_path)
    assert covers.get_cover(_rom(url_cover=None), FakeClient()) is None


def test_get_cover_returns_none_on_fetch_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(covers, "cache_dir", lambda: tmp_path)
    assert covers.get_cover(_rom(), FakeClient(fail=True)) is None
