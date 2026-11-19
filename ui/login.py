"""Écran de connexion et changement de mot de passe obligatoire."""
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (QApplication, QDialog, QHBoxLayout, QLabel, QLineEdit,
                               QMessageBox, QPushButton, QStyle, QVBoxLayout)
from database.connexion import ErreurBaseDeDonnees
from services import auth

MAX_ESSAIS = 5
PAUSE_SECONDES = 30


class _ChampAvecErreur(QVBoxLayout):
    """Libellé au-dessus, champ, puis message d'erreur (icône + texte) sous le champ."""

    def __init__(self, parent, libelle: str, mot_de_passe=False, aide: str = ""):
        super().__init__()
        self.setSpacing(4)
        self.label = QLabel(libelle + " *")
        self.champ = QLineEdit()
        self.champ.setAccessibleName(libelle)
        if mot_de_passe:
            self.champ.setEchoMode(QLineEdit.Password)
        self.addWidget(self.label)
        self.addWidget(self.champ)
        if aide:
            a = QLabel(aide)
            a.setProperty("role", "aide")
            a.setWordWrap(True)
            self.addWidget(a)
        ligne = QHBoxLayout()
        self.icone = QLabel()
        self.icone.setPixmap(parent.style().standardIcon(QStyle.SP_MessageBoxCritical).pixmap(16, 16))
        self.message = QLabel()
        self.message.setProperty("role", "erreur")
        self.message.setWordWrap(True)
        ligne.addWidget(self.icone)
        ligne.addWidget(self.message, 1)
        self.addLayout(ligne)
        self.effacer()

    def erreur(self, texte: str):
        self.message.setText(texte)
        self.icone.show()
        self.message.show()
        self.champ.setProperty("invalide", True)
        self._rafraichir()

    def effacer(self):
        self.icone.hide()
        self.message.hide()
        self.champ.setProperty("invalide", False)
        self._rafraichir()

    def _rafraichir(self):
        self.champ.style().unpolish(self.champ)
        self.champ.style().polish(self.champ)


def _bouton_accent(texte: str, action) -> QPushButton:
    b = QPushButton(texte)
    b.setProperty("role", "accent")
    b.setCursor(Qt.PointingHandCursor)
    b.setAccessibleName(texte)
    b.setDefault(True)
    b.clicked.connect(action)
    return b


class LoginDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("STYLE SHOP PORT-BOUËT : Connexion")
        self.setMinimumWidth(420)
        self.utilisateur = None
        self._echecs = 0
        lay = QVBoxLayout(self)
        lay.setContentsMargins(32, 32, 32, 32)
        lay.setSpacing(12)
        titre = QLabel("STYLE SHOP PORT-BOUËT")
        titre.setProperty("role", "titre")
        sous = QLabel("Connectez-vous pour continuer")
        sous.setProperty("role", "aide")
        lay.addWidget(titre)
        lay.addWidget(sous)
        self.f_nom = _ChampAvecErreur(self, "Identifiant")
        self.f_mdp = _ChampAvecErreur(self, "Mot de passe", mot_de_passe=True)
        lay.addLayout(self.f_nom)
        lay.addLayout(self.f_mdp)
        self.bouton = _bouton_accent("Se connecter", self._valider)
        lay.addWidget(self.bouton)
        self.f_nom.champ.setFocus()
        self.f_nom.champ.returnPressed.connect(self.f_mdp.champ.setFocus)
        self.f_mdp.champ.returnPressed.connect(self._valider)

    def _valider(self):
        self.f_nom.effacer()
        self.f_mdp.effacer()
        if not self.f_nom.champ.text().strip():
            return self.f_nom.erreur("Saisissez votre identifiant.")
        if not self.f_mdp.champ.text():
            return self.f_mdp.erreur("Saisissez votre mot de passe.")
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))  # chargement visible
        try:
            self.utilisateur = auth.authentifier(self.f_nom.champ.text(), self.f_mdp.champ.text())
        except auth.ErreurAuthentification as e:
            self._echecs += 1
            self.f_mdp.erreur(str(e))
            self.f_mdp.champ.clear()
            if self._echecs >= MAX_ESSAIS:
                self._bloquer()
            return
        except ErreurBaseDeDonnees as e:
            QMessageBox.critical(self, "Base de données", str(e))
            return
        finally:
            QApplication.restoreOverrideCursor()
        self.accept()

    def _bloquer(self):
        """Pause après trop d'échecs (limite les essais répétés)."""
        self._reste = PAUSE_SECONDES
        self.bouton.setEnabled(False)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tic)
        self._timer.start(1000)
        self._tic()

    def _tic(self):
        if self._reste <= 0:
            self._timer.stop()
            self._echecs = 0
            self.bouton.setEnabled(True)
            self.bouton.setText("Se connecter")
            return
        self.bouton.setText(f"Réessayez dans {self._reste} s")
        self._reste -= 1


class ChangerMdpDialog(QDialog):
    def __init__(self, utilisateur):
        super().__init__()
        self.setWindowTitle("Changement de mot de passe obligatoire")
        self.setMinimumWidth(440)
        self.utilisateur = utilisateur
        lay = QVBoxLayout(self)
        lay.setContentsMargins(32, 32, 32, 32)
        lay.setSpacing(12)
        titre = QLabel("Choisissez un nouveau mot de passe")
        titre.setProperty("role", "titre")
        lay.addWidget(titre)
        self.f_new = _ChampAvecErreur(self, "Nouveau mot de passe", True,
                                      "8 caractères minimum, avec au moins une lettre et un chiffre.")
        self.f_conf = _ChampAvecErreur(self, "Confirmer le mot de passe", True)
        lay.addLayout(self.f_new)
        lay.addLayout(self.f_conf)
        lay.addWidget(_bouton_accent("Enregistrer le mot de passe", self._valider))
        self.f_new.champ.editingFinished.connect(self._verifier_nouveau)  # validation à la sortie du champ
        self.f_new.champ.returnPressed.connect(self.f_conf.champ.setFocus)
        self.f_conf.champ.returnPressed.connect(self._valider)
        self.f_new.champ.setFocus()

    def _verifier_nouveau(self) -> bool:
        self.f_new.effacer()
        err = auth.valider_nouveau_mdp(self.f_new.champ.text(), self.utilisateur.mot_de_passe_hash)
        if err:
            self.f_new.erreur(err)
        return err is None

    def _valider(self):
        self.f_conf.effacer()
        if not self._verifier_nouveau():
            return
        if self.f_new.champ.text() != self.f_conf.champ.text():
            return self.f_conf.erreur("Les deux mots de passe ne sont pas identiques. Saisissez-les à nouveau.")
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        try:
            auth.changer_mot_de_passe(self.utilisateur, self.f_new.champ.text())
        except (auth.ErreurAuthentification, ErreurBaseDeDonnees) as e:
            self.f_new.erreur(str(e))
            return
        finally:
            QApplication.restoreOverrideCursor()
        self.accept()
