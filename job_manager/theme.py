"""Design tokens and shared stylesheet for the Job Manager UI.

Every colour and the shared stylesheet live here so all dialogs agree and
edits happen in one place.  The stylesheet uses ``palette()`` roles wherever
possible -- it adapts to light *and* dark mode without branching -- and only
reaches for a fixed hex when a specific accent is wanted.

Dark-mode note: ``setStyleSheet`` on a widget that already has one will *not*
re-read the palette after the system switches themes.  Widgets that need a
dynamic accent colour (e.g. the status bar counter) must override
``changeEvent`` and re-apply their colour there instead of locking it in
at construction time.
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject
from PySide6.QtGui import QColor, QPalette

# ---------------------------------------------------------------------------
# State colours -- imported by jobs_dialog and status_widget
# ---------------------------------------------------------------------------

#: Green for RUNNING / busy.
CY_GREEN = "#00e676"
#: Red for FAILED / BLOCKED.
CY_RED = "#ff2d55"
#: Amber for PENDING / warnings.
CY_AMBER = "#ffb700"
#: Teal for DONE.
CY_TEAL = "#14b8a6"
#: Purple for LOST.
CY_PURPLE = "#c77dff"
#: Neutral grey for QUEUED.
CY_GREY = "#8898aa"

# ---------------------------------------------------------------------------
# Accent colours for the UI chrome
# ---------------------------------------------------------------------------

#: Primary blue accent.
CY_ACCENT = "#2979ff"
#: Secondary blue accent.
CY_ACCENT2 = "#1565c0"

# ---------------------------------------------------------------------------
# Shared dialog stylesheet
# ---------------------------------------------------------------------------

# The stylesheet is applied to the top-level dialog widget.  Children inherit
# it unless they override it themselves.  Every ``palette(...)`` reference
# resolves through Qt's current palette, so dark-mode users get dark surfaces
# and light-mode users get light ones.  Fixed hex appears only for the blue
# accent that is the same in both modes, and only on interactive states
# (hover, focus, selection) -- resting widgets use palette() and look natural.

_STYLESHEET_TEMPLATE = f"""
/* --- secondary text: hints, counts, status lines ------------------------- */

QLabel[muted="true"] {{
    color: @MUTED@;
}}

/* --- push buttons --------------------------------------------------------- */

QToolBar {{
    border: none;
    padding: 0px;
    spacing: 6px;
}}

QPushButton, QToolButton[jobManagerAction="true"] {{
    background: palette(button);
    color: palette(button-text);
    border: 1px solid palette(mid);
    border-radius: 5px;
    padding: 5px 14px;
    min-height: 20px;
}}

QPushButton:hover, QToolButton[jobManagerAction="true"]:hover {{
    background: rgba(41, 121, 255, 0.12);
    border-color: {CY_ACCENT};
    color: {CY_ACCENT};
}}

QPushButton:pressed, QToolButton[jobManagerAction="true"]:pressed {{
    background: rgba(41, 121, 255, 0.22);
    border-color: {CY_ACCENT};
}}

QPushButton:disabled, QToolButton[jobManagerAction="true"]:disabled {{
    color: @DISABLED@;
    border-color: palette(mid);
}}

QPushButton:checked, QToolButton[jobManagerAction="true"]:checked {{
    background: rgba(41, 121, 255, 0.15);
    border-color: {CY_ACCENT};
    color: {CY_ACCENT};
}}

/* --- table ---------------------------------------------------------------- */

QTableView {{
    gridline-color: transparent;
    border: 1px solid palette(mid);
    border-radius: 6px;
    alternate-background-color: palette(alternate-base);
    selection-background-color: rgba(41, 121, 255, 0.28);
    selection-color: palette(text);
    outline: none;
}}

QTableView::item {{
    padding: 2px 6px;
    border: none;
}}

QHeaderView::section {{
    background: palette(button);
    color: @MUTED@;
    border: none;
    border-bottom: 1px solid palette(mid);
    padding: 4px 8px;
}}

/* --- tree ----------------------------------------------------------------- */

QTreeWidget {{
    border: 1px solid palette(mid);
    border-radius: 6px;
    outline: none;
}}

QTreeWidget::item:selected {{
    background: rgba(41, 121, 255, 0.28);
    color: palette(text);
}}

QTreeWidget::item:hover:!selected {{
    background: rgba(41, 121, 255, 0.08);
}}

/* --- text/plain edit ------------------------------------------------------ */

QPlainTextEdit, QTextEdit {{
    background: palette(base);
    color: palette(text);
    border: 1px solid palette(mid);
    border-radius: 6px;
    padding: 4px;
}}

QPlainTextEdit:focus, QTextEdit:focus {{
    border-color: {CY_ACCENT2};
}}

/* --- line edit ------------------------------------------------------------ */

QLineEdit {{
    background: palette(base);
    color: palette(text);
    border: 1px solid palette(mid);
    border-radius: 4px;
    padding: 3px 6px;
    min-height: 20px;
}}

QLineEdit:focus {{
    border-color: {CY_ACCENT2};
}}

QLineEdit:disabled {{
    color: @DISABLED@;
    background: palette(window);
}}

/* --- spin box ------------------------------------------------------------- */

QSpinBox {{
    background: palette(base);
    color: palette(text);
    border: 1px solid palette(mid);
    border-radius: 4px;
    padding: 2px 20px 2px 4px;
    min-height: 22px;
}}

QSpinBox:focus {{
    border-color: {CY_ACCENT2};
}}

QSpinBox::up-button {{
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 18px;
}}

QSpinBox::down-button {{
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    width: 18px;
}}

