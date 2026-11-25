"""Warm parchment Light theme & obsidian Dark theme matching Wispr Flow tokens."""

from __future__ import annotations

LIGHT_PALETTE = {
    "name": "light",
    "outer_bg": "#F5F4F0",
    "canvas_bg": "#FCFCFB",
    "canvas_border": "#E9E7E0",
    "card_bg": "#EEEBE3",
    "card_bg_alt": "#F4F2EC",
    "card_border": "#E4E0D6",
    "item_bg": "#FFFFFF",
    "item_hover": "#F8F7F4",
    "nav_active_bg": "#EAE8E1",
    "nav_hover_bg": "#ECEAE4",
    "text_primary": "#1C1917",
    "text_secondary": "#57534E",
    "text_muted": "#8C8982",
    "accent_cta": "#FFA946",
    "accent_cta_hover": "#F29932",
    "accent_cta_border": "#262320",
    "accent_cta_text": "#1C1917",
    "lavender_bg": "#EFE5FC",
    "lavender_hover": "#E6D6FA",
    "lavender_text": "#571B83",
    "teal_bg": "#E2F5F2",
    "teal_text": "#034F46",
    "danger_bg": "#FEE2E2",
    "danger_text": "#B91C1C",
    "input_bg": "#FFFFFF",
    "input_border": "#DEDAD0",
    "divider": "#E3E0D7",
    "icon_color": "#262320",
}

DARK_PALETTE = {
    "name": "dark",
    "outer_bg": "#151514",
    "canvas_bg": "#1D1D1B",
    "canvas_border": "#2B2A27",
    "card_bg": "#242320",
    "card_bg_alt": "#282724",
    "card_border": "#33312D",
    "item_bg": "#242320",
    "item_hover": "#2D2C28",
    "nav_active_bg": "#2D2C28",
    "nav_hover_bg": "#242320",
    "text_primary": "#F7F6F2",
    "text_secondary": "#C4C0B7",
    "text_muted": "#8B877E",
    "accent_cta": "#FFA946",
    "accent_cta_hover": "#F29932",
    "accent_cta_border": "#FFA946",
    "accent_cta_text": "#181512",
    "lavender_bg": "#3A2252",
    "lavender_hover": "#4B2B6B",
    "lavender_text": "#E8D1FF",
    "teal_bg": "#123832",
    "teal_text": "#84CDC1",
    "danger_bg": "#451A1A",
    "danger_text": "#FCA5A5",
    "input_bg": "#171715",
    "input_border": "#383631",
    "divider": "#312F2B",
    "icon_color": "#F0EFEA",
}


def get_palette(theme_name: str) -> dict[str, str]:
    return DARK_PALETTE if theme_name == "dark" else LIGHT_PALETTE


