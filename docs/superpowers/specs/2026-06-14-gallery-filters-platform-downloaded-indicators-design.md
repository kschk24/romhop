# Gallery filters + platform & downloaded indicators

Date: 2026-06-14
Branch: `gui-desktop-pyside`

## Goal

Make the library easier to navigate and the GUI/CLI more informative:

1. **Drop the platform sidebar.** Default to a single flat, A–Z grid of every
   game across all platforms.
2. **Filter bar** under the search row: `Platform ▾ · Downloaded ▾ · Sort ▾`.
   Visible with the library, hidden when settings is open (the search row stays).
3. **Tile indicators** (style B): a platform pill overlaid on the cover, and for
   already-on-disk games a dimmed cover plus a "DOWNLOADED" ribbon.
4. **Human-friendly platform names** ("Game Boy", not `gb`) sourced from RomM and
   persisted for offline reuse — shared by GUI and CLI.
5. **CLI parity:** the `download` disambiguation list shows the platform, e.g.
   `Super Mario Land 2: 6 Golden Coins - Game Boy`.

This subsumes the original "All category" idea: the default view *is* all
platforms, so no separate entry is needed.

## Non-goals (YAGNI)

- No multi-disc / file-type filter.
- No "already downloaded" flag in the CLI match list (the `download` command
  already reports "Already local" after a game is chosen).
- No grouped-by-platform rendering — the grid stays flat; the pill conveys
  platform.

## Components

### 1. Platform names (new module `romhop/platform_names.py`)

RomM's rom payload carries a display name alongside the slug. We harvest it
whenever we fetch roms, persist a `slug → name` map, and read it back for
display — so names survive offline and are identical in GUI and CLI.

- Add `platform_name: str | None = None` to `Rom`; populate it in
  `RommClient.list_roms` from `item.get("platform_name")`.
  - *Verify at implementation time* that `platform_name` is present in the
    `/api/roms` item payload. If it is not, fetch it once from `GET /api/platforms`
    (`{id, slug, name, …}`) and feed the same cache. The rest of the design is
    unchanged either way.
- `PlatformNames` cache persisted as JSON at
  `platformdirs.user_data_dir("romhop")/platform_names.json` (sibling of
  `mapping_cache.json`):
  - `update_from_roms(roms)` — merge any `slug → platform_name` pairs seen, then
    save. Called after every successful rom fetch (GUI + CLI).
  - `name_for(slug) -> str` — cached name, else the raw slug.
- Display rule everywhere: prefer `rom.platform_name`, else
  `cache.name_for(slug)`, else `slug`.

### 2. Downloaded detection (extend `romhop/local_index.py`)

Reuse the existing local-index match used by `download`/`scan`. Add one helper:

```
downloaded_rom_ids(roms, roms_root, overrides) -> set[int]
```

It walks the local library once (`index_local_library`), builds a set of
`(system, match_key)` from local games, and returns the ids of roms whose
`(esde_system, norm(fs_name))` or `(esde_system, norm(fs_name_no_ext))` is
present. This is the same matching `cli.download` does at the single-rom level,
generalized to the whole set and computed once.

### 3. Filter bar (new widget `FilterBar` in `romhop/gui/filter_bar.py`)

A `QWidget` with three combo boxes and signals:

- **Platform**: "All platforms" + one entry per platform (label = display name,
  data = slug). `set_platforms(pairs)` populates it; selecting emits
  `platform_changed(slug | None)`.
- **Downloaded**: All / Downloaded / Not downloaded → `downloaded_changed(mode)`.
- **Sort**: Name A–Z / Name Z–A → `sort_changed(order)`.

The bar owns no data; it only emits the user's intent. MainWindow places it in
the main layout directly under the search row and toggles its visibility on view
switches.

### 4. `LibraryView` changes

- **Remove** the `QListWidget` sidebar and `_on_platform`; the layout becomes the
  scroll-area grid only.
- New filter state: `_platform_filter: str | None`, `_downloaded_filter: str`
  (`all`/`downloaded`/`missing`), `_sort: str`, plus existing `_query` and a new
  `_downloaded_ids: set[int]`.
- Setters re-run `_populate`: `set_platform_filter`, `set_downloaded_filter`,
  `set_sort`, `set_downloaded(ids)`.
