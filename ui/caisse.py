"""Module 2 : caisse (ventes), optimisée pour la vitesse. Administrateur et gestionnaire."""
from datetime import datetime
from pathlib import Path
from PySide6.QtCore import QEvent, QTimer, QUrl, Qt
from PySide6.QtGui import QDesktopServices, QKeySequence, QShortcut
from PySide6.QtWidgets import (QApplication, QButtonGroup, QDialog, QFileDialog, QFrame, QGridLayout,
                               QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMessageBox,
                               QPushButton, QSpinBox, QVBoxLayout, QWidget)
from database.connexion import ErreurBaseDeDonnees
from services import articles, recu as recu_pdf, ventes
from services.auth import AccesRefuse
from services.panier import ErreurPanier, Panier
from ui.icons import icone
from ui.tables import NumItem, alerte_stock, creer_table, texte
from ui.theme import jetons
from ui.widgets import confirmer
from utils.format import format_fcfa, nombre


def _bouton_icone(nom_icone: str, nom_acc: str, info: str) -> QPushButton:
    b = QPushButton()
    b.setIcon(icone(nom_icone, jetons()["texte"], 20))
    b.setMinimumSize(44, 44)  # zone cliquable minimale
    b.setCursor(Qt.PointingHandCursor)
    b.setAccessibleName(nom_acc)
    b.setToolTip(info)
    return b


class LigneWidget(QWidget):
    """Une ligne du panier : nom, boutons - / +, sous-total, retrait."""
    def __init__(self, ligne, id_, moins, plus, retirer):
        super().__init__()
        self.setObjectName("ligne")
        self.setStyleSheet("#ligne { background: transparent; }")
        a = ligne["article"]
        v = QVBoxLayout(self)
        v.setContentsMargins(8, 8, 8, 8)
        v.setSpacing(8)
        nom = QLabel(f"{a['nom']} ({a['marque']})")
        nom.setWordWrap(True)
        nom.setStyleSheet("font-weight: 600;")
        det = QLabel(f"{a['taille']} / {a['couleur']} · {format_fcfa(a['prix_vente'])} l'unité")
        det.setProperty("role", "aide")
        det.setWordWrap(True)
        v.addWidget(nom)
        v.addWidget(det)
        bas = QHBoxLayout()
        bas.setSpacing(8)
        b_moins = _bouton_icone("moins", f"Diminuer la quantité de {a['nom']}", "Diminuer la quantité")
        qte = QLabel(str(ligne["qte"]))
        qte.setAlignment(Qt.AlignCenter)
        qte.setMinimumWidth(32)
        qte.setStyleSheet("font-weight: 700; font-size: 17px;")
        b_plus = _bouton_icone("plus", f"Augmenter la quantité de {a['nom']}", "Augmenter la quantité")
        sous = QLabel(format_fcfa(ligne["qte"] * a["prix_vente"]))
        sous.setStyleSheet("font-weight: 700;")
        sous.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        b_ret = _bouton_icone("supprimer", f"Retirer {a['nom']} du panier", "Retirer la ligne (touche Suppr)")
        for b, f in ((b_moins, moins), (b_plus, plus), (b_ret, retirer)):
            b.clicked.connect(lambda _=False, f=f: QTimer.singleShot(0, lambda: f(id_)))
        for w in (b_moins, qte, b_plus):
            bas.addWidget(w)
        bas.addStretch(1)
        bas.addWidget(sous)
        bas.addWidget(b_ret)
        v.addLayout(bas)


