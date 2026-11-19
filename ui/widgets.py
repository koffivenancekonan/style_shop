"""Composants réutilisables : champ de formulaire avec erreur, confirmation destructive."""
from PySide6.QtWidgets import QLabel, QHBoxLayout, QMessageBox, QVBoxLayout
from ui.icons import icone
from ui.theme import jetons


class ChampForm(QVBoxLayout):
    """Libellé visible au-dessus, champ, aide, puis erreur (icône + texte) sous le champ."""

    def __init__(self, libelle: str, widget, obligatoire: bool = True, aide: str = ""):
        super().__init__()
        self.setSpacing(4)
        self.saisie = widget  # (ne pas l'appeler 'widget' : nom réservé par Qt)
        self.addWidget(QLabel(libelle + (" *" if obligatoire else "")))
        self.addWidget(widget)
        if aide:
            a = QLabel(aide)
            a.setProperty("role", "aide")
            a.setWordWrap(True)
            self.addWidget(a)
        ligne = QHBoxLayout()
        self.icone = QLabel()
        self.icone.setPixmap(icone("erreur", jetons()["danger"], 16).pixmap(16, 16))
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
        self._marquer(True)

    def effacer(self):
        self.icone.hide()
        self.message.hide()
        self._marquer(False)

    def _marquer(self, invalide: bool):
        self.saisie.setProperty("invalide", invalide)
        self.saisie.style().unpolish(self.saisie)
        self.saisie.style().polish(self.saisie)


def confirmer(parent, titre: str, texte: str, bouton_action: str) -> bool:
    """Confirmation avant action destructive, avec un bouton explicite (pas « OK »)."""
    mb = QMessageBox(parent)
    mb.setIcon(QMessageBox.Warning)
    mb.setWindowTitle(titre)
    mb.setText(texte)
    action = mb.addButton(bouton_action, QMessageBox.DestructiveRole)
    annuler = mb.addButton("Annuler", QMessageBox.RejectRole)
    mb.setDefaultButton(annuler)
    mb.exec()
    return mb.clickedButton() is action
