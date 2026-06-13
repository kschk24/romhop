import romhop


def test_version_is_exposed():
    assert isinstance(romhop.__version__, str)
    assert romhop.__version__
