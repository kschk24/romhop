import pytest

from romhop.gui import workers


def test_callable_worker_emits_result(qtbot):
    w = workers.CallableWorker(lambda: 2 + 3)
    with qtbot.waitSignal(w.done, timeout=2000) as blocker:
        w.start()
    assert blocker.args == [5]


def test_callable_worker_emits_error(qtbot):
    def boom():
        raise ValueError("nope")

    w = workers.CallableWorker(boom)
    with qtbot.waitSignal(w.error, timeout=2000) as blocker:
        w.start()
    assert "nope" in blocker.args[0]