class DialogVenteReussie(QDialog):
    def __init__(self, parent, recu: dict):
        super().__init__(parent)
        self.recu = recu
        t = jetons()
        self.setWindowTitle("Vente enregistrée")
        self.setMinimumWidth(420)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(32, 32, 32, 32)
        lay.setSpacing(12)
        ok = QLabel("Vente enregistrée avec succès")
        ok.setProperty("role", "titre")
        ok.setStyleSheet(f"color: {t['succes']};")
        total = QLabel(format_fcfa(recu["total"]))
        total.setProperty("role", "total")
        n = recu["nb_articles"]
        lay.addWidget(ok)
        lay.addWidget(QLabel("Montant encaissé"))
        lay.addWidget(total)
        lay.addWidget(QLabel(f"{n} article{'s' if n > 1 else ''} vendu{'s' if n > 1 else ''}"))
        b_recu = QPushButton("Imprimer / Enregistrer le reçu")
        b_recu.setCursor(Qt.PointingHandCursor)
        b_recu.setAccessibleName("Imprimer ou enregistrer le reçu")
        b_recu.clicked.connect(self._recu)
        b_new = QPushButton("Nouvelle vente")
        b_new.setProperty("role", "accent")
        b_new.setCursor(Qt.PointingHandCursor)
        b_new.setAccessibleName("Nouvelle vente")
        b_new.setDefault(True)
        b_new.clicked.connect(self.accept)
        lay.addSpacing(8)
        lay.addWidget(b_recu)
        lay.addWidget(b_new)
        b_new.setFocus()

    def _recu(self):
        defaut = str(Path.home() / "Documents" / f"recu_{self.recu['id']}.pdf")
        chemin, _ = QFileDialog.getSaveFileName(self, "Enregistrer le reçu", defaut, "Fichier PDF (*.pdf)")
        if not chemin:
            return
        try:
            recu_pdf.generer_recu_pdf(self.recu, chemin)
        except Exception as e:
            QMessageBox.critical(self, "Reçu", f"Impossible de créer le reçu : {e}")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(chemin))  # s'ouvre dans le lecteur PDF : imprimer depuis là


