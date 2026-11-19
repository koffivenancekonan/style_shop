"""Page Stock en lecture seule (gestionnaire) : aucune donnée d'achat, lecture via la vue MySQL."""
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication, QComboBox, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QVBoxLayout, QWidget
from database.connexion import ErreurBaseDeDonnees
from services import articles
from ui.icons import icone
from ui.tables import NumItem, alerte_stock, creer_table, texte
from ui.theme import jetons
from utils.format import nombre

COLONNES = ["Article", "Catégorie", "Taille / couleur", "Prix de vente (FCFA)", "Stock", "État"]


class PageStock(QWidget):
    def __init__(self):
        super().__init__()
        t = jetons()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(12)
        titre = QLabel("Stock disponible")
        titre.setProperty("role", "titre")
        lay.addWidget(titre)
        f = QHBoxLayout()
        self.recherche = QLineEdit()
        self.recherche.setPlaceholderText("Rechercher par nom, marque ou catégorie")
        self.recherche.setAccessibleName("Rechercher un article")
        self.recherche.setClearButtonEnabled(True)
        self.recherche.addAction(icone("recherche", t["texte2"], 18), QLineEdit.LeadingPosition)
        self.categorie = QComboBox()
        self.categorie.setAccessibleName("Filtrer par catégorie")
        self.categorie.setMinimumWidth(220)
        self.lbl_nb = QLabel()
        self.lbl_nb.setProperty("role", "aide")
        f.addWidget(self.recherche, 1)
        f.addWidget(self.categorie)
        f.addWidget(self.lbl_nb)
        lay.addLayout(f)
        self.table = creer_table(COLONNES)
        lay.addWidget(self.table, 1)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(200)
        self._timer.timeout.connect(self.rafraichir)
        self.recherche.textChanged.connect(lambda _: self._timer.start())
        self.categorie.currentIndexChanged.connect(lambda _: self.rafraichir())
        self._charger_categories()

    def _charger_categories(self):
        self.categorie.blockSignals(True)
        self.categorie.clear()
        self.categorie.addItem("Toutes les catégories", None)
        try:
            for c in articles.categories():
                self.categorie.addItem(c, c)
        except ErreurBaseDeDonnees:
            pass
        self.categorie.blockSignals(False)

    def showEvent(self, e):
        super().showEvent(e)
        self.recherche.setFocus()
        self.rafraichir()

    def rafraichir(self):
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            seuil = articles.seuil()
            lignes = articles.lister_vendeur(self.recherche.text(), self.categorie.currentData())
        except ErreurBaseDeDonnees as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "Stock", str(e))
            return
        QApplication.restoreOverrideCursor()
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(lignes))
        for r, a in enumerate(lignes):
            c_qte = NumItem(str(a["quantite_stock"]), a["quantite_stock"])
            c_etat = texte("")
            cellules = [texte(f"{a['nom']} ({a['marque']})"), texte(a["categorie"]),
                        texte(f"{a['taille']} / {a['couleur']}"),
                        NumItem(nombre(a["prix_vente"]), a["prix_vente"]), c_qte, c_etat]
            alerte_stock(cellules, c_etat, c_qte, a["quantite_stock"], seuil)
            for c, it in enumerate(cellules):
                self.table.setItem(r, c, it)
        self.table.setSortingEnabled(True)
        n = len(lignes)
        self.lbl_nb.setText("Aucun article trouvé" if n == 0 else f"{n} article{'s' if n > 1 else ''}")
