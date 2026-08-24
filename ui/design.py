"""
Hybrid Design System — Material Design 3 + Apple HIG
"""
import os

from PyQt6.QtGui import QColor, QFont, QPalette
from PyQt6.QtCore import Qt


class DesignTokens:
    """Central design tokens — all visual values live here."""

    # ── Colors (Material Design 3 + Apple) ──────────────────────────────

    class Light:
        PRIMARY = "#1A73E8"          # Google Blue
        PRIMARY_VARIANT = "#1557B0"
        ON_PRIMARY = "#FFFFFF"

        BACKGROUND = "#FAFAFA"       # Apple-like light gray
        SURFACE = "#FFFFFF"
        SURFACE_VARIANT = "#F1F3F4"
        ON_SURFACE = "#202124"
        ON_SURFACE_VARIANT = "#5F6368"

        ERROR = "#D93025"
        SUCCESS = "#1E8E3E"
        WARNING = "#F9AB00"

        RECORD = "#D93025"           # Only red in the app
        OUTLINE = "#DADCE0"
        OUTLINE_VARIANT = "#BDBFBF"
        DIVIDER = "#E8EAED"

        SELECTED_BG = "#E8F0FE"      # light blue selection
        SELECTED_HOVER = "#F1F6FD"
        SELECTED_FG = "#202124"      # dark readable text

    class Dark:
        PRIMARY = "#8AB4F8"          # Lighter blue for dark mode
        PRIMARY_VARIANT = "#669DF6"
        ON_PRIMARY = "#202124"

        BACKGROUND = "#121212"
        SURFACE = "#1E1E1E"
        SURFACE_VARIANT = "#2C2C2C"
        ON_SURFACE = "#E8EAED"
        ON_SURFACE_VARIANT = "#9AA0A6"

        ERROR = "#F28B82"
        SUCCESS = "#81C995"
        WARNING = "#FDD663"

        RECORD = "#F28B82"
        OUTLINE = "#5F6368"
        OUTLINE_VARIANT = "#8A8F98"
        DIVIDER = "#3C4043"

        SELECTED_BG = "#263A5E"      # dark blue selection
        SELECTED_HOVER = "#2E3F63"
        SELECTED_FG = "#E8EAED"

    # ── Typography ──────────────────────────────────────────────────────

    class Fonts:
        SANS = "Segoe UI, SF Pro Display, Roboto, sans-serif"
        MONO = "SF Mono, Consolas, monospace"

        DISPLAY_LARGE = 32
        DISPLAY_MEDIUM = 24
        HEADLINE_LARGE = 20
        HEADLINE_MEDIUM = 16
        TITLE_LARGE = 14
        TITLE_MEDIUM = 13
        BODY_LARGE = 14
        BODY_MEDIUM = 13
        BODY_SMALL = 12
        LABEL_LARGE = 13
        LABEL_MEDIUM = 11
        CAPTION = 10

    # ── Spacing (8pt grid) ─────────────────────────────────────────────

    class Space:
        XS = 4
        SM = 8
        MD = 12
        LG = 16
        XL = 24
        XXL = 32
        XXXL = 48

    # ── Corner Radius (Material Design 3) ──────────────────────────────

    class Radius:
        NONE = 0
        XS = 4
        SM = 8
        MD = 12
        LG = 16
        XL = 24
        FULL = 9999

    # ── Animation ───────────────────────────────────────────────────────

    class Animation:
        FAST = 100      # ms
        MEDIUM = 200    # ms
        SLOW = 300      # ms


