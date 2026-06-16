# packaging/entry.py — frozen executable entry point.
# Routes to GUI (bare launch) or Typer CLI (any args); see romhop.frozen_dispatch.
from __future__ import annotations

from romhop.frozen_dispatch import main

if __name__ == "__main__":
    main()
