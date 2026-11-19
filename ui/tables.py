"""Aides pour les tableaux : tri numérique, alerte de stock (couleur + icône + texte + gras)."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import QAbstractItemView, QHeaderView, QTableWidget, QTableWidgetItem
from ui.icons import icone
from ui.theme import jetons


class NumItem(QTableWidgetItem):
    """Cellule triable selon une valeur numérique."""
    def __init__(self, texte: str, valeur: int):
        super().__init__(texte)
        self.setData(Qt.UserRole, valeur)
        self.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

    def __lt__(self, autre):
        return (self.data(Qt.UserRole) or 0) < (autre.data(Qt.UserRole) or 0)


def texte(t: str) -> QTableWidgetItem:
    it = QTableWidgetItem(t)
    it.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
    return it


def creer_table(colonnes: list[str]) -> QTableWidget:
    t = QTableWidget(0, len(colonnes))
    t.setHorizontalHeaderLabels(colonnes)
    t.verticalHeader().setVisible(False)
    t.verticalHeader().setDefaultSectionSize(40)  # lignes de 40 px minimum
    t.setAlternatingRowColors(True)
    t.setEditTriggers(QAbstractItemView.NoEditTriggers)
    t.setSelectionBehavior(QAbstractItemView.SelectRows)
    t.setSelectionMode(QAbstractItemView.SingleSelection)
    t.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    t.setSortingEnabled(True)
    h = t.horizontalHeader()
    h.setSectionResizeMode(QHeaderView.ResizeToContents)
    h.setSectionResizeMode(0, QHeaderView.Stretch)
    h.setSortIndicatorShown(True)
    return t


def alerte_stock(cellules: list, etat: QTableWidgetItem, item_qte: QTableWidgetItem, quantite: int, seuil: int):
    """Stock faible/épuisé : ligne rouge clair + pastille texte avec icône + quantité en gras."""
    t = jetons()
    gras = QFont(item_qte.font())
    gras.setBold(True)
    if quantite == 0:
        etat.setText("Épuisé")
    elif quantite < seuil:
        etat.setText("Stock faible")
    else:
        etat.setText("En stock")
        return
    etat.setIcon(icone("alerte", t["stock_faible_texte"], 18))
    item_qte.setFont(gras)
    etat.setFont(gras)
    for c in cellules:
        c.setBackground(QColor(t["stock_faible_fond"]))
        c.setForeground(QColor(t["stock_faible_texte"]))
