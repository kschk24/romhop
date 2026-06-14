from pathlib import Path

from romhop.pull import PullItem, resolve_target


def _item(kind="save", file_name="Sonic.srm", emulator="genesis"):
    return PullItem(kind=kind, rom_id=1, file_name=file_name, emulator=emulator,
                    remote_updated="2026-06-01T10:00:00", data=b"X")


def test_existing_file_found_in_place(tmp_path):
    saves = tmp_path / "saves"
    existing = saves / "Snes9x" / "Sonic.srm"
    existing.parent.mkdir(parents=True)
    existing.write_bytes(b"old")
    target = resolve_target(_item(), saves, tmp_path / "states",
                            sort_saves_by_core=False, sort_states_by_core=False)
    assert target == existing


def test_existing_file_with_bracket_tag_found(tmp_path):
    # ROM/save names use [..] dump tags; rglob must match them literally.
    saves = tmp_path / "saves"
    existing = saves / "Pokemon [!].srm"
    existing.parent.mkdir(parents=True)
    existing.write_bytes(b"old")
    item = _item(file_name="Pokemon [!].srm")
    target = resolve_target(item, saves, tmp_path / "states",
                            sort_saves_by_core=False, sort_states_by_core=False)
    assert target == existing


def test_new_flat_when_sort_off(tmp_path):
    saves = tmp_path / "saves"
    saves.mkdir()
    target = resolve_target(_item(), saves, tmp_path / "states",
                            sort_saves_by_core=False, sort_states_by_core=False)
    assert target == saves / "Sonic.srm"


def test_new_per_core_when_sort_on(tmp_path):
    saves = tmp_path / "saves"
    saves.mkdir()
    target = resolve_target(_item(emulator="genesis"), saves, tmp_path / "states",
                            sort_saves_by_core=True, sort_states_by_core=False)
    assert target == saves / "genesis" / "Sonic.srm"


def test_new_sort_on_but_no_emulator_falls_back_flat(tmp_path):
    saves = tmp_path / "saves"
    saves.mkdir()
    target = resolve_target(_item(emulator=None), saves, tmp_path / "states",
                            sort_saves_by_core=True, sort_states_by_core=False)
    assert target == saves / "Sonic.srm"


def test_state_uses_states_dir_and_flag(tmp_path):
    states = tmp_path / "states"
    states.mkdir()
    item = _item(kind="state", file_name="Sonic.state1", emulator="genesis")
    target = resolve_target(item, tmp_path / "saves", states,
                            sort_saves_by_core=False, sort_states_by_core=True)
    assert target == states / "genesis" / "Sonic.state1"
