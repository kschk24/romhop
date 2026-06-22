from __future__ import annotations

import logging
from contextlib import contextmanager
from dataclasses import dataclass, field
from urllib.parse import quote

import httpx

logger = logging.getLogger(__name__)


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
    regions: list[str] = field(default_factory=list)
    languages: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    revision: str | None = None
    screenshots: list[str] = field(default_factory=list)


@dataclass
class RomDetail:
    summary: str | None = None
    release_date: str | None = None
    genres: list[str] = field(default_factory=list)
    file_size: int | None = None


_ROM_PATH_TEMPLATE = "/rom/{rom_id}"


def romm_game_url(base_url: str, rom_id: int) -> str:
    """Return the browser URL for a game's page on the RomM server."""
    return base_url.rstrip("/") + _ROM_PATH_TEMPLATE.format(rom_id=rom_id)


def _genre_names(raw) -> list[str]:
    names: list[str] = []
    for g in raw or []:
        if isinstance(g, str):
            names.append(g)
        elif isinstance(g, dict) and g.get("name"):
            names.append(g["name"])
    return names


class RommClient:
    def __init__(self, http: httpx.Client | None = None, *, base_url: str = "",
                 token: str = ""):
        self._http = http or httpx.Client(base_url=base_url, timeout=60.0)
        # NOTE: mutates the provided client's default headers (one client per run is expected).
        self.set_token(token)

    def set_token(self, token: str) -> None:
        """Swap the bearer token on the live client (e.g. after the GUI edits
        the keyring), so the change takes effect without restarting. An empty
        token drops the header entirely: ``Bearer `` (trailing space) is an
        illegal header value that httpx/h11 reject before any request goes out."""
        if token:
            self._http.headers["Authorization"] = f"Bearer {token}"
        else:
            self._http.headers.pop("Authorization", None)

    def ping(self) -> None:
        """Cheap auth + URL check: fetch a single-item page and raise on any HTTP
        error. Used to validate credentials without paging the whole library."""
        logger.debug("ping RomM")
        resp = self._http.get("/api/roms", params={"limit": 1, "offset": 0})
        resp.raise_for_status()

    def list_roms(self, search_term: str | None = None) -> list[Rom]:
        # GET /api/roms returns a paginated wrapper {items, total, limit, offset, ...}.
        # Page through all results; pass search_term to narrow server-side.
        logger.debug("list_roms search_term=%r", search_term)
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
                    regions=item.get("regions") or [],
                    languages=item.get("languages") or [],
                    tags=item.get("tags") or [],
                    revision=item.get("revision"),
                    screenshots=item.get("merged_screenshots") or [],
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

    def get_rom(self, rom_id: int) -> RomDetail:
        """Fetch one rom's detail metadata. Every field is optional — RomM may
        omit any of them. NOTE: key names (first_release_date_string,
        fs_size_bytes) are assumed; confirm against the live server."""
        resp = self._http.get(f"/api/roms/{rom_id}")
        resp.raise_for_status()
        item = resp.json()
        return RomDetail(
            summary=item.get("summary") or None,
            release_date=item.get("first_release_date_string") or None,
            genres=_genre_names(item.get("genres")),
            file_size=item.get("fs_size_bytes"),
        )

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

    def upload_state(self, *, rom_id: int, emulator: str | None,
                     file_name: str, data: bytes) -> dict:
        params = {"rom_id": rom_id}
        if emulator:
            params["emulator"] = emulator
        resp = self._http.post(
            "/api/states", params=params,
            files={"stateFile": (file_name, data, "application/octet-stream")},
        )
        resp.raise_for_status()
        return resp.json()

    def download_state_content(self, state_id: int) -> bytes:
        resp = self._http.get(f"/api/states/{state_id}/content")
        resp.raise_for_status()
        return resp.content
