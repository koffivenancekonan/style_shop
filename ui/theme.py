"""Jetons de couleurs (clair/sombre) et feuille de style QSS. Aucune couleur écrite ailleurs."""

CLAIR = {
    "fond": "#F8FAFC", "carte": "#FFFFFF", "bordure": "#CBD5E1",
    "texte": "#0F172A", "texte2": "#475569",
    "primaire": "#0F172A", "texte_primaire": "#FFFFFF",
    "accent": "#0F766E", "texte_accent": "#FFFFFF",
    "succes": "#15803D", "avertissement": "#B45309", "danger": "#B91C1C",
    "stock_faible_fond": "#FEE2E2", "stock_faible_texte": "#7F1D1D",
}
SOMBRE = {
    "fond": "#0B1220", "carte": "#111827", "bordure": "#334155",
    "texte": "#F1F5F9", "texte2": "#94A3B8",
    "primaire": "#020617", "texte_primaire": "#FFFFFF",
    "accent": "#2DD4BF", "texte_accent": "#04201C",
    "succes": "#4ADE80", "avertissement": "#FBBF24", "danger": "#F87171",
    "stock_faible_fond": "#450A0A", "stock_faible_texte": "#FECACA",
}
RAYON = 8  # px
_actuel = CLAIR


def definir_theme(nom: str) -> None:
    global _actuel
    _actuel = SOMBRE if nom == "sombre" else CLAIR


def charger_preference() -> str:
    """Thème choisi sur cet ordinateur (stocké localement, lisible avant la connexion)."""
    from PySide6.QtCore import QSettings
    return str(QSettings("StyleShop", "PortBouet").value("theme", "clair"))


def enregistrer_preference(nom: str) -> None:
    from PySide6.QtCore import QSettings
    QSettings("StyleShop", "PortBouet").setValue("theme", nom)


def jetons() -> dict:
    return _actuel


