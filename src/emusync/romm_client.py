from __future__ import annotations

from dataclasses import dataclass

import httpx


@dataclass
class Rom:
    id: int
    name: str
    platform_slug: str
    fs_name: str
    fs_name_no_ext: str
    file_names: list[str]


class RommClient:
    def __init__(self, http: httpx.Client | None = None, *, base_url: str = "",
                 token: str = ""):
        self._http = http or httpx.Client(base_url=base_url, timeout=60.0)
        self._http.headers["Authorization"] = f"Bearer {token}"

    def list_roms(self) -> list[Rom]:
        resp = self._http.get("/api/roms")
        resp.raise_for_status()
        roms = []
        for item in resp.json():
            roms.append(Rom(
                id=item["id"],
                name=item["name"],
                platform_slug=item["platform_slug"],
                fs_name=item["fs_name"],
                fs_name_no_ext=item["fs_name_no_ext"],
                file_names=[f["file_name"] for f in item.get("files", [])],
            ))
        return roms

    def download_rom_content(self, rom_id: int, out_name: str) -> bytes:
        resp = self._http.get(f"/api/roms/{rom_id}/content/{out_name}")
        resp.raise_for_status()
        return resp.content

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