def build_stylesheet(p: dict[str, str]) -> str:
    return f"""
    QWidget {{
        font-family: "Segoe UI", "Inter", sans-serif;
        color: {p['text_primary']};
        font-size: 13px;
    }}
    QMainWindow, QWidget#RootFrame {{
        background-color: {p['outer_bg']};
    }}
    QFrame#TopBar {{
        background-color: {p['outer_bg']};
        border: none;
    }}
    QFrame#Sidebar {{
        background-color: {p['outer_bg']};
        border: none;
    }}
    QFrame#MainCanvas {{
        background-color: {p['canvas_bg']};
        border: 1px solid {p['canvas_border']};
        border-top-left-radius: 16px;
        border-top-right-radius: 12px;
        border-bottom-left-radius: 12px;
        border-bottom-right-radius: 12px;
    }}
    QFrame#RightCard {{
        background-color: {p['card_bg']};
        border: 1px solid {p['card_border']};
        border-radius: 14px;
    }}
    QFrame#SoftCard {{
        background-color: {p['card_bg_alt']};
        border: 1px solid {p['card_border']};
        border-radius: 12px;
    }}
    QFrame#SurfaceCard {{
        background-color: {p['item_bg']};
        border: 1px solid {p['card_border']};
        border-radius: 12px;
    }}
    QFrame#Divider {{
        background-color: {p['divider']};
        max-height: 1px;
        min-height: 1px;
    }}
    QPushButton#NavBtn {{
        background-color: transparent;
        border: none;
        border-radius: 10px;
        padding: 8px 10px;
        text-align: left;
        color: {p['text_secondary']};
        font-size: 13px;
        font-weight: 500;
    }}
    QPushButton#NavBtn:hover {{
        background-color: {p['nav_hover_bg']};
        color: {p['text_primary']};
    }}
    QPushButton#NavBtn[active="true"] {{
        background-color: {p['nav_active_bg']};
        color: {p['text_primary']};
        font-weight: 600;
    }}
    QPushButton#IconBtn {{
        background-color: transparent;
        border: none;
        border-radius: 8px;
        padding: 5px;
    }}
    QPushButton#IconBtn:hover {{
        background-color: {p['nav_hover_bg']};
    }}
    QPushButton#WinCtrlBtn {{
        background-color: transparent;
        border: none;
        border-radius: 6px;
        font-size: 13px;
        color: {p['text_primary']};
        min-width: 32px;
        min-height: 28px;
    }}
    QPushButton#WinCtrlBtn:hover {{
        background-color: {p['nav_hover_bg']};
    }}
    QPushButton#WinCloseBtn {{
        background-color: transparent;
        border: none;
        border-radius: 6px;
        font-size: 14px;
        color: {p['text_primary']};
        min-width: 32px;
        min-height: 28px;
    }}
    QPushButton#WinCloseBtn:hover {{
        background-color: #E5484D;
        color: #FFFFFF;
    }}
    QPushButton#LavenderPill {{
        background-color: {p['lavender_bg']};
        color: {p['lavender_text']};
        border: none;
        border-radius: 8px;
        padding: 6px 14px;
        font-size: 12.5px;
        font-weight: 600;
    }}
    QPushButton#LavenderPill:hover {{
        background-color: {p['lavender_hover']};
    }}
    QPushButton#AmberCTA {{
        background-color: {p['accent_cta']};
        color: {p['accent_cta_text']};
        border: 1px solid {p['accent_cta_border']};
        border-radius: 8px;
        padding: 9px 16px;
        font-size: 13px;
        font-weight: 600;
    }}
    QPushButton#AmberCTA:hover {{
        background-color: {p['accent_cta_hover']};
    }}
    QPushButton#SecondaryBtn {{
        background-color: {p['item_bg']};
        color: {p['text_primary']};
        border: 1px solid {p['input_border']};
        border-radius: 8px;
        padding: 7px 14px;
        font-size: 12.5px;
        font-weight: 500;
    }}
    QPushButton#SecondaryBtn:hover {{
        background-color: {p['item_hover']};
    }}
    QPushButton#GhostBtn {{
        background-color: transparent;
        color: {p['text_secondary']};
        border: none;
        border-radius: 6px;
        padding: 4px 8px;
        font-size: 12px;
    }}
    QPushButton#GhostBtn:hover {{
        background-color: {p['nav_hover_bg']};
        color: {p['text_primary']};
    }}
    QPushButton#RecordBtn {{
        background-color: #1C1917;
        color: #FFFFEB;
        border: none;
        border-radius: 9px;
        padding: 7px 14px;
        font-size: 12.5px;
        font-weight: 600;
    }}
    QPushButton#RecordBtn:hover {{
        background-color: #332E2B;
    }}
    QPushButton#RecordBtn[recording="true"] {{
        background-color: #DC2626;
        color: #FFFFFF;
    }}
    QLineEdit, QTextEdit, QPlainTextEdit, QComboBox {{
        background-color: {p['input_bg']};
        color: {p['text_primary']};
        border: 1px solid {p['input_border']};
        border-radius: 8px;
        padding: 7px 10px;
        font-size: 13px;
    }}
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus {{
        border: 1.5px solid {p['lavender_text']};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 24px;
    }}
    QCheckBox {{
        spacing: 8px;
        color: {p['text_primary']};
    }}
    QScrollArea {{
        border: none;
        background-color: {p['canvas_bg']};
    }}
    QScrollArea > QWidget, QScrollArea > QWidget > QWidget {{
        background-color: {p['canvas_bg']};
    }}
    QStackedWidget {{
        background-color: {p['canvas_bg']};
    }}
    QTabWidget::pane {{
        background-color: {p['item_bg']};
        border: 1px solid {p['card_border']};
        border-radius: 10px;
        padding: 4px;
    }}
    QTabBar::tab {{
        background-color: {p['card_bg_alt']};
        color: {p['text_secondary']};
        border: 1px solid {p['card_border']};
        border-bottom: none;
        border-top-left-radius: 8px;
        border-top-right-radius: 8px;
        padding: 7px 14px;
        margin-right: 4px;
        font-weight: 500;
    }}
    QTabBar::tab:selected {{
        background-color: {p['item_bg']};
        color: {p['text_primary']};
        font-weight: 600;
    }}
    QComboBox QAbstractItemView {{
        background-color: {p['item_bg']};
        color: {p['text_primary']};
        border: 1px solid {p['input_border']};
        selection-background-color: {p['lavender_bg']};
        selection-color: {p['lavender_text']};
        outline: none;
    }}
    QLabel {{
        background-color: transparent;
    }}
    QCheckBox {{
        background-color: transparent;
    }}
    QScrollBar:vertical {{
        background: transparent;
        width: 7px;
        margin: 2px;
    }}
    QScrollBar::handle:vertical {{
        background: {p['input_border']};
        border-radius: 3px;
        min-height: 28px;
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    QLabel#PageTitle {{
        font-size: 24px;
        font-weight: 600;
        color: {p['text_primary']};
    }}
    QLabel#SectionTitle {{
        font-size: 15px;
        font-weight: 600;
        color: {p['text_primary']};
    }}
    QLabel#MutedLabel {{
        color: {p['text_muted']};
        font-size: 12px;
    }}
    QLabel#SecondaryLabel {{
        color: {p['text_secondary']};
        font-size: 12.5px;
    }}
    QLabel#BadgeTeal {{
        background-color: {p['teal_bg']};
        color: {p['teal_text']};
        border-radius: 6px;
        padding: 3px 8px;
        font-size: 11px;
        font-weight: 600;
    }}
    QLabel#BadgeLavender {{
        background-color: {p['lavender_bg']};
        color: {p['lavender_text']};
        border-radius: 6px;
        padding: 3px 8px;
        font-size: 11px;
        font-weight: 600;
    }}
    """
