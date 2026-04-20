"""STMesh main window — Adobe AE Mesh Warp preset builder."""

from __future__ import annotations

import os
import re
import sys
import traceback
from dataclasses import dataclass

from PySide6.QtCore import (
    QEasingCurve, QObject, QPropertyAnimation, QSize, Qt, QThread,
    Signal,
)
from PySide6.QtGui import QAction, QFont, QIcon, QKeySequence, QPixmap
from PySide6.QtWidgets import (
    QApplication, QComboBox, QFileDialog, QFrame, QHBoxLayout, QLabel,
    QLineEdit, QMainWindow, QMessageBox, QPlainTextEdit, QProgressBar,
    QPushButton, QSizePolicy, QStatusBar, QVBoxLayout, QWidget,
)

from . import __app_name__, __version__
from . import core, theme


def _icon_path() -> str | None:
    """Locate the app icon whether running from source or a PyInstaller bundle."""
    candidates = []
    base = getattr(sys, "_MEIPASS", None)  # PyInstaller extraction dir
    if base:
        candidates.append(os.path.join(base, "assets", "stmesh.ico"))
        candidates.append(os.path.join(base, "assets", "stmesh.png"))
    here = os.path.dirname(os.path.abspath(__file__))
    candidates.append(os.path.join(here, "..", "assets", "stmesh.ico"))
    candidates.append(os.path.join(here, "..", "assets", "stmesh.png"))
    for p in candidates:
        if p and os.path.isfile(p):
            return p
    return None


# ---------------------------------------------------------------------------
# Reusable UI atoms
# ---------------------------------------------------------------------------

def _section_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("sectionTitle")
    return lbl


def _field_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("fieldLabel")
    return lbl


def _helper(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("helper")
    lbl.setWordWrap(True)
    return lbl


def _make_card() -> QFrame:
    card = QFrame()
    card.setObjectName("card")
    card.setFrameShape(QFrame.NoFrame)
    return card


class FileField(QWidget):
    """A labelled line-edit + browse button for picking a single file."""

    changed = Signal(str)

    def __init__(self, label: str, helper: str, browse_text: str = "Browse",
                 file_filter: str = "All files (*.*)",
                 parent: QWidget | None = None):
        super().__init__(parent)
        self._filter = file_filter

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)

        head = QHBoxLayout()
        head.setSpacing(8)
        head.addWidget(_field_label(label))
        head.addStretch(1)
        lay.addLayout(head)

        row = QHBoxLayout()
        row.setSpacing(8)

        self.edit = QLineEdit()
        self.edit.setPlaceholderText("No file selected")
        self.edit.textChanged.connect(self.changed)
        row.addWidget(self.edit, 1)

        self.browse = QPushButton(browse_text)
        self.browse.setObjectName("ghost")
        self.browse.clicked.connect(self._browse)
        row.addWidget(self.browse, 0)

        lay.addLayout(row)
        lay.addWidget(_helper(helper))

    def value(self) -> str:
        return self.edit.text().strip()

    def set_value(self, v: str) -> None:
        self.edit.setText(v)

    def _browse(self) -> None:
        start = os.path.dirname(self.value()) if self.value() else ""
        path, _ = QFileDialog.getOpenFileName(
            self, "Select file", start, self._filter)
        if path:
            self.edit.setText(path)


class DirField(QWidget):
    """A labelled line-edit + browse button for picking a directory."""

    changed = Signal(str)

    def __init__(self, label: str, helper: str,
                 parent: QWidget | None = None):
        super().__init__(parent)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)

        lay.addWidget(_field_label(label))

        row = QHBoxLayout()
        row.setSpacing(8)

        self.edit = QLineEdit()
        self.edit.setPlaceholderText("Choose a folder")
        self.edit.textChanged.connect(self.changed)
        row.addWidget(self.edit, 1)

        self.browse = QPushButton("Browse")
        self.browse.setObjectName("ghost")
        self.browse.clicked.connect(self._browse)
        row.addWidget(self.browse, 0)

        lay.addLayout(row)
        lay.addWidget(_helper(helper))

    def value(self) -> str:
        return self.edit.text().strip()

    def set_value(self, v: str) -> None:
        self.edit.setText(v)

    def _browse(self) -> None:
        start = self.value() or ""
        path = QFileDialog.getExistingDirectory(self, "Select folder", start)
        if path:
            self.edit.setText(path)


# ---------------------------------------------------------------------------
# Export worker (runs off the GUI thread)
# ---------------------------------------------------------------------------

@dataclass
class ExportRequest:
    shot_name: str
    export_dir: str
    undistort_stmap: str
    distort_stmap: str
    grid_res: int


class ExportWorker(QObject):
    log = Signal(str)
    finished = Signal(object)  # ExportResult on success, None on failure
    failed = Signal(str)

    def __init__(self, req: ExportRequest):
        super().__init__()
        self._req = req

    def run(self) -> None:
        try:
            result = core.export_presets(
                shot_name=self._req.shot_name,
                export_dir=self._req.export_dir,
                undistort_stmap=self._req.undistort_stmap,
                distort_stmap=self._req.distort_stmap,
                grid_res=self._req.grid_res,
                log=lambda msg: self.log.emit(msg),
            )
        except Exception as exc:  # noqa: BLE001
            self.log.emit("ERROR: " + str(exc))
            self.log.emit(traceback.format_exc())
            self.failed.emit(str(exc))
            return
        self.finished.emit(result)


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------