def get_palette(is_dark: bool = False) -> QPalette:
    """Generate a QPalette for the application."""
    palette = QPalette()

    if is_dark:
        colors = DesignTokens.Dark
    else:
        colors = DesignTokens.Light

    palette.setColor(QPalette.ColorRole.Window, QColor(colors.BACKGROUND))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(colors.ON_SURFACE))
    palette.setColor(QPalette.ColorRole.Base, QColor(colors.SURFACE))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(colors.SURFACE_VARIANT))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(colors.SURFACE))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(colors.ON_SURFACE))
    palette.setColor(QPalette.ColorRole.Text, QColor(colors.ON_SURFACE))
    palette.setColor(QPalette.ColorRole.Button, QColor(colors.SURFACE))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(colors.ON_SURFACE))
    palette.setColor(QPalette.ColorRole.BrightText, QColor(colors.RECORD))
    palette.setColor(QPalette.ColorRole.Link, QColor(colors.PRIMARY))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(colors.PRIMARY))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(colors.ON_PRIMARY))

    return palette


def get_stylesheet(is_dark: bool = False) -> str:
    """Generate a complete stylesheet for the application."""
    if is_dark:
        c = DesignTokens.Dark
    else:
        c = DesignTokens.Light

    # Absolute path to the checkbox checkmark so QSS url() resolves
    check_img = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "icons", "check_primary.png").replace("\\", "/")

    return f"""
    /* Global */
    QWidget {{
        background-color: {c.BACKGROUND};
        color: {c.ON_SURFACE};
        font-family: {DesignTokens.Fonts.SANS};
        font-size: {DesignTokens.Fonts.BODY_MEDIUM}px;
    }}

    /* Main Window */
    QMainWindow {{
        background-color: {c.BACKGROUND};
    }}

    /* Buttons */
    QPushButton {{
        background-color: {c.SURFACE_VARIANT};
        color: {c.ON_SURFACE};
        border: 1px solid {c.OUTLINE};
        border-radius: {DesignTokens.Radius.SM}px;
        padding: 8px 16px;
        font-weight: 500;
    }}
    QPushButton:hover {{
        background-color: {c.SURFACE};
        border-color: {c.PRIMARY};
    }}
    QPushButton:pressed {{
        background-color: {c.SURFACE_VARIANT};
    }}

    /* Primary Button */
    QPushButton[cssClass="primary"] {{
        background-color: {c.PRIMARY};
        color: {c.ON_PRIMARY};
        border: none;
        border-radius: {DesignTokens.Radius.FULL}px;
        padding: 12px 24px;
        font-weight: 600;
    }}
    QPushButton[cssClass="primary"]:hover {{
        background-color: {c.PRIMARY_VARIANT};
    }}

    /* Record Button (FAB) */
    QPushButton[cssClass="record"] {{
        background-color: {c.PRIMARY};
        color: {c.ON_PRIMARY};
        border: none;
        border-radius: 60px;
        min-width: 120px;
        min-height: 120px;
        font-size: 14px;
        font-weight: 600;
    }}
    QPushButton[cssClass="record"]:hover {{
        background-color: {c.PRIMARY_VARIANT};
    }}
    QPushButton[cssClass="record"][recording="true"] {{
        background-color: {c.RECORD};
    }}

    /* Text Input */
    QLineEdit, QTextEdit, QComboBox {{
        background-color: {c.SURFACE};
        color: {c.ON_SURFACE};
        border: 1px solid {c.OUTLINE};
        border-radius: {DesignTokens.Radius.SM}px;
        padding: 8px 12px;
        min-height: 22px;
        selection-background-color: {c.PRIMARY};
    }}
    QLineEdit:focus, QTextEdit:focus, QComboBox:focus {{
        border-color: {c.PRIMARY};
    }}

    /* Labels */
    QLabel {{
        color: {c.ON_SURFACE};
        background: transparent;
    }}
    QLabel[cssClass="caption"] {{
        color: {c.ON_SURFACE_VARIANT};
        font-size: {DesignTokens.Fonts.CAPTION}px;
    }}
    QLabel[cssClass="title"] {{
        font-size: {DesignTokens.Fonts.TITLE_LARGE}px;
        font-weight: 600;
    }}

    /* Tabs */
    QTabWidget::pane {{
        border: 1px solid {c.OUTLINE};
        border-radius: {DesignTokens.Radius.SM}px;
        background: {c.SURFACE};
    }}
    QTabBar::tab {{
        background: transparent;
        padding: 8px 16px;
        border-bottom: 2px solid transparent;
    }}
    QTabBar::tab:selected {{
        border-bottom-color: {c.PRIMARY};
        color: {c.PRIMARY};
    }}

    /* ScrollBar */
    QScrollBar:vertical {{
        background: transparent;
        width: 8px;
    }}
    QScrollBar::handle:vertical {{
        background: {c.OUTLINE};
        border-radius: 4px;
        min-height: 20px;
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    QScrollBar:horizontal {{
        background: transparent;
        height: 8px;
    }}
    QScrollBar::handle:horizontal {{
        background: {c.OUTLINE};
        border-radius: 4px;
        min-width: 20px;
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0px;
    }}
    QScrollBar::handle:hover {{
        background: {c.OUTLINE_VARIANT};
    }}

    /* List selection — readable (light blue bg + dark text) */
    QListWidget::item:selected, QListView::item:selected {{
        background: {c.SELECTED_BG};
        color: {c.SELECTED_FG};
        border-radius: {DesignTokens.Radius.XS}px;
    }}
    QListWidget::item:hover, QListView::item:hover {{
            background: {c.SELECTED_HOVER};
            border-radius: {DesignTokens.Radius.XS}px;
        }}

        /* Make inner containers borderless/transparent so the rounded
           QTabWidget pane corners show (no square borders overlapping) */
        QScrollArea, QListWidget, QListView, QPlainTextEdit, QTextBrowser {{
            border: none;
            background: transparent;
        }}
        QScrollArea > QWidget QWidget {{
            background: transparent;
        }}

    /* CheckBox — blue outline (consistent with radio) */
        QCheckBox {{
            spacing: 8px;
            background: transparent;
        }}
        QCheckBox::indicator {{
            width: 18px;
            height: 18px;
            border-radius: 4px;
            border: 2px solid {c.OUTLINE};
            background: transparent;
        }}
        QCheckBox::indicator:hover {{
            border-color: {c.PRIMARY};
        }}
        QCheckBox::indicator:checked {{
            border: 2px solid {c.PRIMARY};
            background: #E8F0FE;
            image: url({check_img});
        }}

    /* Radio Button (fix invisible-on-select in wizards) */
    QRadioButton {{
        spacing: 8px;
        color: {c.ON_SURFACE};
        background: transparent;
    }}
    QRadioButton::indicator {{
        width: 18px;
        height: 18px;
        border-radius: 9px;
        border: 2px solid {c.OUTLINE};
        background: {c.SURFACE};
    }}
    QRadioButton::indicator:hover {{
        border-color: {c.PRIMARY};
    }}
    QRadioButton::indicator:checked {{
        border: 5px solid {c.PRIMARY};
        background: {c.SURFACE};
    }}
    QRadioButton:checked {{
        color: {c.ON_SURFACE};
        font-weight: 600;
    }}

    /* ComboBox */
    QComboBox {{
        background-color: {c.SURFACE};
        border: 1px solid {c.OUTLINE};
        border-radius: {DesignTokens.Radius.SM}px;
        padding: 6px 12px;
    }}
    QComboBox:hover {{
        border-color: {c.PRIMARY};
    }}
    QComboBox::drop-down {{
        border: none;
    }}
    QComboBox QAbstractItemView {{
        background-color: {c.SURFACE};
        color: {c.ON_SURFACE};
        border: 1px solid {c.OUTLINE};
        border-radius: {DesignTokens.Radius.SM}px;
        padding: 2px;
        selection-background-color: {c.PRIMARY};
        selection-color: {c.ON_PRIMARY};
        outline: none;
    }}
    QComboBox QAbstractItemView::item {{
        min-height: 26px;
        padding: 4px 8px;
        color: {c.ON_SURFACE};
    }}
    QComboBox QAbstractItemView::item:selected {{
        background: {c.PRIMARY};
        color: {c.ON_PRIMARY};
        border-radius: {DesignTokens.Radius.XS}px;
    }}
    """
