"""Module 1 : catalogue des articles (administrateur uniquement)."""
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (QApplication, QComboBox, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
                               QPushButton, QVBoxLayout, QWidget)
from database.connexion import ErreurBaseDeDonnees
from services import articles
from services.auth import AccesRefuse
from ui.form_article import DialogArticle
from ui.icons import icone
from ui.tables import NumItem, alerte_stock, creer_table, texte
from ui.theme import jetons
from ui.widgets import confirmer
from utils.format import nombre

COLONNES = ["Article", "Catégorie", "Taille / couleur", "Achat (FCFA)", "Vente (FCFA)", "Bénéfice (FCFA)", "Stock", "État"]


def _bouton(texte_b, nom_icone, couleur, action, role=None):
    b = QPushButton(" " + texte_b)
    b.setIcon(icone(nom_icone, couleur, 18))
    b.setCursor(Qt.PointingHandCursor)
    b.setAccessibleName(texte_b)
    if role:
        b.setProperty("role", role)
    b.clicked.connect(action)
    return b


class PageCatalogue(QWidget):
    def __init__(self):
        super().__init__()
        t = jetons()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(12)
        titre = QLabel("Catalogue")
        titre.setProperty("role", "titre")
        haut = QHBoxLayout()
        haut.addWidget(titre)
        haut.addStretch(1)
        self.btn_ajout = _bouton("Ajouter un article", "plus", t["texte_accent"], self._ajouter, "accent")
        self.btn_ajout.setToolTip("Ajouter un nouvel article au catalogue")
        haut.addWidget(self.btn_ajout)
        lay.addLayout(haut)

        filtres = QHBoxLayout()
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
        filtres.addWidget(self.recherche, 1)
        filtres.addWidget(self.categorie)
        filtres.addWidget(self.lbl_nb)
        lay.addLayout(filtres)

        self.table = creer_table(COLONNES)
        self.table.doubleClicked.connect(self._modifier)
        lay.addWidget(self.table, 1)

        bas = QHBoxLayout()
        bas.addStretch(1)
        self.btn_modif = _bouton("Modifier", "modifier", t["texte"], self._modifier)
        self.btn_modif.setToolTip("Modifier l'article sélectionné (ou double-clic)")
        self.btn_suppr = _bouton("Supprimer", "supprimer", t["texte"], self._supprimer)
        self.btn_suppr.setToolTip("Supprimer l'article sélectionné (touche Suppr)")
        bas.addWidget(self.btn_modif)
        bas.addWidget(self.btn_suppr)
        lay.addLayout(bas)

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(200)
        self._timer.timeout.connect(self.rafraichir)
        self.recherche.textChanged.connect(lambda _: self._timer.start())
        self.categorie.currentIndexChanged.connect(lambda _: self.rafraichir())
        self.table.itemSelectionChanged.connect(self._maj_boutons)
        sc = QShortcut(QKeySequence(Qt.Key_Delete), self.table)
        sc.setContext(Qt.WidgetWithChildrenShortcut)
        sc.activated.connect(self._supprimer)
        self._charger_categories()
        self._maj_boutons()

    def showEvent(self, e):
        super().showEvent(e)
        self.recherche.setFocus()
        self.rafraichir()

    def _charger_categories(self):
        courant = self.categorie.currentData()
        self.categorie.blockSignals(True)
        self.categorie.clear()
        self.categorie.addItem("Toutes les catégories", None)
        try:
            for c in articles.categories():
                self.categorie.addItem(c, c)
        except ErreurBaseDeDonnees:
            pass
        i = self.categorie.findData(courant)
        self.categorie.setCurrentIndex(max(i, 0))
        self.categorie.blockSignals(False)

    def _selection(self):
        lignes = self.table.selectionModel().selectedRows()
        return self.table.item(lignes[0].row(), 0).data(Qt.UserRole + 1) if lignes else None

    def _maj_boutons(self):
        actif = self._selection() is not None
        self.btn_modif.setEnabled(actif)
        self.btn_suppr.setEnabled(actif)

    def rafraichir(self):
        QApplication.setOverrideCursor(Qt.WaitCursor)  # chargement visible
        try:
            seuil = articles.seuil()
            lignes = articles.lister_admin(self.recherche.text(), self.categorie.currentData())
        except (ErreurBaseDeDonnees, AccesRefuse) as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "Catalogue", str(e))
            return
        QApplication.restoreOverrideCursor()
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(lignes))
        for r, a in enumerate(lignes):
            benef = articles.benefice_unitaire(a["prix_vente"], a["prix_achat_reel"])
            c0 = texte(f"{a['nom']} ({a['marque']})")
            c0.setData(Qt.UserRole + 1, a)
            c_qte = NumItem(str(a["quantite_stock"]), a["quantite_stock"])
            c_etat = texte("")
            cellules = [c0, texte(a["categorie"]), texte(f"{a['taille']} / {a['couleur']}"),
                        NumItem(nombre(a["prix_achat_reel"]), a["prix_achat_reel"]),
                        NumItem(nombre(a["prix_vente"]), a["prix_vente"]),
                        NumItem(nombre(benef), benef), c_qte, c_etat]
            alerte_stock(cellules, c_etat, c_qte, a["quantite_stock"], seuil)
            for c, it in enumerate(cellules):
                self.table.setItem(r, c, it)
        self.table.setSortingEnabled(True)
        n = len(lignes)
        self.lbl_nb.setText(f"{n} article{'s' if n > 1 else ''}")
        if n == 0:
            self.lbl_nb.setText("Aucun article trouvé")
        self._maj_boutons()

    def _ajouter(self):
        if DialogArticle(self).exec():
            self._charger_categories()
            self.rafraichir()

    def _modifier(self, *_):
        a = self._selection()
        if a and DialogArticle(self, a).exec():
            self._charger_categories()
            self.rafraichir()

    def _supprimer(self):
        a = self._selection()
        if not a:
            return
        try:
            vendu = articles.a_ete_vendu(a["id"])
        except (ErreurBaseDeDonnees, AccesRefuse) as e:
            QMessageBox.critical(self, "Suppression impossible", str(e))
            return
        if vendu:
            msg = (f"« {a['nom']} » a déjà été vendu. Il sera archivé (retiré du catalogue) "
                   "pour conserver l'historique des ventes et des bénéfices.")
            bouton = "Archiver l'article"
        else:
            msg = f"Voulez-vous supprimer définitivement « {a['nom']} » ? Cette action est irréversible."
            bouton = "Supprimer l'article"
        if not confirmer(self, "Confirmation", msg, bouton):
            return
        try:
            articles.supprimer(a["id"])
        except (ErreurBaseDeDonnees, AccesRefuse) as e:
            QMessageBox.critical(self, "Suppression impossible", str(e))
            return
        self._charger_categories()
        self.rafraichir()
