from __future__ import annotations


def test_second_instance_activates_first(qtbot):
    from romhop.gui.single_instance import SingleInstance

    primary = SingleInstance(key="romhop-test-activate")
    primary.listen()
    second = SingleInstance(key="romhop-test-activate")
    # is_running() on the second must connect to the first and trigger its
    # `activated` signal (this is the "raise the existing window" path).
    with qtbot.waitSignal(primary.activated, timeout=2000):
        assert second.is_running() is True
    qtbot.wait(50)
    primary.close()


def test_first_instance_is_not_running(qtbot):
    from romhop.gui.single_instance import SingleInstance

    inst = SingleInstance(key="romhop-test-first")
    # No server listening on this key yet -> the gate reports we are first.
    assert inst.is_running() is False
    inst.close()


def test_listen_clears_stale_server(qtbot):
    from PySide6.QtNetwork import QLocalServer
    from romhop.gui.single_instance import SingleInstance

    # Simulate a socket left behind by a crashed instance.
    QLocalServer.removeServer("romhop-test-stale")
    orphan = QLocalServer()
    orphan.listen("romhop-test-stale")
    # A fresh instance must still be able to claim the key.
    inst = SingleInstance(key="romhop-test-stale")
    inst.listen()
    assert inst._server.isListening() is True
    inst.close()
    orphan.close()
