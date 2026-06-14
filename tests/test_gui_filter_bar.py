from romhop.gui.filter_bar import FilterBar


def test_platform_combo_defaults_to_all_then_lists_platforms(qtbot):
    bar = FilterBar()
    qtbot.addWidget(bar)
    bar.set_platforms([("gb", "Game Boy"), ("snes", "Super Nintendo")])
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
        bar.downloaded_combo.setCurrentIndex(1)
    assert sig.args == ["downloaded"]


def test_sort_change_emits_order(qtbot):
    bar = FilterBar()
    qtbot.addWidget(bar)
    with qtbot.waitSignal(bar.sort_changed) as sig:
        bar.sort_combo.setCurrentIndex(1)
    assert sig.args == ["desc"]