QSpinBox:disabled {{
    color: @DISABLED@;
    background: palette(window);
}}

/* --- combo box ------------------------------------------------------------ */

QComboBox {{
    background: palette(base);
    color: palette(text);
    border: 1px solid palette(mid);
    border-radius: 4px;
    padding: 3px 6px;
    min-height: 20px;
}}

QComboBox:focus {{
    border-color: {CY_ACCENT2};
}}

QComboBox:disabled {{
    color: @DISABLED@;
    background: palette(window);
}}

QComboBox QAbstractItemView {{
    background: palette(base);
    border: 1px solid {CY_ACCENT2};
    selection-background-color: rgba(41, 121, 255, 0.28);
}}

/* --- group box ------------------------------------------------------------ */

QGroupBox {{
    border: 1px solid palette(mid);
    border-radius: 6px;
    margin-top: 10px;
    padding-top: 6px;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
    color: @MUTED@;
}}

/* --- list widget ---------------------------------------------------------- */

QListWidget {{
    background: palette(base);
    border: 1px solid palette(mid);
    border-radius: 6px;
    outline: none;
}}

QListWidget::item:selected {{
    background: rgba(41, 121, 255, 0.28);
    color: palette(text);
}}

QListWidget::item:hover:!selected {{
    background: rgba(41, 121, 255, 0.08);
}}

/* --- scroll bars ---------------------------------------------------------- */

QScrollBar:vertical {{
    background: transparent;
    width: 7px;
    margin: 0;
}}

QScrollBar::handle:vertical {{
    background: palette(mid);
    border-radius: 3px;
    min-height: 24px;
}}

QScrollBar::handle:vertical:hover {{
    background: {CY_ACCENT2};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}

QScrollBar:horizontal {{
    background: transparent;
    height: 7px;
    margin: 0;
}}

QScrollBar::handle:horizontal {{
    background: palette(mid);
    border-radius: 3px;
    min-width: 24px;
}}

QScrollBar::handle:horizontal:hover {{
    background: {CY_ACCENT2};
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}

/* --- dialog button box ---------------------------------------------------- */

QDialogButtonBox QPushButton {{
    min-width: 72px;
}}

/* --- splitter ------------------------------------------------------------- */

QSplitter::handle {{
    background: palette(mid);
}}

QSplitter::handle:horizontal {{ width: 1px; }}
QSplitter::handle:vertical   {{ height: 1px; }}

/* --- scroll area ---------------------------------------------------------- */

QScrollArea {{
    border: none;
}}
"""

#: Used when no palette is at hand. Mid-greys that read on light and dark surfaces.
_FALLBACK_MUTED = "#767676"
_FALLBACK_DISABLED = "#8c8c8c"


def _blend(palette: QPalette, weight: float) -> str:
    """Window text mixed toward the window colour; *weight* is the text's share."""
    text = palette.color(QPalette.ColorRole.WindowText)
    back = palette.color(QPalette.ColorRole.Window)
    mix = QColor(
        round(text.red() * weight + back.red() * (1 - weight)),
        round(text.green() * weight + back.green() * (1 - weight)),
        round(text.blue() * weight + back.blue() * (1 - weight)),
    )
    return mix.name()


def disabled_text_color(palette: QPalette) -> str:
    """Fainter than muted text so a disabled control still looks disabled."""
    return _blend(palette, 0.4)


def muted_text_color(palette: QPalette) -> str:
    """Secondary text: the window text blended 60/40 toward the window colour.

    ``palette(mid)`` was used for this, but it is a border shade, not a text
    colour. Under Fusion -- the default style on Linux -- it is #b8b8b8 on a
    white or #efefef surface, and hints, header labels and group titles all
    but vanished. A blend keeps the same contrast direction in light and
    dark palettes alike.
    """
    return _blend(palette, 0.6)


def dialog_stylesheet(palette: QPalette = None) -> str:
    """The shared stylesheet, with secondary text matched to *palette*."""
    if palette is None:
        muted, disabled = _FALLBACK_MUTED, _FALLBACK_DISABLED
    else:
        muted, disabled = muted_text_color(palette), disabled_text_color(palette)
    return _STYLESHEET_TEMPLATE.replace("@MUTED@", muted).replace("@DISABLED@", disabled)


DIALOG_STYLESHEET = dialog_stylesheet()


__all__ = [
    "CY_GREEN",
    "CY_RED",
    "CY_AMBER",
    "CY_TEAL",
    "CY_PURPLE",
    "CY_GREY",
    "CY_ACCENT",
    "CY_ACCENT2",
    "DIALOG_STYLESHEET",
    "apply_theme",
    "dialog_stylesheet",
    "disabled_text_color",
    "mark_muted",
    "muted_text_color",
]


def _sheet_for(widget) -> str:
    from PySide6.QtWidgets import QApplication

    return dialog_stylesheet(QApplication.palette(widget))


class ThemeWatcher(QObject):
    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.PaletteChange:
            sheet = _sheet_for(obj)
            if obj.styleSheet() != sheet:
                obj.setStyleSheet(sheet)
        return False


_theme_watcher = None


def apply_theme(widget) -> None:
    """Apply DIALOG_STYLESHEET and re-apply it on system theme changes."""
    global _theme_watcher
    if _theme_watcher is None:
        _theme_watcher = ThemeWatcher()
    widget.setStyleSheet(_sheet_for(widget))
    widget.installEventFilter(_theme_watcher)


def mark_muted(label) -> None:
    """Show *label* as secondary text, in the themed dialog's muted colour."""
    label.setProperty("muted", True)
    style = label.style()
    style.unpolish(label)
    style.polish(label)
