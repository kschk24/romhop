# Gallery Filters + Platform & Downloaded Indicators Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the platform sidebar with a flat all-platform grid plus a Platform/Downloaded/Sort filter bar, add platform-pill and downloaded (dim + ribbon) tile indicators, persist RomM platform display names for GUI+CLI reuse, and show the platform in the CLI `download` match list.

**Architecture:** RomM's rom payload gains a `platform_name` field on the `Rom` dataclass; a small `PlatformNames` JSON cache (sibling of `mapping_cache.json`) persists `slug → name` harvested on every fetch and is read back with a `name→cache→slug` fallback. A new `downloaded_rom_ids()` helper in `local_index` reuses the existing local-index match to mark on-disk games. The GUI gains a stateless `FilterBar` widget; `LibraryView` drops its sidebar and filters/sorts a single grid, rendering a pill + optional dim/ribbon per tile. `MainWindow` places the filter bar under the search row, hides it in settings, and refreshes the downloaded set after each download batch. The CLI reuses the same display-name rule.

**Tech Stack:** Python 3.14, PySide6 (Qt Widgets), pytest + pytest-qt, Typer (CLI), httpx (RomM client).

**Run tests with:** `.venv/bin/python -m pytest` (this repo's Python; py3.14 venv has no pip).

---

### Task 1: `Rom.platform_name` field + `list_roms` harvest

**Files:**
- Modify: `src/romhop/romm_client.py:9-18` (dataclass), `src/romhop/romm_client.py:44-54` (item parse)
- Test: `tests/test_romm_client.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_romm_client.py`:

```python
def test_list_roms_captures_platform_name():
    import httpx
    from romhop.romm_client import RommClient

    def handler(request):
        return httpx.Response(200, json={
            "items": [{
                "id": 1, "name": "Sonic", "platform_slug": "genesis",
                "platform_name": "Sega Genesis",
                "fs_name": "Sonic.md", "fs_name_no_ext": "Sonic",
                "files": [], "has_multiple_files": False, "url_cover": None,
            }],
            "total": 1, "limit": 500, "offset": 0,
        })

    client = RommClient(httpx.Client(transport=httpx.MockTransport(handler),
                                     base_url="http://x"))
    roms = client.list_roms()
    assert roms[0].platform_name == "Sega Genesis"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_romm_client.py::test_list_roms_captures_platform_name -v`
Expected: FAIL — `TypeError: __init__() got an unexpected keyword argument 'platform_name'` (or AttributeError).

- [ ] **Step 3: Add the field and parse it**

In `src/romhop/romm_client.py`, add to the `Rom` dataclass (after `url_cover`):

```python
    url_cover: str | None = None
    platform_name: str | None = None
```

In `list_roms`, inside the `Rom(...)` construction (after `url_cover=item.get("url_cover"),`):

```python
                    url_cover=item.get("url_cover"),
                    platform_name=item.get("platform_name"),
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_romm_client.py -v`
Expected: PASS (all existing romm_client tests still pass).

- [ ] **Step 5: Commit**

```bash
git add src/romhop/romm_client.py tests/test_romm_client.py
git commit -m "feat(romm): capture platform_name from rom payload"
```

---

### Task 2: `PlatformNames` persistence module

**Files:**
- Create: `src/romhop/platform_names.py`
- Test: `tests/test_platform_names.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_platform_names.py`:

```python
from romhop.platform_names import PlatformNames, display_name
from romhop.romm_client import Rom


def _rom(slug, platform_name=None):
    return Rom(id=1, name="G", platform_slug=slug, fs_name="G",
               fs_name_no_ext="G", file_names=[], platform_name=platform_name)


def test_name_for_falls_back_to_slug(tmp_path):
    names = PlatformNames(tmp_path / "p.json")
    assert names.name_for("gb") == "gb"


def test_update_from_roms_persists_and_reloads(tmp_path):
    path = tmp_path / "p.json"
    names = PlatformNames(path)
    names.update_from_roms([_rom("gb", "Game Boy"), _rom("snes", "Super Nintendo")])
    assert names.name_for("gb") == "Game Boy"
    # A fresh instance reads the persisted file.
    assert PlatformNames(path).name_for("snes") == "Super Nintendo"


def test_update_from_roms_ignores_missing_names(tmp_path):
    names = PlatformNames(tmp_path / "p.json")
    names.update_from_roms([_rom("gba", None)])
    assert names.name_for("gba") == "gba"  # nothing cached


def test_display_name_prefers_rom_then_cache_then_slug(tmp_path):
    names = PlatformNames(tmp_path / "p.json")
    names.update_from_roms([_rom("gb", "Game Boy")])
    # rom carries its own name -> use it
    assert display_name(_rom("gb", "GB Color"), names) == "GB Color"
    # rom has no name -> cache
    assert display_name(_rom("gb", None), names) == "Game Boy"
    # rom has no name, slug not cached -> slug
    assert display_name(_rom("xyz", None), names) == "xyz"
    # no cache passed, no rom name -> slug
    assert display_name(_rom("gb", None)) == "gb"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_platform_names.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'romhop.platform_names'`.

- [ ] **Step 3: Implement the module**

Create `src/romhop/platform_names.py`:

```python
from __future__ import annotations

import json
from pathlib import Path

from romhop.romm_client import Rom


class PlatformNames:
    """Persisted RomM platform `slug -> display name` map.

    Harvested from rom payloads on every fetch (so it stays current) and read
    back with a slug fallback, so platform labels survive offline and are
    identical in the GUI and the CLI.
    """

    def __init__(self, path: Path):
        self.path = path
        self._names: dict[str, str] = {}
        if path.exists():
            self._names = json.loads(path.read_text())

    def update_from_roms(self, roms: list[Rom]) -> None:
        changed = False
        for rom in roms:
            name = getattr(rom, "platform_name", None)
            if name and self._names.get(rom.platform_slug) != name:
                self._names[rom.platform_slug] = name
                changed = True
        if changed:
            self.save()

    def name_for(self, slug: str) -> str:
        return self._names.get(slug, slug)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._names, indent=2, sort_keys=True))


def display_name(rom: Rom, names: PlatformNames | None = None) -> str:
    """Platform label for a rom: its own name, else the cache, else the slug."""
    if getattr(rom, "platform_name", None):
        return rom.platform_name
    if names is not None:
        return names.name_for(rom.platform_slug)
    return rom.platform_slug
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_platform_names.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add src/romhop/platform_names.py tests/test_platform_names.py
git commit -m "feat: persisted platform-name cache shared by GUI and CLI"
```

---

### Task 3: `downloaded_rom_ids` helper

**Files:**
- Modify: `src/romhop/local_index.py` (append a function; imports `norm`, `esde_system_for_slug` already present)
- Test: `tests/test_local_index.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_local_index.py`:

```python
def test_downloaded_rom_ids_marks_on_disk_games(tmp_path):
    from romhop.local_index import downloaded_rom_ids
    from romhop.romm_client import Rom

    (tmp_path / "genesis").mkdir()
    (tmp_path / "genesis" / "Sonic.md").write_bytes(b"x")

    roms = [
        Rom(id=1, name="Sonic", platform_slug="genesis",
            fs_name="Sonic.md", fs_name_no_ext="Sonic", file_names=["Sonic.md"]),
        Rom(id=2, name="Mario", platform_slug="nes",
            fs_name="Mario.nes", fs_name_no_ext="Mario", file_names=["Mario.nes"]),
    ]
    assert downloaded_rom_ids(roms, tmp_path, {}) == {1}


def test_downloaded_rom_ids_empty_when_root_missing(tmp_path):
    from romhop.local_index import downloaded_rom_ids
    from romhop.romm_client import Rom
    roms = [Rom(id=1, name="Sonic", platform_slug="genesis",
                fs_name="Sonic.md", fs_name_no_ext="Sonic", file_names=["Sonic.md"])]
    assert downloaded_rom_ids(roms, tmp_path / "nope", {}) == set()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_local_index.py::test_downloaded_rom_ids_marks_on_disk_games -v`
Expected: FAIL — `ImportError: cannot import name 'downloaded_rom_ids'`.

- [ ] **Step 3: Implement the helper**

Append to `src/romhop/local_index.py`:

```python
def downloaded_rom_ids(roms: list[Rom], roms_root: Path,
                       overrides: dict[str, str]) -> set[int]:
    """Ids of roms already present in the local ES-DE tree.

    Walks the library once and matches each rom by its platform-scoped,
    normalized filename keys — the same match `download`/`scan` use, generalized
    to the whole rom set.
    """
    by_system: dict[str, set[str]] = defaultdict(set)
    for game in index_local_library(roms_root, overrides):
        by_system[game.system].add(game.match_key)
    ids: set[int] = set()
    for rom in roms:
        system = esde_system_for_slug(rom.platform_slug, overrides)
        keys = by_system.get(system, set())
        if norm(rom.fs_name) in keys or norm(rom.fs_name_no_ext) in keys:
            ids.add(rom.id)
    return ids
```

(`defaultdict`, `norm`, `esde_system_for_slug`, `index_local_library`, `Rom`, `Path` are all already imported at the top of the file.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_local_index.py -v`
Expected: PASS (new tests + existing ones).

- [ ] **Step 5: Commit**

```bash
git add src/romhop/local_index.py tests/test_local_index.py
git commit -m "feat(local-index): downloaded_rom_ids set for indicators"
```

---

### Task 4: CLI platform suffix + cache warming

**Files:**
- Modify: `src/romhop/cli.py` — `_select_match` (lines ~250-261), `download` (after `client.list_roms`, ~411), `_run_scan` (after `client.list_roms`, ~517)
- Test: `tests/test_cli.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_cli.py` (uses the existing Typer `CliRunner` pattern in that file — mirror how other tests there construct `runner` and patch `_client`/`config`; the assertion below is the new behavior):

```python
def test_download_ambiguous_lists_platform(monkeypatch, tmp_path):
    from typer.testing import CliRunner
    from romhop import cli, config
    from romhop.romm_client import Rom

    settings = config.Settings(roms_root=tmp_path)
    monkeypatch.setattr(cli.config, "load_settings", lambda: settings)
    monkeypatch.setattr(cli.config, "roms_root_configured", lambda s: True)

    class FakeClient:
        def list_roms(self, search_term=None):
            return [
                Rom(id=1, name="Super Mario Land", platform_slug="gb",
                    fs_name="a", fs_name_no_ext="a", file_names=[],
                    platform_name="Game Boy"),
                Rom(id=2, name="Super Mario Land 2: 6 Golden Coins",
                    platform_slug="gb", fs_name="b", fs_name_no_ext="b",
                    file_names=[], platform_name="Game Boy"),
            ]

    monkeypatch.setattr(cli, "_client", lambda: FakeClient())
    monkeypatch.setattr(cli, "_cache_path", lambda: tmp_path / "map.json")
    monkeypatch.setattr(cli, "_platform_names_path", lambda: tmp_path / "names.json")

    result = CliRunner(mix_stderr=True).invoke(cli.app, ["download", "Super Mario"])
    assert result.exit_code == 2
    assert "Super Mario Land - Game Boy" in result.output
    assert "Super Mario Land 2: 6 Golden Coins - Game Boy" in result.output
```

(If `config.Settings` needs more required fields in this repo, copy the construction used by neighboring tests in `tests/test_cli.py`.)

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_cli.py::test_download_ambiguous_lists_platform -v`
Expected: FAIL — output lists bare names (`Super Mario Land`) without `- Game Boy`, and/or `_platform_names_path` is undefined.

- [ ] **Step 3: Implement**

In `src/romhop/cli.py`, add the import near the other `from romhop...` imports:

```python
from romhop.platform_names import PlatformNames, display_name
```

Add a path helper next to `_cache_path`:

```python
def _platform_names_path() -> Path:
    import platformdirs
    return Path(platformdirs.user_data_dir("romhop")) / "platform_names.json"
```

Change `_select_match`'s candidate listing loop (the `for r in matches:` block) to:

```python
    names = PlatformNames(_platform_names_path())
    for r in matches:
        typer.echo(f"  {r.name} - {display_name(r, names)}", err=True)
```

In `download`, immediately after `roms = client.list_roms(search_term=name)` succeeds (before computing `matches`), warm the cache:

```python
    PlatformNames(_platform_names_path()).update_from_roms(roms)
```

In `_run_scan`, immediately after `roms = client.list_roms()` succeeds, add the same line:

```python
    PlatformNames(_platform_names_path()).update_from_roms(roms)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_cli.py -v`
Expected: PASS (new test + existing CLI tests).

- [ ] **Step 5: Commit**

```bash
git add src/romhop/cli.py tests/test_cli.py
git commit -m "feat(cli): show platform in download match list; warm name cache"
```

---

### Task 5: `FilterBar` widget

**Files:**
- Create: `src/romhop/gui/filter_bar.py`
- Test: `tests/test_gui_filter_bar.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_gui_filter_bar.py`:

```python
from romhop.gui.filter_bar import FilterBar


def test_platform_combo_defaults_to_all_then_lists_platforms(qtbot):
    bar = FilterBar()
    qtbot.addWidget(bar)
    bar.set_platforms([("gb", "Game Boy"), ("snes", "Super Nintendo")])
    # Index 0 is "All platforms" -> slug None.
    assert bar.platform_combo.itemText(0) == "All platforms"
    assert bar.platform_combo.itemData(0) is None
    assert bar.platform_combo.itemText(1) == "Game Boy"
    assert bar.platform_combo.itemData(1) == "gb"


def test_platform_change_emits_slug(qtbot):
    bar = FilterBar()
    qtbot.addWidget(bar)
    bar.set_platforms([("gb", "Game Boy")])
    with qtbot.waitSignal(bar.platform_changed) as sig:
        bar.platform_combo.setCurrentIndex(1)
    assert sig.args == ["gb"]


def test_downloaded_change_emits_mode(qtbot):
    bar = FilterBar()
    qtbot.addWidget(bar)
    with qtbot.waitSignal(bar.downloaded_changed) as sig:
        bar.downloaded_combo.setCurrentIndex(1)  # "Downloaded"
    assert sig.args == ["downloaded"]


def test_sort_change_emits_order(qtbot):
    bar = FilterBar()
    qtbot.addWidget(bar)
    with qtbot.waitSignal(bar.sort_changed) as sig:
        bar.sort_combo.setCurrentIndex(1)  # "Name Z-A"
    assert sig.args == ["desc"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_gui_filter_bar.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'romhop.gui.filter_bar'`.

- [ ] **Step 3: Implement the widget**

Create `src/romhop/gui/filter_bar.py`:

```python
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QWidget


class FilterBar(QWidget):
    """Stateless gallery filter controls: Platform, Downloaded, Sort.

    Owns no library data — it only reports the user's intent via signals. The
    platform list is injected with set_platforms().
    """

    platform_changed = Signal(object)   # slug str, or None for "All platforms"
    downloaded_changed = Signal(str)    # "all" | "downloaded" | "missing"
    sort_changed = Signal(str)          # "asc" | "desc"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.platform_combo = QComboBox()
        self.platform_combo.addItem("All platforms", None)
        self.platform_combo.currentIndexChanged.connect(self._emit_platform)

        self.downloaded_combo = QComboBox()
        for label, mode in (("Downloaded: All", "all"),
                            ("Downloaded", "downloaded"),
                            ("Not downloaded", "missing")):
            self.downloaded_combo.addItem(label, mode)
        self.downloaded_combo.currentIndexChanged.connect(
            lambda i: self.downloaded_changed.emit(self.downloaded_combo.itemData(i)))

        self.sort_combo = QComboBox()
        for label, order in (("Name A-Z", "asc"), ("Name Z-A", "desc")):
            self.sort_combo.addItem(label, order)
        self.sort_combo.currentIndexChanged.connect(
            lambda i: self.sort_changed.emit(self.sort_combo.itemData(i)))

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(self.platform_combo)
        row.addWidget(self.downloaded_combo)
        row.addWidget(self.sort_combo)
        row.addStretch(1)

    def set_platforms(self, pairs: list[tuple[str, str]]) -> None:
        """Replace the platform list. `pairs` = [(slug, display_name), ...].
        Keeps "All platforms" at index 0."""
        self.platform_combo.blockSignals(True)
        self.platform_combo.clear()
        self.platform_combo.addItem("All platforms", None)
        for slug, name in pairs:
            self.platform_combo.addItem(name, slug)
        self.platform_combo.setCurrentIndex(0)
        self.platform_combo.blockSignals(False)

    def _emit_platform(self, index: int) -> None:
        self.platform_changed.emit(self.platform_combo.itemData(index))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_gui_filter_bar.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add src/romhop/gui/filter_bar.py tests/test_gui_filter_bar.py
git commit -m "feat(gui): FilterBar widget (platform/downloaded/sort)"
```

---

### Task 6: `LibraryView` — drop sidebar, add filters + indicators

**Files:**
- Modify: `src/romhop/gui/library_view.py`
- Test: `tests/test_gui_views.py` (rewrite sidebar-dependent tests; add new ones)

- [ ] **Step 1: Rewrite `filter_games` and its tests (pure function first)**

Replace the three `filter_games` tests in `tests/test_gui_views.py` (the `test_filter_games_*` functions) and add downloaded/sort tests:

```python
def test_filter_games_all_platforms_sorted_asc():
    roms = [_rom("Sonic", "genesis"), _rom("Mario", "nes"), _rom("Zelda", "nes")]
    out = library_view.filter_games(roms, platform=None, query="")
    assert [r.name for r in out] == ["Mario", "Sonic", "Zelda"]


def test_filter_games_platform_scopes():
    roms = [_rom("Sonic", "genesis"), _rom("Mario", "nes")]
    out = library_view.filter_games(roms, platform="genesis", query="")
    assert [r.name for r in out] == ["Sonic"]


def test_filter_games_query_combines_with_platform():
    roms = [_rom("Sonic", "genesis"), _rom("Streets of Rage", "genesis")]
    out = library_view.filter_games(roms, platform="genesis", query="so")
    assert [r.name for r in out] == ["Sonic"]


def test_filter_games_sort_desc():
    roms = [_rom("Mario", "nes"), _rom("Zelda", "nes")]
    out = library_view.filter_games(roms, platform=None, query="", sort="desc")
    assert [r.name for r in out] == ["Zelda", "Mario"]


def test_filter_games_downloaded_modes():
    a, b = _rom("Sonic", "genesis"), _rom("Mario", "nes")
    ids = {a.id}
    only_dl = library_view.filter_games([a, b], platform=None, query="",
                                        downloaded_ids=ids, downloaded_mode="downloaded")
    assert [r.name for r in only_dl] == ["Sonic"]
    only_missing = library_view.filter_games([a, b], platform=None, query="",
                                             downloaded_ids=ids, downloaded_mode="missing")
    assert [r.name for r in only_missing] == ["Mario"]
```

Run: `.venv/bin/python -m pytest tests/test_gui_views.py -k filter_games -v`
Expected: FAIL — old signature / new params unsupported.

- [ ] **Step 2: Reimplement `filter_games`**

Replace the existing `filter_games` in `src/romhop/gui/library_view.py` with:

```python
def filter_games(roms: list[Rom], platform: str | None, query: str,
                 downloaded_ids: set[int] | None = None,
                 downloaded_mode: str = "all", sort: str = "asc") -> list[Rom]:
    """Filter the whole rom set by platform (None = all), text query, and
    downloaded status, then sort by name. `downloaded_mode` is all/downloaded/missing."""
    ids = downloaded_ids or set()
    q = query.strip().lower()
    out = list(roms)
    if platform is not None:
        out = [r for r in out if r.platform_slug == platform]
    if q:
        out = [r for r in out if q in r.name.lower()]
    if downloaded_mode == "downloaded":
        out = [r for r in out if r.id in ids]
    elif downloaded_mode == "missing":
        out = [r for r in out if r.id not in ids]
    out.sort(key=lambda r: r.name.lower(), reverse=(sort == "desc"))
    return out
```

Run: `.venv/bin/python -m pytest tests/test_gui_views.py -k filter_games -v`
Expected: PASS.

- [ ] **Step 3: Rewrite the sidebar-dependent widget tests**

In `tests/test_gui_views.py`, **delete** `test_selection_persists_across_platform_switch` and `test_tiles_have_fixed_size_regardless_of_game_count`'s sidebar usage and **replace** `test_library_view_populates_and_selects` + the fixed-size test with these (also delete any other reference to `view.sidebar` or `view.current_platform()`):

```python
def test_library_view_populates_all_platforms(qtbot):
    from romhop.gui.library_view import LibraryView
    view = LibraryView()
    qtbot.addWidget(view)
    view.set_roms([_rom("Sonic", "genesis"), _rom("Mario", "nes")])
    # No sidebar: both platforms render in one flat grid.
    assert {rom.name for _, rom in view._checks.values()} == {"Sonic", "Mario"}
    check, rom = next((c, r) for c, r in view._checks.values() if r.name == "Sonic")
    check.setChecked(True)
    assert view.selected_roms()[0].name == "Sonic"


def test_platform_filter_scopes_grid(qtbot):
    from romhop.gui.library_view import LibraryView
    view = LibraryView()
    qtbot.addWidget(view)
    view.set_roms([_rom("Sonic", "genesis"), _rom("Mario", "nes")])
    view.set_platform_filter("genesis")
    assert {rom.name for _, rom in view._checks.values()} == {"Sonic"}


def test_selection_survives_platform_filter(qtbot):
    from romhop.gui.library_view import LibraryView
    view = LibraryView()
    qtbot.addWidget(view)
    view.set_roms([_rom("Sonic", "genesis"), _rom("Mario", "nes")])
    check, _ = next((c, r) for c, r in view._checks.values() if r.name == "Sonic")
    check.setChecked(True)
    view.set_platform_filter("nes")           # Sonic now off-screen
    check2, _ = next((c, r) for c, r in view._checks.values() if r.name == "Mario")
    check2.setChecked(True)
    assert sorted(r.name for r in view.selected_roms()) == ["Mario", "Sonic"]


def test_tiles_have_fixed_size_regardless_of_game_count(qtbot):
    from romhop.gui.library_view import CELL_HEIGHT, CELL_WIDTH, LibraryView
    view = LibraryView()
    qtbot.addWidget(view)
    view.set_roms([_rom(f"G{i}", "nds") for i in range(30)] + [_rom("Solo", "threeds")])
    assert view._cells
    for c in view._cells:
        assert c.minimumHeight() == CELL_HEIGHT and c.maximumHeight() == CELL_HEIGHT
        assert c.minimumWidth() == CELL_WIDTH and c.maximumWidth() == CELL_WIDTH
```

Run: `.venv/bin/python -m pytest tests/test_gui_views.py -v`
Expected: FAIL — `set_platform_filter` not defined; `view.sidebar` removed references gone but code still has sidebar.

- [ ] **Step 4: Refactor `LibraryView` — remove sidebar, add filter state**

In `src/romhop/gui/library_view.py`:

Remove the `QListWidget` import. In `__init__`, **delete** the `self.sidebar = QListWidget()` block and the `_on_platform` connection, and **delete** the `self.sidebar` from the layout. Replace the layout/init region (from `self.sidebar = ...` through the `row.addWidget(self._scroll, 1)`) with:

```python
        self._platform_filter: str | None = None
        self._downloaded_mode = "all"
        self._sort = "asc"
        self._downloaded_ids: set[int] = set()

        self._grid_host = QWidget()
        self._grid = QGridLayout(self._grid_host)
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setWidget(self._grid_host)

        row = QHBoxLayout(self)
        row.addWidget(self._scroll, 1)
```

Add `platform_label` injection to `__init__`'s signature and store it:

```python
    def __init__(self, parent=None, *, cover_provider=None, platform_label=None):
        super().__init__(parent)
        # platform_label(rom) -> str for the tile pill; defaults to rom name/slug.
        self._platform_label = platform_label or (
            lambda rom: rom.platform_name or rom.platform_slug)
```

Replace `set_roms` with (no sidebar; reset filters; populate directly):

```python
    def set_roms(self, roms: list[Rom]) -> None:
        self._roms = roms
        self._selected_ids.clear()
        self._platform_filter = None
        self._downloaded_mode = "all"
        self._sort = "asc"
        self._populate()
```

Delete `current_platform` and `_on_platform`. Replace `filter` and add the new setters:

```python
    def filter(self, query: str) -> None:
        self._query = query
        self._populate()

    def set_platform_filter(self, slug: str | None) -> None:
        self._platform_filter = slug
        self._populate()

    def set_downloaded_filter(self, mode: str) -> None:
        self._downloaded_mode = mode
        self._populate()

    def set_sort(self, order: str) -> None:
        self._sort = order
        self._populate()

    def set_downloaded(self, ids: set[int]) -> None:
        self._downloaded_ids = set(ids)
        self._populate()
```

Change `_populate` to take no platform/query args and use state + the new `filter_games`. Replace its signature and the `games = ...` line:

```python
    def _populate(self) -> None:
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
            del item
        self._checks.clear()
        self._cover_labels = {}
        self._pills = {}
        self._ribbons = {}
        self._cells = []
        games = filter_games(self._roms, self._platform_filter, self._query,
                             self._downloaded_ids, self._downloaded_mode, self._sort)
```

In `__init__`, initialize the new tile-label dicts alongside `_cover_labels`:

```python
        self._cover_labels: dict[int, QLabel] = {}
        self._pills: dict[int, QLabel] = {}
        self._ribbons: dict[int, QLabel] = {}
```

- [ ] **Step 5: Add pill + downloaded indicator to each tile**

Inside `_populate`'s `for rom in games:` loop, after the `cover` QLabel is created and before `check = QCheckBox(rom.name)`, add the pill and (when downloaded) the ribbon + dim, parented to the cover:

```python
            # Platform pill, bottom-left over the cover.
            pill = QLabel(self._platform_label(rom), cover)
            pill.setObjectName("PlatformPill")
            pill.move(4, COVER_HEIGHT - 20)
            self._pills[rom.id] = pill
            if rom.id in self._downloaded_ids:
                cover.setProperty("downloaded", True)
                ribbon = QLabel("DOWNLOADED", cover)
                ribbon.setObjectName("DownloadedRibbon")
                ribbon.setFixedWidth(CELL_WIDTH - 8)
                ribbon.setAlignment(Qt.AlignCenter)
                ribbon.move(0, 0)
                self._ribbons[rom.id] = ribbon
```

(The dim is the QSS in Step 7 keying on the `downloaded` property; the ribbon is the green banner.)

Run: `.venv/bin/python -m pytest tests/test_gui_views.py -v`
Expected: PASS (rewritten tests), once Step 6's indicator tests are also added they pass too.

- [ ] **Step 6: Add indicator tests**

Add to `tests/test_gui_views.py`:

```python
def test_tile_shows_platform_pill(qtbot):
    from romhop.gui.library_view import LibraryView
    view = LibraryView(platform_label=lambda rom: "Game Boy")
    qtbot.addWidget(view)
    view.set_roms([_rom("Tetris", "gb")])
    pill = next(iter(view._pills.values()))
    assert pill.text() == "Game Boy"


def test_downloaded_tile_gets_ribbon_others_do_not(qtbot):
    from romhop.gui.library_view import LibraryView
    view = LibraryView()
    qtbot.addWidget(view)
    a, b = _rom("Sonic", "genesis"), _rom("Mario", "nes")
    view.set_roms([a, b])
    view.set_downloaded({a.id})
    assert a.id in view._ribbons
    assert b.id not in view._ribbons


def test_downloaded_filter_hides_missing(qtbot):
    from romhop.gui.library_view import LibraryView
    view = LibraryView()
    qtbot.addWidget(view)
    a, b = _rom("Sonic", "genesis"), _rom("Mario", "nes")
    view.set_roms([a, b])
    view.set_downloaded({a.id})
    view.set_downloaded_filter("downloaded")
    assert {rom.name for _, rom in view._checks.values()} == {"Sonic"}
```

Run: `.venv/bin/python -m pytest tests/test_gui_views.py -v`
Expected: PASS.

- [ ] **Step 7: Style the pill, ribbon, and dim**

Append to `src/romhop/gui/themes/base.qss`:

```css
#PlatformPill {
    background: rgba(0, 0, 0, 0.6);
    color: #ffffff;
    font-size: 9px;
    padding: 1px 6px;
    border-radius: 8px;
}
#DownloadedRibbon {
    background: #2e9e4f;
    color: #ffffff;
    font-size: 9px;
    padding: 2px 0;
}
#Cover[downloaded="true"] {
    /* dim downloaded covers so the ribbon reads clearly */
    background: rgba(0, 0, 0, 0.45);
}
```

Run: `.venv/bin/python -m pytest tests/test_gui_views.py tests/test_gui_theme.py -v`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add src/romhop/gui/library_view.py src/romhop/gui/themes/base.qss tests/test_gui_views.py
git commit -m "feat(gui): flat grid with platform pill + downloaded indicators"
```

---

### Task 7: `MainWindow` — place filter bar, hide in settings, refresh downloaded set

**Files:**
- Modify: `src/romhop/gui/main_window.py`
- Test: `tests/test_gui_app.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_gui_app.py` (mirror how that file constructs `MainWindow` with providers; minimal stubs shown):

```python
def test_filter_bar_hidden_in_settings_shown_in_library(qtbot):
    from romhop.config import Settings
    from romhop.gui.main_window import MainWindow
    win = MainWindow(Settings(), rom_provider=lambda: [])
    qtbot.addWidget(win)
    win.show()
    qtbot.waitExposed(win)
    assert win.filter_bar.isVisible()
    win.show_settings()
    assert not win.filter_bar.isVisible()
    win.show_library()
    assert win.filter_bar.isVisible()


def test_load_library_populates_filter_platforms_and_downloaded(qtbot, monkeypatch, tmp_path):
    from romhop.config import Settings
    from romhop.gui import main_window
    from romhop.gui.main_window import MainWindow
    from romhop.romm_client import Rom

    rom = Rom(id=1, name="Sonic", platform_slug="genesis", fs_name="Sonic.md",
              fs_name_no_ext="Sonic", file_names=["Sonic.md"], platform_name="Genesis")
    # Pretend Sonic is on disk.
    monkeypatch.setattr(main_window, "downloaded_rom_ids", lambda roms, root, ov: {1})

    win = MainWindow(Settings(roms_root=tmp_path), rom_provider=lambda: [rom])
    qtbot.addWidget(win)
    win.load_library()
    # Platform dropdown got the platform; downloaded set reached the view.
    assert win.filter_bar.platform_combo.itemText(1) == "Genesis"
    assert win.library._downloaded_ids == {1}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_gui_app.py -k "filter_bar or load_library_populates" -v`
Expected: FAIL — `MainWindow` has no `filter_bar`; `downloaded_rom_ids` not imported in `main_window`.

- [ ] **Step 3: Wire the filter bar into `MainWindow`**

In `src/romhop/gui/main_window.py`:

Add imports:

```python
from romhop.gui.filter_bar import FilterBar
from romhop.local_index import downloaded_rom_ids
from romhop.gui.library_view import platforms_from_roms
from romhop.platform_names import display_name
```

In `__init__`, after building `self.library` and before/around the stack, construct the bar and connect it (place this after `self.library = LibraryView(...)`):

```python
        self.filter_bar = FilterBar()
        self.filter_bar.platform_changed.connect(self.library.set_platform_filter)
        self.filter_bar.downloaded_changed.connect(self.library.set_downloaded_filter)
        self.filter_bar.sort_changed.connect(self.library.set_sort)
```

Pass a `platform_label` into the `LibraryView` so pills use the names cache when present. Change the `LibraryView` construction to accept it via app wiring — keep MainWindow's default but allow override through a new `platform_label` kwarg on `MainWindow.__init__` (add `platform_label=None` to the signature and pass it):

```python
    def __init__(self, settings: Settings, parent=None, *,
                 rom_provider=None, download_action=None,
                 sync_watch_fn=None, persist_settings=None, cover_provider=None,
                 platform_label=None):
        ...
        self.library = LibraryView(cover_provider=cover_provider,
                                   platform_label=platform_label)
```

In the main `layout` assembly, insert the filter bar between `top` and the stack:

```python
        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(self.filter_bar)
        layout.addWidget(self.stack, 1)
        layout.addWidget(self.bottom)
```

In `show_settings`, hide the bar; in `show_library`, show it:

```python
    def show_settings(self) -> None:
        self.settings_view.reset()
        self.settings_view.setFocus()
        self.filter_bar.hide()
        self.stack.setCurrentIndex(1)
        self.settings_view.filter(self.search.text())

    def show_library(self) -> None:
        self.filter_bar.show()
        self.stack.setCurrentIndex(0)
        self.library.filter(self.search.text())
```

Replace `load_library` to populate platforms + downloaded set:

```python
    def load_library(self) -> None:
        if self._rom_provider is None:
            return
        roms = self._rom_provider()
        self.library.set_roms(roms)
        pairs = [(slug, self._platform_name_for(roms, slug))
                 for slug in platforms_from_roms(roms)]
        self.filter_bar.set_platforms(pairs)
        self._refresh_downloaded(roms)

    def _platform_name_for(self, roms, slug: str) -> str:
        rom = next((r for r in roms if r.platform_slug == slug), None)
        return display_name(rom) if rom is not None else slug

    def _refresh_downloaded(self, roms=None) -> None:
        roms = roms if roms is not None else getattr(self.library, "_roms", [])
        ids = downloaded_rom_ids(roms, self._settings.roms_root,
                                 self._settings.platform_overrides)
        self.library.set_downloaded(ids)
```

In `_on_batch_finished`, refresh so freshly downloaded games flip style (add before `self.downloads_finished.emit()`):

```python
        self._refresh_downloaded()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_gui_app.py -v`
Expected: PASS (new + existing). If an existing test asserted the old sidebar via MainWindow, update it to the filter-bar equivalent.

- [ ] **Step 5: Commit**

```bash
git add src/romhop/gui/main_window.py tests/test_gui_app.py
git commit -m "feat(gui): filter bar in window, hidden in settings, downloaded refresh"
```

---

### Task 8: Wire the names cache + downloaded label into `app.py`

**Files:**
- Modify: `src/romhop/gui/app.py`
- Test: covered by `tests/test_gui_app.py` (run full suite)

- [ ] **Step 1: Wire `PlatformNames` and `platform_label` in `run()`**

In `src/romhop/gui/app.py`, add imports inside `run()` near the others:

```python
    from romhop.platform_names import PlatformNames, display_name
```

After building `cache`, create the names cache and a label fn:

```python
    names = PlatformNames(Path(platformdirs.user_data_dir("romhop")) / "platform_names.json")

    def platform_label(rom):
        return display_name(rom, names)
```

Update `rom_provider` to warm the names cache on every fetch:

```python
    def rom_provider():
        roms = client.list_roms()
        names.update_from_roms(roms)
        return roms
```

Pass `platform_label` into `MainWindow(...)`:

```python
    window = MainWindow(
        settings=settings,
        rom_provider=rom_provider,
        download_action=download_action,
        sync_watch_fn=sync_watch_fn,
        cover_provider=cover_provider,
        platform_label=platform_label,
    )
```

- [ ] **Step 2: Run the full suite**

Run: `.venv/bin/python -m pytest`
Expected: PASS (all tests).

- [ ] **Step 3: Commit**

```bash
git add src/romhop/gui/app.py
git commit -m "feat(gui): wire platform-name cache into the app"
```

---

### Task 9: Full-suite verification + manual smoke

**Files:** none (verification only)

- [ ] **Step 1: Run the entire test suite**

Run: `.venv/bin/python -m pytest -q`
Expected: all pass, no sidebar references remain (grep to confirm):

```bash
grep -rn "\.sidebar\|current_platform" src/ tests/ || echo "clean"
```
Expected: `clean`.

- [ ] **Step 2: Manual smoke (optional, needs a configured RomM)**

Run: `.venv/bin/python -m romhop gui`
Confirm: no sidebar; filter bar shows Platform/Downloaded/Sort; tiles show platform pills; on-disk games are dimmed with a DOWNLOADED ribbon; entering settings hides the filter bar; downloading a game flips it to downloaded without a reload. And: `romhop download "<ambiguous>"` lists candidates as `<name> - <platform>`.

- [ ] **Step 3: Final commit (if grep/cleanup changed anything)**

```bash
git add -A && git commit -m "chore: remove residual sidebar references"
```

---

## Self-Review

**Spec coverage:**
- Drop sidebar / flat A–Z grid → Task 6 (Steps 2,4) + filter_games sort.
- Filter bar (Platform/Downloaded/Sort), hidden in settings → Tasks 5, 7.
- Tile indicators (pill + dim/ribbon, every view) → Task 6 (Steps 5,7).
- Platform names harvested + persisted, name→cache→slug → Tasks 1, 2; wired 4 (CLI), 8 (GUI).
- Downloaded detection helper + refresh after batch → Tasks 3, 7.
- CLI platform suffix → Task 4.
- Tests for each unit → every task; existing sidebar tests rewritten in Task 6 Step 3.

**Placeholder scan:** none — every code/test step has concrete content.

**Type consistency:** `filter_games(roms, platform, query, downloaded_ids, downloaded_mode, sort)` defined in Task 6 Step 2 and called with the same names in `_populate` (Task 6 Step 4). `set_downloaded`/`set_platform_filter`/`set_downloaded_filter`/`set_sort` defined in Task 6 Step 4 and called in Task 7 connections. `downloaded_rom_ids(roms, roms_root, overrides)` defined in Task 3, imported/called in Task 7. `display_name(rom, names)` defined in Task 2, used in Tasks 4, 7, 8. `PlatformNames.update_from_roms/name_for/save` consistent across Tasks 2, 4, 8. FilterBar signal payloads (`object`/`str`) match Task 5 tests and Task 7 slots.
