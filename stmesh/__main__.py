"""Allow `python -m stmesh` to launch the app."""

from .app import main

if __name__ == "__main__":
    raise SystemExit(main())
