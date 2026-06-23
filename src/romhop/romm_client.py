from __future__ import annotations

import logging
import math
import threading
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable
from urllib.parse import quote

import httpx

logger = logging.getLogger(__name__)

UPLOAD_CHUNK_SIZE = 1 << 20  # 1 MiB


class RomAlreadyExists(Exception):
    """upload/start returned 400 'File already exists'."""


class UploadCancelled(Exception):
    """stop_event was set during upload_rom."""


class InsufficientScopeError(Exception):
    """HTTP 403: token is missing a required API scope."""

    def __init__(self, scope: str, response: httpx.Response | None = None) -> None:
        self.scope = scope
        super().__init__(f"Token missing scope '{scope}'. Grant it in the RomM admin panel.")


class ScanError(Exception):
    """Socket.IO scan failed or timed out."""


class ScanConnectError(ScanError):
    """Could not connect to RomM Socket.IO — socket is unreachable."""


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

    # ------------------------------------------------------------------
    # Platform management
    # ------------------------------------------------------------------

    def _check_scope(self, resp: httpx.Response, scope: str) -> None:
        """Raise InsufficientScopeError on 403; raise_for_status on other errors."""
        if resp.status_code == 403:
            raise InsufficientScopeError(scope, resp)
        resp.raise_for_status()

    def list_platforms(self) -> list[dict]:
        """GET /api/platforms. Requires platforms.read scope."""
        resp = self._http.get("/api/platforms")
        self._check_scope(resp, "platforms.read")
        return resp.json()

    def create_platform(self, fs_slug: str) -> dict:
        """Create platform if not already present; return the platform dict.

        Existence-checks first (no dedup via POST). Requires platforms.read +
        platforms.write scopes.
        """
        platforms = self.list_platforms()
        for p in platforms:
            if p.get("fs_slug") == fs_slug or p.get("slug") == fs_slug:
                logger.debug("create_platform: reusing existing slug=%r id=%s", fs_slug, p.get("id"))
                return p
        resp = self._http.post("/api/platforms", json={"fs_slug": fs_slug})
        self._check_scope(resp, "platforms.write")
        return resp.json()

    # ------------------------------------------------------------------
    # Rom upload (chunked, store-only — does NOT create a rom)
    # ------------------------------------------------------------------

    def upload_rom(
        self,
        *,
        platform_id: int,
        file_path: Path,
        file_name: str,
        stop_event: threading.Event | None = None,
        progress_fn: Callable[[int], None] | None = None,
        chunk_size: int = UPLOAD_CHUNK_SIZE,
    ) -> None:
        """Stream one rom file from disk via the chunked start→PUT→complete flow.

        file_name MUST be a bare leaf (no path separators) — a slash causes a
        500 at complete. complete returns 201 with empty body and creates no rom;
        the caller must trigger a scan to materialise the uploaded file.

        Raises RomAlreadyExists if the file already exists on the platform.
        Raises UploadCancelled if stop_event is set during upload.
        Raises InsufficientScopeError on 403 (scope roms.write required).
        """
        file_size = file_path.stat().st_size
        total_chunks = max(1, math.ceil(file_size / chunk_size))

        resp = self._http.post(
            "/api/roms/upload/start",
            headers={
                "x-upload-platform": str(platform_id),
                "x-upload-filename": file_name,
                "x-upload-total-size": str(file_size),
                "x-upload-total-chunks": str(total_chunks),
            },
        )
        if resp.status_code == 400:
            detail = (resp.json() or {}).get("detail", "")
            if "already exists" in detail:
                raise RomAlreadyExists(file_name)
        self._check_scope(resp, "roms.write")
        upload_id = resp.json()["upload_id"]

        try:
            with file_path.open("rb") as fh:
                for chunk_index in range(total_chunks):
                    if stop_event and stop_event.is_set():
                        self._cancel_upload(upload_id)
                        raise UploadCancelled(file_name)
                    chunk = fh.read(chunk_size)
                    put = self._http.put(
                        f"/api/roms/upload/{upload_id}",
                        headers={"x-chunk-index": str(chunk_index)},
                        content=chunk,
                    )
                    put.raise_for_status()
                    if progress_fn:
                        progress_fn(len(chunk))
        except UploadCancelled:
            raise
        except Exception:
            self._cancel_upload(upload_id)
            raise

        complete = self._http.post(f"/api/roms/upload/{upload_id}/complete")
        complete.raise_for_status()

    def _cancel_upload(self, upload_id: str) -> None:
        try:
            self._http.post(f"/api/roms/upload/{upload_id}/cancel")
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Socket.IO scan trigger (materialises uploaded files as roms)
    # ------------------------------------------------------------------

    def trigger_scan(
        self,
        platform_id: int,
        *,
        timeout: float = 60.0,
        _sio_factory=None,
    ) -> dict:
        """Trigger a quick platform-scoped scan via Socket.IO.

        Connects to /ws/socket.io with bearer auth, emits a quick scan for the
        given platform, and awaits scan:done. Returns the scan:done payload.

        Raises ScanConnectError if the socket is unreachable (caller should fall
        back to hand-off: seed a basic mapping entry and tell the user to scan in
        RomM). Raises ScanError on scan:done_ko or timeout.
        """
        import socketio as _sio_mod  # optional dep; imported lazily

        SioClient = _sio_factory or _sio_mod.Client
        sio = SioClient()

        result: dict = {}
        done_event = threading.Event()

        @sio.on("scan:done")  # type: ignore[misc]
        def _on_done(data):
            result["data"] = data
            result["ok"] = True
            done_event.set()

        @sio.on("scan:done_ko")  # type: ignore[misc]
        def _on_done_ko(data):
            result["data"] = data
            result["ok"] = False
            done_event.set()

        base_url = str(self._http.base_url).rstrip("/")
        auth_header = self._http.headers.get("Authorization", "")
        try:
            sio.connect(
                base_url,
                headers={"Authorization": auth_header},
                socketio_path="/ws/socket.io",
                transports=["websocket"],
            )
        except Exception as exc:
            raise ScanConnectError(str(exc)) from exc

        try:
            sio.emit("scan", {
                "platforms": [platform_id],
                "roms_ids": [],
                "type": "quick",
                "apis": [],
            })
            done_event.wait(timeout=timeout)
        finally:
            try:
                sio.disconnect()
            except Exception:
                pass

        if not done_event.is_set():
            raise ScanError(f"Scan timed out after {timeout}s")
        if not result.get("ok"):
            raise ScanError(f"scan:done_ko: {result.get('data')}")
        return result["data"]

    # ------------------------------------------------------------------
    # Post-scan rom discovery
    # ------------------------------------------------------------------

    def find_roms_by_fs_names(
        self,
        platform_slug: str,
        fs_names: set[str],
        search_term: str | None = None,
    ) -> list[Rom]:
        """/api/roms ignores platform_id — filter client-side by platform_slug + fs_name."""
        roms = self.list_roms(search_term=search_term)
        return [
            r for r in roms
            if r.platform_slug == platform_slug and r.fs_name in fs_names
        ]