- `set_roms(roms)` no longer builds a sidebar; it stores roms, clears selection
  (unchanged), and resets to defaults (platform=All, downloaded=all, sort=A–Z).
- Generalize the pure filter function:
  `filter_games(roms, platform_or_none, query, downloaded_ids, downloaded_mode, sort)`
  → returns the games to render. Platform `None` means all platforms.
- Tile rendering (`_populate`): add a platform-name pill overlaid on the cover
  (display rule above), and when `rom.id in _downloaded_ids` apply the dimmed
  cover + "DOWNLOADED" ribbon. Pill shows in every view, including single-platform.

### 5. `MainWindow` wiring

- Construct `FilterBar`; add it to the vertical layout between `top` and `stack`.
- `show_settings`: hide the filter bar. `show_library`: show it.
- Connect `FilterBar` signals to the matching `LibraryView` setters.
- `load_library`: after `set_roms`, (a) `platform_names.update_from_roms(roms)`,
  (b) populate `FilterBar.set_platforms` from the roms' slugs + display names,
  (c) compute `downloaded_rom_ids(...)` and call `library.set_downloaded(ids)`.
- After a download batch finishes (`_on_batch_finished`): recompute
  `downloaded_rom_ids` and refresh `library.set_downloaded(ids)` so freshly
  downloaded games flip to the downloaded style without a reload.

### 6. CLI parity (`romhop/cli.py`)

- A small display helper builds `"<name> - <platform display name>"` using the
  same rule (prefer `rom.platform_name`, else the names cache, else slug).
- `_select_match`'s ambiguous-match listing prints each candidate as
  `  Super Mario Land 2: 6 Golden Coins - Game Boy`.
- `download` (and `scan`) call `platform_names.update_from_roms(roms)` after a
  successful fetch so the cache stays warm for both tools.

## Data flow

```
RomM /api/roms ──> list_roms ──> [Rom(... platform_name)]
                                   │
        ┌──────────────────────────┼───────────────────────────┐
        ▼                          ▼                            ▼
 platform_names.update    downloaded_rom_ids(roms,        FilterBar.set_platforms
 (persist slug→name)      roms_root, overrides)           (slug,name pairs)
                                   │
                                   ▼
                          LibraryView.set_downloaded(ids)
                                   │
 FilterBar signals ───────────────┼──> LibraryView setters ──> _populate ──> tiles
 (platform/downloaded/sort)        (pill + dim/ribbon, filtered, sorted)
```

## Error handling

- Offline / unreachable RomM: unchanged — `load_library` already fails soft and
  shows the error in the status area. The persisted name cache means any games
  shown still get proper platform labels.
- Missing `platform_name` in payload: falls back to the names cache, then to the
  raw slug; never errors.
- `downloaded_rom_ids` when `roms_root` is unset/missing: `index_local_library`
  already returns `[]`, so the set is empty (nothing marked downloaded) — no error.

## Testing

- `platform_names`: round-trip persist/load; `update_from_roms` merges new slugs;
  `name_for` falls back to slug for unknown.
- `local_index.downloaded_rom_ids`: roms with/without a local match; respects
  platform overrides; empty when `roms_root` absent.
- `filter_games`: platform=None spans all; platform filter scopes; downloaded
  modes (all/downloaded/missing) using an ids set; sort A–Z and Z–A; query still
  applies and combines with filters.
- `FilterBar`: populating platforms, and that each combo emits the expected
  signal payload.
- `LibraryView`: no sidebar; `set_downloaded` flips tile styling; setters
  re-populate; selection still spans platforms after filtering.
- `MainWindow`: filter bar hidden in settings / shown in library; download-batch
  finish refreshes the downloaded set.
- CLI: `_select_match` ambiguous output includes `- <platform name>`.

## Affected files

- New: `src/romhop/platform_names.py`, `src/romhop/gui/filter_bar.py`,
  `tests/test_platform_names.py`, `tests/test_gui_filter_bar.py`.
- Changed: `romm_client.py` (Rom field + harvest), `local_index.py` (helper),
  `gui/library_view.py` (sidebar removal, filters, indicators),
  `gui/main_window.py` (filter bar + refresh), `gui/app.py` (wire cache +
  downloaded set), `cli.py` (platform suffix + cache update). Tests updated
  alongside.
