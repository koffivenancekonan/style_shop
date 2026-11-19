"""Paramètres (administrateur) : seuil de stock faible, apparence, mot de passe."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QApplication, QButtonGroup, QFrame, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
                               QPushButton, QScrollArea, QSpinBox, QVBoxLayout, QWidget)
from database.connexion import ErreurBaseDeDonnees
from services import articles, auth, parametres
from ui.theme import charger_preference, enregistrer_preference
from ui.widgets import ChampForm


def _carte(titre: str) -> tuple[QFrame, QVBoxLayout]:
    f = QFrame()
    f.setProperty("carte", True)
    v = QVBoxLayout(f)
    v.setContentsMargins(20, 16, 20, 16)
    v.setSpacing(8)
    t = QLabel(titre)
    t.setProperty("role", "section")
    v.addWidget(t)
    return f, v


def _bouton(libelle: str, action) -> QPushButton:
    b = QPushButton(libelle)
    b.setProperty("role", "accent")
    b.setCursor(Qt.PointingHandCursor)
    b.setAccessibleName(libelle)
    b.clicked.connect(action)
    return b


class PageParametres(QScrollArea):
    theme_change = Signal()  # la fenêtre se recharge pour appliquer le nouveau thème

    def __init__(self, utilisateur):
        super().__init__()
        self.u = utilisateur
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        contenu = QWidget()
        self.setWidget(contenu)
        lay = QVBoxLayout(contenu)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(16)
        titre = QLabel("Paramètres")
        titre.setProperty("role", "titre")
        lay.addWidget(titre)

        # --- Seuil de stock faible ---
        c1, v1 = _carte("Alerte de stock faible")
        self.seuil = QSpinBox()
        self.seuil.setRange(1, 999)
        self.seuil.setMinimumHeight(44)
        self.seuil.setAccessibleName("Seuil de stock faible")
        self.f_seuil = ChampForm("Seuil critique (quantité)", self.seuil,
            aide="Un article est en alerte (ligne rouge) quand sa quantité est strictement inférieure à ce seuil.")
        v1.addLayout(self.f_seuil)
        self.ok_seuil = QLabel()
        self.ok_seuil.setProperty("role", "succes")
        v1.addWidget(self.ok_seuil)
        v1.addWidget(_bouton("Enregistrer le seuil", self._enregistrer_seuil), 0, Qt.AlignLeft)
        lay.addWidget(c1)

        # --- Apparence ---
        c2, v2 = _carte("Apparence")
        ligne = QHBoxLayout()
        self.groupe = QButtonGroup(self)
        self.groupe.setExclusive(True)
        actuel = charger_preference()
        for libelle, cle in (("Thème clair", "clair"), ("Thème sombre", "sombre")):
            b = QPushButton(libelle)
            b.setProperty("chip", True)
            b.setCheckable(True)
            b.setChecked(cle == actuel)
            b.setProperty("cle", cle)
            b.setCursor(Qt.PointingHandCursor)
            b.setAccessibleName(libelle)
            self.groupe.addButton(b)
            ligne.addWidget(b)
        ligne.addStretch(1)
        v2.addLayout(ligne)
        aide = QLabel("Ce réglage s'applique à cet ordinateur. L'affichage est rechargé, sans vous déconnecter.")
        aide.setProperty("role", "aide")
        aide.setWordWrap(True)
        v2.addWidget(aide)
        v2.addWidget(_bouton("Appliquer l'apparence", self._appliquer_theme), 0, Qt.AlignLeft)
        lay.addWidget(c2)

        # --- Mon mot de passe ---
        c3, v3 = _carte("Mon mot de passe")
        self.champs = {}
        for cle, lib in (("actuel", "Mot de passe actuel"), ("nouveau", "Nouveau mot de passe"),
                         ("conf", "Confirmer le nouveau mot de passe")):
            e = QLineEdit()
            e.setEchoMode(QLineEdit.Password)
            e.setAccessibleName(lib)
            self.champs[cle] = ChampForm(lib, e, aide="8 caractères minimum, avec une lettre et un chiffre." if cle == "nouveau" else "")
            v3.addLayout(self.champs[cle])
        self.ok_mdp = QLabel()
        self.ok_mdp.setProperty("role", "succes")
        v3.addWidget(self.ok_mdp)
        v3.addWidget(_bouton("Changer mon mot de passe", self._changer_mdp), 0, Qt.AlignLeft)
        lay.addWidget(c3)
        lay.addStretch(1)

    def showEvent(self, e):
        super().showEvent(e)
        try:
            self.seuil.setValue(articles.seuil())
        except ErreurBaseDeDonnees:
            pass

    def _enregistrer_seuil(self):
        self.ok_seuil.setText("")
        n, err = parametres.valider_seuil(str(self.seuil.value()))
        if err:
            self.f_seuil.erreur(err)
            return
        self.f_seuil.effacer()
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            parametres.definir_seuil(n)
        except (ErreurBaseDeDonnees, auth.AccesRefuse) as e:
            QMessageBox.critical(self, "Paramètres", str(e))
            return
        finally:
            QApplication.restoreOverrideCursor()
        self.ok_seuil.setText(f"Seuil enregistré : alerte sous {n} pièces.")

    def _appliquer_theme(self):
        cle = self.groupe.checkedButton().property("cle")
        if cle == charger_preference():
            return
        enregistrer_preference(cle)
        self.theme_change.emit()

    def _changer_mdp(self):
        self.ok_mdp.setText("")
        for c in self.champs.values():
            c.effacer()
        actuel, nouveau, conf = (self.champs[k].saisie.text() for k in ("actuel", "nouveau", "conf"))
        if not auth.verifier(actuel, self.u.mot_de_passe_hash):
            self.champs["actuel"].erreur("Mot de passe actuel incorrect.")
            return
        m = auth.valider_nouveau_mdp(nouveau, self.u.mot_de_passe_hash)
        if m:
            self.champs["nouveau"].erreur(m)
            return
        if nouveau != conf:
            self.champs["conf"].erreur("Les deux mots de passe ne sont pas identiques. Saisissez-les à nouveau.")
            return
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            auth.changer_mot_de_passe(self.u, nouveau)
        except (auth.ErreurAuthentification, ErreurBaseDeDonnees) as e:
            self.champs["nouveau"].erreur(str(e))
            return
        finally:
            QApplication.restoreOverrideCursor()
        for c in self.champs.values():
            c.saisie.clear()
        self.ok_mdp.setText("Mot de passe modifié.")
