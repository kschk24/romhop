from __future__ import annotations

"""Entry-point router for the single frozen executable.

The frozen build ships ONE PyInstaller exe (named ``romhop``) that serves both
frontends: bare launch -> GUI, any other argument -> the Typer CLI. This lets a
frozen per-user install expose the ``romhop`` CLI without a second binary (see
TASK-002). The exe is built ``console=False`` so double-clicking never flashes a
terminal; ``_attach_console_windows`` re-attaches the parent console for CLI
mode so output is still visible from a shell.

Qt-free: GUI/CLI are imported lazily so this module stays importable without the
GUI extra (CLAUDE.md core invariant).
"""

import os
import sys

# Flags consumed by the GUI launch path (gui.app.run); they must NOT trigger CLI
# dispatch even though they look like arguments.
GUI_ONLY_FLAGS = frozenset({"--uninstall", "--appimage-bootstrap", "--smoke-exit"})


def is_cli_invocation(argv: list[str]) -> bool:
    """True if the frozen exe was called as the CLI rather than to launch the GUI."""
    return len(argv) > 1 and argv[1] not in GUI_ONLY_FLAGS


def _attach_console_windows() -> None:
    """Re-attach the parent console on Windows so a console=False exe can print.

    No-op on non-Windows and when there is no parent console (e.g. launched from
    Explorer). Best-effort: any failure leaves streams as-is.
    """
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ATTACH_PARENT_PROCESS = -1
        if not ctypes.windll.kernel32.AttachConsole(ATTACH_PARENT_PROCESS):
            return
        sys.stdout = open("CONOUT$", "w")  # noqa: SIM115 - kept open for process life
        sys.stderr = open("CONOUT$", "w")  # noqa: SIM115
        sys.stdin = open("CONIN$", "r")  # noqa: SIM115
    except OSError:
        pass


def main(argv: list[str] | None = None) -> None:
    argv = sys.argv if argv is None else argv
    if is_cli_invocation(argv):
        _attach_console_windows()
        from romhop.cli import app

        app()
    else:
        # Prevent the bundled libatk-bridge-2.0 from registering with the
        # system AT-SPI2 D-Bus service. The bundled Ubuntu 24.04 build of
        # libatk-bridge can segfault against a different-version system daemon
        # (Fedora, Arch, newer Ubuntu). NO_AT_BRIDGE=1 skips bridge init while
        # leaving Qt's own accessibility intact.
        if sys.platform.startswith("linux"):
            os.environ.setdefault("NO_AT_BRIDGE", "1")
        from romhop.gui.app import run

        run()


if __name__ == "__main__":
    main()
