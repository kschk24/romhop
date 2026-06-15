from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from urllib.parse import quote

import httpx


@dataclass
class Rom:
    id: int
    name: str
    platform_slug: str
    fs_name: str
    fs_name_no_ext: str
    file_names: list[str]
    has_multiple_files: bool = False
    url_cover: str | None = None
    platform_name: str | None = None


class RommClient:
    def __init__(self, http: httpx.Client | None = None, *, base_url: str = "",
                 token: str = ""):
        self._http = http or httpx.Client(base_url=base_url, timeout=60.0)
        # NOTE: mutates the provided client's default headers (one client per run is expected).
        self._http.headers["Authorization"] = f"Bearer {token}"

    def list_roms(self, search_term: str | None = None) -> list[Rom]:
        # GET /api/roms returns a paginated wrapper {items, total, limit, offset, ...}.
        # Page through all results; pass search_term to narrow server-side.
        roms: list[Rom] = []
        offset = 0
        limit = 500
        while True:
            params: dict = {"limit": limit, "offset": offset}
            if search_term:
                params["search_term"] = search_term
            resp = self._http.get("/api/roms", params=params)
            resp.raise_for_status()
            page = resp.json()
            # tolerate a bare list too (defensive)
            items = page["items"] if isinstance(page, dict) else page
            total = page.get("total") if isinstance(page, dict) else None
            for item in items:
                roms.append(Rom(
                    id=item["id"],
                    name=item["name"],
                    platform_slug=item["platform_slug"],
                    fs_name=item["fs_name"],
                    fs_name_no_ext=item["fs_name_no_ext"],
                    file_names=[f["file_name"] for f in (item.get("files") or [])],
                    has_multiple_files=bool(item.get("has_multiple_files", False)),
                    url_cover=item.get("url_cover"),
                    platform_name=item.get("platform_name"),
                ))
            offset += limit
            if not items or total is None or offset >= total:
                break
        return roms

    def download_cover(self, url_cover: str) -> bytes:
        """Fetch raw cover-image bytes for a relative cover URL."""
        resp = self._http.get(url_cover)
        resp.raise_for_status()
        return resp.content

    @contextmanager
    def stream_rom_content(self, rom_id: int, out_name: str):
        """Stream a rom's bytes. Yields ``(total, chunk_iterator)`` where total
        is the Content-Length in bytes (or None if absent). Pure transport —
        the caller owns progress, cancellation, throttling, and writing."""
        url = f"/api/roms/{rom_id}/content/{quote(out_name, safe='')}"
        with self._http.stream("GET", url) as resp:
            resp.raise_for_status()
            cl = resp.headers.get("content-length")
            total = int(cl) if cl is not None else None
            yield total, resp.iter_bytes()

    def list_saves(self, rom_id: int) -> list[dict]:
        resp = self._http.get("/api/saves", params={"rom_id": rom_id})
        resp.raise_for_status()
        return resp.json()

    def upload_save(self, *, rom_id: int, emulator: str | None,
                    file_name: str, data: bytes) -> dict:
        params = {"rom_id": rom_id}
        if emulator:
            params["emulator"] = emulator
        resp = self._http.post(
            "/api/saves", params=params,
            files={"saveFile": (file_name, data, "application/octet-stream")},
        )
        resp.raise_for_status()
        return resp.json()

    def download_save_content(self, save_id: int) -> bytes:
        resp = self._http.get(f"/api/saves/{save_id}/content")
        resp.raise_for_status()
        return resp.content

    def list_states(self, rom_id: int) -> list[dict]:
        resp = self._http.get("/api/states", params={"rom_id": rom_id})
        resp.raise_for_status()
        return resp.json()

    def download_state_content(self, state_id: int) -> bytes:
        resp = self._http.get(f"/api/states/{state_id}/content")
        resp.raise_for_status()
        return resp.content
