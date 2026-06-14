from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def run() -> None:
    import sys as _sys
    from pathlib import Path

    import platformdirs
    from PySide6.QtWidgets import QApplication

    from romhop.config import get_token, load_settings
    from romhop.download import download_rom
    from romhop.gui.main_window import MainWindow
    from romhop.mapping_cache import MappingCache
    from romhop.romm_client import RommClient

    settings = load_settings()
    client = RommClient(base_url=settings.romm_url, token=get_token() or "")
    cache_path = Path(platformdirs.user_data_dir("romhop")) / "mapping_cache.json"
    cache = MappingCache(cache_path)

    def rom_provider():
        return client.list_roms()

    def download_action(rom):
        return download_rom(
            rom, client,
            roms_root=settings.roms_root,
            cache=cache,
            overrides=settings.platform_overrides,
        )

    app = QApplication(_sys.argv)
    window = MainWindow(
        settings=settings,
        rom_provider=rom_provider,
        download_action=download_action,
    )
    window.resize(900, 600)
    # An unconfigured or unreachable RomM must not crash startup: open the
    # window empty and surface the failure in the status bar instead.
    try:
        window.load_library()
    except Exception as exc:  # noqa: BLE001 - keep the window alive
        logger.warning("Could not load RomM library at startup: %s", exc)
        window.set_sync_status(f"library load failed: {exc}")
    window.show()
    _sys.exit(app.exec())
