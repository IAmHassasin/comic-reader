"""GUI bootstrap: logging, QApplication, theme, database, main window."""

from __future__ import annotations

import logging
import sqlite3
import sys
import traceback
from logging.handlers import RotatingFileHandler
from types import TracebackType

from . import __version__, config

log = logging.getLogger("foldervault")


def setup_logging() -> None:
    handler = RotatingFileHandler(
        config.logs_dir() / "app.log", maxBytes=1_000_000, backupCount=5, encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)


def _install_excepthook() -> None:
    def hook(exc_type: type[BaseException], exc: BaseException, tb: TracebackType | None) -> None:
        log.critical("Unhandled exception", exc_info=(exc_type, exc, tb))
        try:
            from PySide6.QtWidgets import QApplication, QMessageBox

            if QApplication.instance() is not None:
                box = QMessageBox(
                    QMessageBox.Icon.Critical,
                    "FolderVault",
                    "An unexpected error occurred. Details were written to the log.",
                )
                box.setDetailedText("".join(traceback.format_exception(exc_type, exc, tb)))
                box.exec()
        except Exception:  # noqa: BLE001 - never raise from the excepthook
            log.exception("Failed to show the error dialog")

    sys.excepthook = hook


def run(argv: list[str]) -> int:
    setup_logging()
    _install_excepthook()
    log.info("Starting FolderVault %s", __version__)

    from PySide6.QtCore import Qt
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtWidgets import QApplication, QMessageBox

    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(argv)
    app.setApplicationName(config.APP_NAME)
    app.setApplicationVersion(__version__)
    app.setStyle("Fusion")  # QSS renders consistently on Fusion; the system font is kept

    from .data.db import connect
    from .data.repository import Repository
    from .ui.main_window import MainWindow
    from .ui.settings import Preferences
    from .ui.theme import tokens
    from .ui.theme.qss import build_palette, build_qss

    try:
        conn = connect(config.db_path())
    except sqlite3.Error as exc:
        log.exception("Cannot open the database")
        QMessageBox.critical(None, "FolderVault", f"Cannot open the library database:\n{exc}")
        return 1

    repo = Repository(conn)
    theme = tokens.build_theme(Preferences.load(repo).accent_base())
    tokens.set_current(theme)
    from .ui.theme import icons

    app.setWindowIcon(icons.icon("folder", theme.accent))
    app.setPalette(build_palette(theme))
    app.setStyleSheet(build_qss(theme))

    window = MainWindow(repo)
    window.show()
    code = app.exec()
    conn.close()
    log.info("Exited with code %d", code)
    return code