_SHOT_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.\-]*$")
EXR_FILTER = "OpenEXR STMap (*.exr);;All files (*.*)"


class MainWindow(QMainWindow):

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"{__app_name__} - AE Mesh Warp Preset Builder")
        self.setMinimumSize(780, 880)
        self.resize(900, 960)

        icon = _icon_path()
        if icon:
            self.setWindowIcon(QIcon(icon))

        self._thread: QThread | None = None
        self._worker: ExportWorker | None = None

        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(28, 24, 28, 20)
        root.setSpacing(18)

        # Header
        root.addLayout(self._build_header())

        # Shot + output card (fixed height so its fields never get squashed)
        shot_card = self._build_shot_card()
        shot_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        root.addWidget(shot_card)

        # STMap card (fixed height)
        stmap_card = self._build_stmap_card()
        stmap_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        root.addWidget(stmap_card)

        # Action bar (fixed height)
        action_bar = self._build_action_bar()
        action_bar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        root.addWidget(action_bar)

        # Log card absorbs all remaining vertical space
        log_card = self._build_log_card()
        log_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        root.addWidget(log_card, 1)

        # Status bar
        self.status = QStatusBar(self)
        self.setStatusBar(self.status)
        self.status.showMessage("Ready.")

        self._wire_validation()

        self.setStyleSheet(theme.STYLE)

    # ---- Sections ----

    def _build_header(self) -> QVBoxLayout:
        col = QVBoxLayout()
        col.setSpacing(2)

        title = QLabel(__app_name__)
        title.setObjectName("title")
        col.addWidget(title)

        subtitle = QLabel(
            "Build Adobe After Effects Mesh Warp .ffx presets from 32-bit "
            "STMap EXRs."
        )
        subtitle.setObjectName("subtitle")
        col.addWidget(subtitle)
        return col

    def _build_shot_card(self) -> QFrame:
        card = _make_card()
        lay = QVBoxLayout(card)
        lay.setContentsMargins(20, 18, 20, 20)
        lay.setSpacing(14)

        lay.addWidget(_section_label("Shot"))

        name_row = QVBoxLayout()
        name_row.setSpacing(6)
        name_row.addWidget(_field_label("Shot name"))
        self.shot_edit = QLineEdit()
        self.shot_edit.setPlaceholderText("e.g. ABC_0100")
        name_row.addWidget(self.shot_edit)
        name_row.addWidget(_helper(
            "Used as the output folder and preset filename prefix. "
            "Letters, numbers, underscore, dot, and hyphen only."
        ))
        lay.addLayout(name_row)

        self.export_dir = DirField(
            "Export location",
            "The folder that will contain "
            "<shot>_AE_mesh_warp_presets/.",
        )
        lay.addWidget(self.export_dir)

        return card

    def _build_stmap_card(self) -> QFrame:
        card = _make_card()
        lay = QVBoxLayout(card)
        lay.setContentsMargins(20, 18, 20, 20)
        lay.setSpacing(14)

        head = QHBoxLayout()
        head.addWidget(_section_label("STMaps"))
        head.addStretch(1)

        head.addWidget(_field_label("Grid"))
        self.grid_combo = QComboBox()
        for r in core.VALID_GRID_RES:
            self.grid_combo.addItem(f"{r} x {r}", userData=r)
        self.grid_combo.setCurrentIndex(
            list(core.VALID_GRID_RES).index(core.DEFAULT_GRID_RES))
        self.grid_combo.setToolTip(
            "Mesh resolution. Must match one of AE's supported sizes."
        )
        head.addWidget(self.grid_combo)

        lay.addLayout(head)

        self.undistort_field = FileField(
            "Undistort STMap",
            "32-bit EXR that maps distorted pixels to their undistorted "
            "positions.",
            file_filter=EXR_FILTER,
        )
        lay.addWidget(self.undistort_field)

        self.distort_field = FileField(
            "Distort STMap",
            "32-bit EXR that re-applies lens distortion "
            "(a.k.a. redistort).",
            file_filter=EXR_FILTER,
        )
        lay.addWidget(self.distort_field)

        return card

    def _build_action_bar(self) -> QWidget:
        wrap = QWidget()
        row = QHBoxLayout(wrap)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(10)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)  # indeterminate when visible
        self.progress.setVisible(False)
        self.progress.setMaximumWidth(220)
        row.addWidget(self.progress)

        row.addStretch(1)

        self.reveal_btn = QPushButton("Open output folder")
        self.reveal_btn.setObjectName("ghost")
        self.reveal_btn.setEnabled(False)
        self.reveal_btn.clicked.connect(self._on_reveal)
        row.addWidget(self.reveal_btn)

        self.export_btn = QPushButton("Export presets")
        self.export_btn.setObjectName("primary")
        self.export_btn.setEnabled(False)
        self.export_btn.clicked.connect(self._on_export)
        row.addWidget(self.export_btn)

        return wrap

    def _build_log_card(self) -> QFrame:
        card = _make_card()
        lay = QVBoxLayout(card)
        lay.setContentsMargins(20, 14, 20, 18)
        lay.setSpacing(8)

        head = QHBoxLayout()
        head.addWidget(_section_label("Log"))
        head.addStretch(1)
        clear = QPushButton("Clear")
        clear.setObjectName("ghost")
        clear.clicked.connect(lambda: self.log_view.clear())
        head.addWidget(clear)
        lay.addLayout(head)

        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setPlaceholderText("Output from the exporter will appear here.")
        self.log_view.setMinimumHeight(120)
        lay.addWidget(self.log_view)

        return card

    # ---- Behaviour ----

    def _wire_validation(self) -> None:
        self.shot_edit.textChanged.connect(self._revalidate)
        self.export_dir.changed.connect(self._revalidate)
        self.undistort_field.changed.connect(self._revalidate)
        self.distort_field.changed.connect(self._revalidate)
        self._revalidate()

    def _revalidate(self) -> None:
        shot = self.shot_edit.text().strip()
        shot_ok = bool(_SHOT_NAME_RE.match(shot)) if shot else False

        export_dir = self.export_dir.value()
        dir_ok = bool(export_dir) and os.path.isdir(export_dir)

        u = self.undistort_field.value()
        d = self.distort_field.value()
        files_ok = (
            bool(u) and bool(d)
            and os.path.isfile(u) and os.path.isfile(d)
            and u.lower().endswith(".exr") and d.lower().endswith(".exr")
        )

        self.export_btn.setEnabled(shot_ok and dir_ok and files_ok)

        if shot and not shot_ok:
            self.status.showMessage(
                "Shot name may only contain letters, numbers, underscore, "
                "dot, and hyphen.")
        elif export_dir and not dir_ok:
            self.status.showMessage("Export location is not a valid folder.")
        elif u and not u.lower().endswith(".exr"):
            self.status.showMessage("Undistort STMap must be a .exr file.")
        elif d and not d.lower().endswith(".exr"):
            self.status.showMessage("Distort STMap must be a .exr file.")
        else:
            self.status.showMessage("Ready." if self.export_btn.isEnabled()
                                    else "Fill in the fields above to export.")

    def _append_log(self, msg: str) -> None:
        self.log_view.appendPlainText(msg)

    # ---- Export flow ----

    def _on_export(self) -> None:
        if self._thread is not None:
            return

        req = ExportRequest(
            shot_name=self.shot_edit.text().strip(),
            export_dir=self.export_dir.value(),
            undistort_stmap=self.undistort_field.value(),
            distort_stmap=self.distort_field.value(),
            grid_res=int(self.grid_combo.currentData()),
        )

        self.export_btn.setEnabled(False)
        self.reveal_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.status.showMessage("Exporting…")
        self._append_log(f"--- Export: {req.shot_name} ---")

        thread = QThread(self)
        worker = ExportWorker(req)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.log.connect(self._append_log)
        worker.finished.connect(self._on_export_finished)
        worker.failed.connect(self._on_export_failed)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._on_thread_cleanup)
        self._thread = thread
        self._worker = worker
        thread.start()

    def _on_export_finished(self, result) -> None:
        self._last_output_dir = result.output_dir
        self.reveal_btn.setEnabled(True)
        self.progress.setVisible(False)
        self.export_btn.setEnabled(True)
        self.status.showMessage(f"Wrote {len(result.ffx_paths)} preset(s).")
        self._append_log(f"Output: {result.output_dir}")

    def _on_export_failed(self, message: str) -> None:
        self.progress.setVisible(False)
        self.export_btn.setEnabled(True)
        self.status.showMessage("Export failed.")
        QMessageBox.critical(self, "Export failed", message)

    def _on_thread_cleanup(self) -> None:
        self._thread = None
        self._worker = None

    def _on_reveal(self) -> None:
        path = getattr(self, "_last_output_dir", None)
        if not path or not os.path.isdir(path):
            return
        _open_in_file_manager(path)


def _open_in_file_manager(path: str) -> None:
    if sys.platform.startswith("win"):
        os.startfile(path)  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        import subprocess
        subprocess.Popen(["open", path])
    else:
        import subprocess
        subprocess.Popen(["xdg-open", path])


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName(__app_name__)
    app.setApplicationDisplayName(__app_name__)
    app.setApplicationVersion(__version__)
    app.setOrganizationName("STMesh")
    icon = _icon_path()
    if icon:
        app.setWindowIcon(QIcon(icon))

    # On Windows, set an explicit AppUserModelID so the taskbar groups
    # our icon (and not the generic python.exe one) when running from
    # source or the frozen .exe.
    if sys.platform.startswith("win"):
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "STMesh.App")
        except Exception:
            pass

    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