class PageCaisse(QWidget):
    def __init__(self):
        super().__init__()
        t = jetons()
        self.panier = Panier()
        self._cat = None
        root = QHBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        # ----- Colonne gauche : recherche + articles -----
        g = QVBoxLayout()
        g.setSpacing(8)
        titre = QLabel("Caisse")
        titre.setProperty("role", "titre")
        g.addWidget(titre)
        self.recherche = QLineEdit()
        self.recherche.setPlaceholderText("Rechercher un article (nom, marque, catégorie)")
        self.recherche.setAccessibleName("Rechercher un article")
        self.recherche.setClearButtonEnabled(True)
        self.recherche.addAction(icone("recherche", t["texte2"], 18), QLineEdit.LeadingPosition)
        self.recherche.setToolTip("Entrée : ajouter l'article sélectionné · Flèches : changer de ligne")
        self.recherche.installEventFilter(self)
        g.addWidget(self.recherche)
        self.grille = QGridLayout()
        self.grille.setSpacing(8)
        self.groupe = QButtonGroup(self)
        self.groupe.setExclusive(True)
        g.addLayout(self.grille)
        self.liste = creer_table(["Article", "Taille / couleur", "Prix (FCFA)", "Stock", "État"])
        self.liste.setToolTip("Double-clic ou Entrée : ajouter au panier")
        g.addWidget(self.liste, 1)
        ajout = QHBoxLayout()
        ajout.setSpacing(8)
        self.b_moins = _bouton_icone("moins", "Diminuer la quantité à ajouter", "Diminuer la quantité")
        self.qte = QSpinBox()
        self.qte.setRange(1, 999)
        self.qte.setButtonSymbols(QSpinBox.NoButtons)
        self.qte.setAlignment(Qt.AlignCenter)
        self.qte.setMinimumSize(64, 44)
        self.qte.setAccessibleName("Quantité à ajouter")
        self.b_plus = _bouton_icone("plus", "Augmenter la quantité à ajouter", "Augmenter la quantité")
        self.b_moins.clicked.connect(lambda: self.qte.setValue(self.qte.value() - 1))
        self.b_plus.clicked.connect(lambda: self.qte.setValue(self.qte.value() + 1))
        self.b_ajout = QPushButton(" Ajouter au panier")
        self.b_ajout.setIcon(icone("plus", t["texte_accent"], 20))
        self.b_ajout.setProperty("role", "accent")
        self.b_ajout.setMinimumHeight(44)
        self.b_ajout.setCursor(Qt.PointingHandCursor)
        self.b_ajout.setAccessibleName("Ajouter au panier")
        self.b_ajout.setToolTip("Ajouter l'article sélectionné (Entrée)")
        self.b_ajout.clicked.connect(self._ajouter_selection)
        for w in (self.b_moins, self.qte, self.b_plus):
            ajout.addWidget(w)
        ajout.addWidget(self.b_ajout, 1)
        g.addLayout(ajout)
        root.addLayout(g, 3)

        # ----- Colonne droite : panier -----
        carte = QFrame()
        carte.setProperty("carte", True)
        d = QVBoxLayout(carte)
        d.setContentsMargins(16, 16, 16, 16)
        d.setSpacing(8)
        tp = QLabel("Panier")
        tp.setProperty("role", "section")
        d.addWidget(tp)
        self.panier_ui = QListWidget()
        self.panier_ui.setAccessibleName("Articles du panier")
        self.panier_ui.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        d.addWidget(self.panier_ui, 1)
        msg = QHBoxLayout()
        self.ico_msg = QLabel()
        self.ico_msg.setPixmap(icone("erreur", t["danger"], 16).pixmap(16, 16))
        self.lbl_msg = QLabel()
        self.lbl_msg.setProperty("role", "erreur")
        self.lbl_msg.setWordWrap(True)
        msg.addWidget(self.ico_msg, 0, Qt.AlignTop)
        msg.addWidget(self.lbl_msg, 1)
        d.addLayout(msg)
        self.lbl_nb = QLabel()
        self.lbl_nb.setProperty("role", "aide")
        d.addWidget(self.lbl_nb)
        lt = QLabel("Total à payer")
        d.addWidget(lt)
        self.lbl_total = QLabel()
        self.lbl_total.setProperty("role", "total")
        self.lbl_total.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        d.addWidget(self.lbl_total)
        self.b_valider = QPushButton("Valider la vente")
        self.b_valider.setProperty("role", "accent")
        self.b_valider.setMinimumHeight(56)
        self.b_valider.setCursor(Qt.PointingHandCursor)
        self.b_valider.setAccessibleName("Valider la vente")
        self.b_valider.setToolTip("Valider la vente (Ctrl+Entrée)")
        self.b_valider.clicked.connect(self._valider)
        self.b_vider = QPushButton("Vider le panier")
        self.b_vider.setMinimumHeight(44)
        self.b_vider.setCursor(Qt.PointingHandCursor)
        self.b_vider.setAccessibleName("Vider le panier")
        self.b_vider.setToolTip("Annuler la vente en cours (Échap)")
        self.b_vider.clicked.connect(self._echap)
        d.addWidget(self.b_vider)
        d.addWidget(self.b_valider)
        root.addWidget(carte, 2)

        # ----- Comportements et raccourcis -----
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(200)
        self._timer.timeout.connect(self.rafraichir_liste)
        self.recherche.textChanged.connect(lambda _: self._timer.start())
        self.recherche.returnPressed.connect(self._ajouter_selection)
        self.liste.doubleClicked.connect(self._ajouter_selection)
        self.liste.itemSelectionChanged.connect(self._maj_bouton_ajout)
        self.groupe.buttonClicked.connect(self._choisir_categorie)
        self._raccourci(Qt.Key_Return, self.liste, self._ajouter_selection, Qt.WidgetShortcut)
        self._raccourci(Qt.Key_Enter, self.liste, self._ajouter_selection, Qt.WidgetShortcut)
        self._raccourci(Qt.Key_Delete, self.panier_ui, self._retirer_courant, Qt.WidgetShortcut)
        self._raccourci(QKeySequence("Ctrl+Return"), self, self._valider, Qt.WidgetWithChildrenShortcut)
        self._raccourci(QKeySequence("Ctrl+Enter"), self, self._valider, Qt.WidgetWithChildrenShortcut)
        self._raccourci(Qt.Key_Escape, self, self._echap, Qt.WidgetWithChildrenShortcut)
        self._message("")
        self._maj_panier()

    def _raccourci(self, touche, parent, action, contexte):
        sc = QShortcut(QKeySequence(touche), parent)
        sc.setContext(contexte)
        sc.activated.connect(action)

    def eventFilter(self, obj, ev):
        """Flèches haut/bas dans la recherche : déplacent la sélection dans la liste."""
        if obj is self.recherche and ev.type() == QEvent.KeyPress and ev.key() in (Qt.Key_Down, Qt.Key_Up):
            QApplication.sendEvent(self.liste, ev)
            return True
        return super().eventFilter(obj, ev)

    def showEvent(self, e):
        super().showEvent(e)
        self._charger_categories()
        self.rafraichir_liste()
        self.recherche.setFocus()  # champ actif dès l'ouverture

    # ----- Liste des articles -----
    def _charger_categories(self):
        for b in list(self.groupe.buttons()):
            self.groupe.removeButton(b)
            b.deleteLater()
        try:
            cats = articles.categories()
        except ErreurBaseDeDonnees:
            cats = []
        for i, (libelle, valeur) in enumerate([("Toutes", None)] + [(c, c) for c in cats]):
            b = QPushButton(libelle)
            b.setProperty("chip", True)
            b.setCheckable(True)
            b.setChecked(valeur == self._cat)
            b.setCursor(Qt.PointingHandCursor)
            b.setAccessibleName(f"Catégorie {libelle}")
            b.setProperty("valeur", valeur)
            self.groupe.addButton(b)
            self.grille.addWidget(b, i // 3, i % 3)
        if not self.groupe.checkedButton():
            self.groupe.buttons()[0].setChecked(True)
            self._cat = None

    def _choisir_categorie(self, bouton):
        self._cat = bouton.property("valeur")
        self.rafraichir_liste()
        self.recherche.setFocus()

    def rafraichir_liste(self):
        QApplication.setOverrideCursor(Qt.WaitCursor)
        erreur = None
        try:
            seuil = articles.seuil()
            lignes = articles.lister_vendeur(self.recherche.text(), self._cat)
        except ErreurBaseDeDonnees as e:
            erreur = e
        finally:
            QApplication.restoreOverrideCursor()
        if erreur:
            QMessageBox.critical(self, "Caisse", str(erreur))
            return
        self.liste.setSortingEnabled(False)
        self.liste.setRowCount(len(lignes))
        for r, a in enumerate(lignes):
            c0 = texte(f"{a['nom']} ({a['marque']})")
            c0.setData(Qt.UserRole + 1, a)
            c_qte = NumItem(str(a["quantite_stock"]), a["quantite_stock"])
            c_etat = texte("")
            cellules = [c0, texte(f"{a['taille']} / {a['couleur']}"),
                        NumItem(nombre(a["prix_vente"]), a["prix_vente"]), c_qte, c_etat]
            alerte_stock(cellules, c_etat, c_qte, a["quantite_stock"], seuil)
            for c, it in enumerate(cellules):
                self.liste.setItem(r, c, it)
        self.liste.setSortingEnabled(True)
        if lignes:
            self.liste.selectRow(0)  # Entrée ajoute directement le premier résultat
        self._maj_bouton_ajout()

    def _article_selectionne(self):
        lignes = self.liste.selectionModel().selectedRows()
        return self.liste.item(lignes[0].row(), 0).data(Qt.UserRole + 1) if lignes else None

    def _maj_bouton_ajout(self):
        a = self._article_selectionne()
        self.b_ajout.setEnabled(bool(a) and a["quantite_stock"] > 0)  # Épuisé : bouton désactivé

    # ----- Panier -----
    def _message(self, txt: str):
        self.lbl_msg.setText(txt)
        self.lbl_msg.setVisible(bool(txt))
        self.ico_msg.setVisible(bool(txt))

    def _ajouter_selection(self, *_):
        a = self._article_selectionne()
        if not a:
            self._message("Sélectionnez d'abord un article dans la liste.")
            return
        try:
            self.panier.ajouter(a, self.qte.value())
        except ErreurPanier as e:
            self._message(str(e))
            return
        self._message("")
        self.qte.setValue(1)
        self._maj_panier()
        self.recherche.setFocus()
        self.recherche.selectAll()

    def _maj_panier(self):
        self.panier_ui.clear()
        for l in self.panier.lignes():
            id_ = l["article"]["id"]
            it = QListWidgetItem()
            it.setData(Qt.UserRole, id_)
            w = LigneWidget(l, id_, lambda i: self._changer(i, -1), lambda i: self._changer(i, +1), self._retirer)
            it.setSizeHint(w.sizeHint())
            self.panier_ui.addItem(it)
            self.panier_ui.setItemWidget(it, w)
        n = self.panier.nb_articles
        self.lbl_nb.setText(f"{n} article{'s' if n > 1 else ''} dans le panier" if n else "Le panier est vide")
        self.lbl_total.setText(format_fcfa(self.panier.total))
        self.b_valider.setEnabled(not self.panier.est_vide)
        self.b_vider.setEnabled(not self.panier.est_vide)

    def _changer(self, id_, delta):
        ligne = next((l for l in self.panier.lignes() if l["article"]["id"] == id_), None)
        if not ligne:
            return
        try:
            self.panier.definir_qte(id_, ligne["qte"] + delta)
            self._message("")
        except ErreurPanier as e:
            self._message(str(e))
        self._maj_panier()

    def _retirer(self, id_):
        self.panier.retirer(id_)
        self._message("")
        self._maj_panier()

    def _retirer_courant(self):
        it = self.panier_ui.currentItem()
        if it:
            self._retirer(it.data(Qt.UserRole))

    def _echap(self):
        """Échap : vide le panier (avec confirmation) ou, s'il est vide, efface la recherche."""
        if self.panier.est_vide:
            self.recherche.clear()
            return
        if confirmer(self, "Annuler la vente", "Voulez-vous vider le panier et annuler cette vente ?", "Vider le panier"):
            self.panier.vider()
            self._message("")
            self._maj_panier()

    # ----- Validation de la vente -----
    def _valider(self):
        if self.panier.est_vide:
            return
        lignes = [(l["article"]["id"], l["qte"]) for l in self.panier.lignes()]
        secours = self._recu_secours()
        QApplication.setOverrideCursor(Qt.WaitCursor)
        erreur, vente_id = None, None
        try:
            vente_id = ventes.enregistrer_vente(lignes)
        except (ErreurBaseDeDonnees, AccesRefuse) as e:
            erreur = e
        finally:
            QApplication.restoreOverrideCursor()
        if erreur:
            if isinstance(erreur, ventes.ErreurStock):
                QMessageBox.warning(self, "Stock insuffisant", str(erreur))
                self.rafraichir_liste()
            else:
                QMessageBox.critical(self, "Vente non enregistrée", str(erreur))
            return
        try:
            recu = ventes.lire_recu(vente_id)
        except ErreurBaseDeDonnees:  # vente déjà enregistrée : on garde un reçu construit depuis le panier
            recu = {**secours, "id": vente_id}
        self.panier.vider()
        self._message("")
        self._maj_panier()
        self.rafraichir_liste()
        DialogVenteReussie(self, recu).exec()
        self.recherche.clear()
        self.recherche.setFocus()

    def _recu_secours(self) -> dict:
        return {"id": 0, "date_heure": datetime.now(), "total": self.panier.total, "nb_articles": self.panier.nb_articles,
                "lignes": [{"nom": l["article"]["nom"], "taille": l["article"]["taille"], "couleur": l["article"]["couleur"],
                            "quantite": l["qte"], "prix_unitaire": l["article"]["prix_vente"]} for l in self.panier.lignes()]}