def generer_qss(t: dict | None = None) -> str:
    t = t or _actuel
    return f"""
* {{ font-family: "Nunito Sans", "Segoe UI", sans-serif; font-size: 15px; }}
QWidget {{ background: {t['fond']}; color: {t['texte']}; }}
QDialog {{ background: {t['carte']}; }}
QLabel {{ background: transparent; }}
QToolTip {{ background: {t['primaire']}; color: {t['texte_primaire']}; border: 1px solid {t['bordure']}; padding: 4px; }}
QLabel[role="titre"] {{ font-family: "Rubik", "Segoe UI", sans-serif; font-size: 22px; font-weight: 600; }}
QLabel[role="section"] {{ font-family: "Rubik", "Segoe UI", sans-serif; font-size: 16px; font-weight: 600; }}
QLabel[role="aide"] {{ color: {t['texte2']}; font-size: 14px; }}
QLabel[role="erreur"] {{ color: {t['danger']}; font-size: 14px; }}
QLabel[role="succes"] {{ color: {t['succes']}; font-size: 14px; font-weight: 600; }}
QLabel[role="alerte"] {{ color: {t['avertissement']}; font-size: 14px; }}
QLabel[role="montant"] {{ font-size: 24px; font-weight: 700; }}
QLineEdit, QComboBox {{ background: {t['carte']}; border: 1px solid {t['bordure']}; border-radius: {RAYON}px;
             padding: 8px 12px; min-height: 28px; }}
QLineEdit:hover, QComboBox:hover {{ border-color: {t['texte2']}; }}
QLineEdit:focus, QComboBox:focus {{ border: 2px solid {t['accent']}; padding: 7px 11px; }}
QLineEdit[invalide="true"], QComboBox[invalide="true"] {{ border: 2px solid {t['danger']}; padding: 7px 11px; }}
QComboBox QAbstractItemView {{ background: {t['carte']}; selection-background-color: {t['accent']};
             selection-color: {t['texte_accent']}; }}
QPushButton {{ background: {t['carte']}; border: 1px solid {t['bordure']}; border-radius: {RAYON}px;
               padding: 8px 16px; min-height: 28px; min-width: 44px; }}
QPushButton:hover {{ border-color: {t['accent']}; }}
QPushButton:focus {{ border: 2px solid {t['accent']}; }}
QPushButton[role="accent"] {{ background: {t['accent']}; color: {t['texte_accent']}; border: none; font-weight: 600; }}
QPushButton[role="accent"]:hover {{ background: {t['succes']}; }}
QPushButton[role="danger"] {{ background: {t['danger']}; color: {t['texte_primaire']}; border: none; font-weight: 600; }}
QPushButton:disabled {{ background: {t['bordure']}; color: {t['texte2']}; border: none; }}
QLabel[role="total"] {{ font-family: "Rubik", "Segoe UI", sans-serif; font-size: 34px; font-weight: 700; }}
QPushButton[chip="true"] {{ border-radius: 18px; padding: 6px 14px; min-height: 32px; }}
QPushButton[chip="true"]:checked {{ background: {t['accent']}; color: {t['texte_accent']}; border: none; font-weight: 600; }}
QFrame[carte="true"] {{ background: {t['carte']}; border: 1px solid {t['bordure']}; border-radius: {RAYON}px; }}
QFrame[carte="true"] QLabel {{ border: none; }}
QSpinBox {{ background: {t['carte']}; border: 1px solid {t['bordure']}; border-radius: {RAYON}px; padding: 4px 8px; font-weight: 700; font-size: 17px; }}
QSpinBox:focus {{ border: 2px solid {t['accent']}; }}
QListWidget {{ background: {t['carte']}; border: 1px solid {t['bordure']}; border-radius: {RAYON}px; }}
QListWidget:focus {{ border: 2px solid {t['accent']}; }}
QListWidget::item {{ border-bottom: 1px solid {t['bordure']}; }}
QListWidget::item:selected {{ background: {t['fond']}; }}
QDateEdit {{ background: {t['carte']}; border: 1px solid {t['bordure']}; border-radius: {RAYON}px; padding: 8px 12px; min-height: 28px; }}
QDateEdit:focus {{ border: 2px solid {t['accent']}; padding: 7px 11px; }}
QTabWidget::pane {{ border: 1px solid {t['bordure']}; border-radius: {RAYON}px; background: {t['carte']}; top: -1px; }}
QTabBar::tab {{ background: transparent; padding: 10px 18px; min-height: 24px; border-bottom: 3px solid transparent; }}
QTabBar::tab:hover {{ border-bottom: 3px solid {t['bordure']}; }}
QTabBar::tab:selected {{ font-weight: 600; border-bottom: 3px solid {t['accent']}; }}
QTabBar::tab:focus {{ border: 2px solid {t['accent']}; }}
QFrame#menu {{ background: {t['primaire']}; }}
QFrame#menu QLabel {{ color: {t['texte_primaire']}; }}
QFrame#menu QLabel[role="aide"] {{ color: {t['bordure']}; }}
QPushButton[menu="true"] {{ background: transparent; color: {t['texte_primaire']}; border: none;
               text-align: left; padding: 12px 16px; min-height: 44px; }}
QPushButton[menu="true"]:hover {{ background: {t['texte2']}; }}
QPushButton[menu="true"]:checked {{ background: {t['accent']}; color: {t['texte_accent']}; font-weight: 600; }}
QPushButton[menu="true"]:focus {{ border: 2px solid {t['texte_primaire']}; }}
QTableWidget {{ background: {t['carte']}; alternate-background-color: {t['fond']};
               border: 1px solid {t['bordure']}; border-radius: {RAYON}px; gridline-color: {t['bordure']}; }}
QTableWidget::item {{ padding: 0 8px; }}
QTableWidget::item:selected {{ background: {t['accent']}; color: {t['texte_accent']}; }}
QHeaderView::section {{ background: {t['fond']}; color: {t['texte']}; padding: 8px; border: 0;
               border-bottom: 1px solid {t['bordure']}; font-weight: 600; }}
"""
