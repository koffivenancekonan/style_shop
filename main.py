"""Point d'entrée : vérifie MySQL, crée l'admin par défaut, connexion, fenêtre principale."""
import sys
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication, QMessageBox
from config.settings import RACINE
from database.connexion import ErreurBaseDeDonnees, verifier_mysql
from services import auth
from ui.fenetre_principale import FenetrePrincipale
from ui.login import ChangerMdpDialog, LoginDialog
from ui.theme import charger_preference, definir_theme, generer_qss


def charger_polices():
    """Charge les polices embarquées (Rubik, Nunito Sans) : fonctionne sans internet."""
    for ttf in (RACINE / "assets" / "fonts").glob("*.ttf"):
        QFontDatabase.addApplicationFont(str(ttf))


def appliquer_theme(app):
    definir_theme(charger_preference())
    app.setStyleSheet(generer_qss())


def main() -> int:
    app = QApplication(sys.argv)
    charger_polices()
    appliquer_theme(app)
    try:
        verifier_mysql()
        temporaire = auth.creer_admin_defaut()
    except (ErreurBaseDeDonnees, RuntimeError) as e:
        QMessageBox.critical(None, "Démarrage impossible", str(e))
        return 1
    if temporaire:
        QMessageBox.information(None, "Compte administrateur créé",
            f"Identifiant : admin\nMot de passe temporaire : {temporaire}\n\n"
            "Notez-le maintenant : il ne sera plus affiché. "
            "Vous devrez le changer à la première connexion.")
    while True:  # boucle : après une déconnexion, retour à l'écran de connexion
        dlg = LoginDialog()
        if dlg.exec() != LoginDialog.Accepted:
            return 0
        u = dlg.utilisateur
        if u.doit_changer_mdp and ChangerMdpDialog(u).exec() != ChangerMdpDialog.Accepted:
            return 0
        auth.definir_utilisateur(u)
        while True:  # rechargement de l'affichage (changement de thème) sans nouvelle connexion
            fen = FenetrePrincipale(u)
            fen.show()
            app.exec()
            if not fen.recharger:
                break
            appliquer_theme(app)
        auth.definir_utilisateur(None)
        if not fen.deconnecte:
            return 0


if __name__ == "__main__":
    sys.exit(main())
