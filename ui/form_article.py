"""Formulaire d'ajout / modification d'un article (administrateur)."""
from PySide6.QtCore import QRegularExpression, Qt
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtWidgets import (QApplication, QComboBox, QDialog, QGridLayout, QHBoxLayout, QLabel,
                               QLineEdit, QMessageBox, QPushButton, QVBoxLayout)
from database.connexion import ErreurBaseDeDonnees
from services import articles
from services.auth import AccesRefuse
from ui.icons import icone
from ui.theme import jetons
from ui.widgets import ChampForm
from utils.format import format_fcfa

ORDRE = ["nom", "categorie", "taille", "couleur", "marque", "prix_achat_min", "prix_achat_max",
         "prix_achat_reel", "prix_vente", "quantite_stock"]


def _entier(texte: str):
    t = texte.strip()
    return int(t) if t.isdigit() else None


class DialogArticle(QDialog):
    def __init__(self, parent=None, article: dict | None = None):
        super().__init__(parent)
        self.article = article
        self.setWindowTitle("Modifier l'article" if article else "Ajouter un article")
        self.setMinimumWidth(780)
        self._touches: set[str] = set()
        self.w, self.champs = {}, {}

        def ligne(nom, libelle, aide="", numerique=False):
            e = QLineEdit()
            e.setAccessibleName(libelle)
            if numerique:
                e.setValidator(QRegularExpressionValidator(QRegularExpression(r"\d{0,9}")))
                e.setAlignment(Qt.AlignRight)
            e.editingFinished.connect(lambda n=nom: self._sortie_champ(n))
            self.w[nom] = e
            self.champs[nom] = ChampForm(libelle, e, aide=aide)

        ligne("nom", "Nom de l'article")
        self.cat = QComboBox()
        self.cat.setEditable(True)
        self.cat.setAccessibleName("Catégorie")
        try:
            self.cat.addItems(articles.categories())
        except ErreurBaseDeDonnees:
            self.cat.addItems(articles.CATEGORIES_DEFAUT)
        self.cat.setCurrentIndex(-1)
        self.cat.lineEdit().editingFinished.connect(lambda: self._sortie_champ("categorie"))
        self.w["categorie"] = self.cat
        self.champs["categorie"] = ChampForm("Catégorie", self.cat, aide="Choisissez dans la liste ou saisissez-en une nouvelle.")
        ligne("taille", "Taille")
        ligne("couleur", "Couleur")
        ligne("marque", "Marque")
        ligne("prix_achat_min", "Prix d'achat minimum (FCFA)", numerique=True)
        ligne("prix_achat_max", "Prix d'achat maximum (FCFA)", numerique=True)
        ligne("prix_achat_reel", "Prix d'achat réel (FCFA)", "Coût de revient réel de l'article.", True)
        ligne("prix_vente", "Prix de vente (FCFA)", numerique=True)
        ligne("quantite_stock", "Quantité en boutique", numerique=True)

        # Bénéfice affiché en direct
        self.lbl_benef = QLabel("—")
        self.lbl_benef.setProperty("role", "montant")
        boite = QVBoxLayout()
        boite.addWidget(QLabel("Bénéfice unitaire"))
        boite.addWidget(self.lbl_benef)
        self.lbl_avert = QLabel()
        self.lbl_avert.setProperty("role", "alerte")
        self.lbl_avert.setWordWrap(True)
        self.ico_avert = QLabel()
        self.ico_avert.setPixmap(icone("alerte", jetons()["avertissement"], 18).pixmap(18, 18))
        avert = QHBoxLayout()
        avert.addWidget(self.ico_avert, 0, Qt.AlignTop)
        avert.addWidget(self.lbl_avert, 1)
        self.w["prix_achat_reel"].textChanged.connect(self._maj_benefice)
        self.w["prix_vente"].textChanged.connect(self._maj_benefice)

        g = QGridLayout()
        g.setHorizontalSpacing(16)
        g.setVerticalSpacing(8)
        t1 = QLabel("Informations")
        t1.setProperty("role", "section")
        t2 = QLabel("Prix et stock (visibles uniquement par l'administrateur)")
        t2.setProperty("role", "section")
        g.addWidget(t1, 0, 0, 1, 3)
        g.addLayout(self.champs["nom"], 1, 0, 1, 2)
        g.addLayout(self.champs["categorie"], 1, 2)
        g.addLayout(self.champs["taille"], 2, 0)
        g.addLayout(self.champs["couleur"], 2, 1)
        g.addLayout(self.champs["marque"], 2, 2)
        g.addWidget(t2, 3, 0, 1, 3)
        g.addLayout(self.champs["prix_achat_min"], 4, 0)
        g.addLayout(self.champs["prix_achat_max"], 4, 1)
        g.addLayout(self.champs["prix_achat_reel"], 4, 2)
        g.addLayout(self.champs["prix_vente"], 5, 0)
        g.addLayout(self.champs["quantite_stock"], 5, 1)
        g.addLayout(boite, 5, 2)
        g.addLayout(avert, 6, 0, 1, 3)

        annuler = QPushButton("Annuler")
        annuler.setCursor(Qt.PointingHandCursor)
        annuler.setAccessibleName("Annuler")
        annuler.clicked.connect(self.reject)
        self.ok = QPushButton("Enregistrer l'article")
        self.ok.setProperty("role", "accent")
        self.ok.setCursor(Qt.PointingHandCursor)
        self.ok.setAccessibleName("Enregistrer l'article")
        self.ok.setDefault(True)  # Entrée valide le formulaire
        self.ok.clicked.connect(self._enregistrer)
        bas = QHBoxLayout()
        bas.addStretch(1)
        bas.addWidget(annuler)
        bas.addWidget(self.ok)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(12)
        lay.addLayout(g)
        lay.addLayout(bas)

        if article:
            for n in ("nom", "taille", "couleur", "marque"):
                self.w[n].setText(str(article[n]))
            self.cat.setEditText(article["categorie"])
            for n in ("prix_achat_min", "prix_achat_max", "prix_achat_reel", "prix_vente", "quantite_stock"):
                self.w[n].setText(str(article[n]))
        self._maj_benefice()
        self.w["nom"].setFocus()

    def _donnees(self) -> dict:
        d = {n: self.w[n].text().strip() for n in ("nom", "taille", "couleur", "marque")}
        d["categorie"] = self.cat.currentText().strip()
        for n in ("prix_achat_min", "prix_achat_max", "prix_achat_reel", "prix_vente", "quantite_stock"):
            d[n] = _entier(self.w[n].text())
        return d

    def _maj_benefice(self):
        t = jetons()
        d = self._donnees()
        if d["prix_vente"] is not None and d["prix_achat_reel"] is not None:
            b = articles.benefice_unitaire(d["prix_vente"], d["prix_achat_reel"])
            self.lbl_benef.setText(format_fcfa(b))
            self.lbl_benef.setStyleSheet(f"color: {t['succes'] if b >= 0 else t['danger']};")
        else:
            self.lbl_benef.setText("—")
            self.lbl_benef.setStyleSheet("")
        msg = articles.avertissement_prix(d)
        self.lbl_avert.setText(msg or "")
        self.lbl_avert.setVisible(bool(msg))
        self.ico_avert.setVisible(bool(msg))

    def _afficher(self, erreurs: dict):
        for n, champ in self.champs.items():
            if n in self._touches and n in erreurs:
                champ.erreur(erreurs[n])
            else:
                champ.effacer()

    def _sortie_champ(self, nom: str):
        """Validation à la sortie du champ."""
        self._touches.add(nom)
        self._afficher(articles.valider(self._donnees()))

    def _enregistrer(self):
        self._touches = set(ORDRE)
        erreurs = articles.valider(self._donnees())
        self._afficher(erreurs)
        if erreurs:
            self.w[next(n for n in ORDRE if n in erreurs)].setFocus()
            return
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            if self.article:
                articles.modifier(self.article["id"], self._donnees())
            else:
                articles.creer(self._donnees())
        except articles.ErreurValidation as e:
            self._afficher(e.erreurs)
            return
        except (ErreurBaseDeDonnees, AccesRefuse) as e:
            QMessageBox.critical(self, "Enregistrement impossible", str(e))
            return
        finally:
            QApplication.restoreOverrideCursor()
        self.accept()
