import emusync


def test_version_is_exposed():
    assert isinstance(emusync.__version__, str)
    assert emusync.__version__
