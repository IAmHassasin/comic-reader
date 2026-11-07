"""Entry point: ``python -m foldervault`` (GUI) or ``python -m foldervault import-meta ...``."""

from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] in ("import-meta", "export-meta", "-h", "--help"):
        from foldervault import cli

        return cli.run(args)

    from foldervault import app

    return app.run(sys.argv[:1] + args)


if __name__ == "__main__":
    sys.exit(main())
