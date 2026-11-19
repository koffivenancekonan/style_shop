"""Fenêtre principale : menu latéral (icône + texte) filtré selon le rôle, pages empilées."""
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (QButtonGroup, QFrame, QHBoxLayout, QLabel, QMainWindow, QMessageBox,
                               QPushButton, QStackedWidget, QVBoxLayout, QWidget)
from database.connexion import ErreurBaseDeDonnees
from services import articles
from ui.caisse import PageCaisse
from ui.catalogue import PageCatalogue
from ui.dashboard import PageDashboard
from ui.parametres import PageParametres
from ui.utilisateurs import PageUtilisateurs
from ui.icons import icone
from ui.stock import PageStock
from ui.theme import jetons


class PageProvisoire(QWidget):
    """Écran à venir (livré dans une étape suivante)."""
    def __init__(self, titre: str, etape: str):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 24, 24, 24)
        t = QLabel(titre)
        t.setProperty("role", "titre")
        a = QLabel(f"Cet écran sera disponible à l'{etape}.")
        a.setProperty("role", "aide")
        lay.addWidget(t)
        lay.addWidget(a)
        lay.addStretch(1)
        
class FenetrePrincipale(QMainWindow):
    deconnexion = Signal()
    def __init__(self, utilisateur):
        super().__init__()
        self.u = utilisateur
        self.deconnecte = False
        self.setWindowTitle("STYLE SHOP PORT-BOUËT")
        self.setMinimumSize(1024, 700)  # redimensionnable, sans défilement horizontal
        t = jetons()

        self.recharger = False
        if utilisateur.est_admin:
            self.page_parametres = PageParametres(utilisateur)
            self.page_parametres.theme_change.connect(self._recharger_theme)
            entrees = [("Caisse", "caisse", PageCaisse()),
                       ("Catalogue", "catalogue", PageCatalogue()),
                       ("Tableau de bord", "dashboard", PageDashboard()),
                       ("Utilisateurs", "utilisateurs", PageUtilisateurs()),
                       ("Paramètres", "parametres", self.page_parametres)]
        else:  # gestionnaire : Caisse et Stock uniquement
            entrees = [("Caisse", "caisse", PageCaisse()),
                       ("Stock", "stock", PageStock())]

        menu = QFrame()
        menu.setObjectName("menu")
        menu.setFixedWidth(240)
        ml = QVBoxLayout(menu)
        ml.setContentsMargins(12, 20, 12, 16)
        ml.setSpacing(8)
        nom = QLabel("STYLE SHOP\nPORT-BOUËT")
        nom.setProperty("role", "titre")
        ml.addWidget(nom)
        ml.addSpacing(16)

        self.pages = QStackedWidget()
        groupe = QButtonGroup(self)
        groupe.setExclusive(True)
        for i, (libelle, ico, page) in enumerate(entrees):
            b = QPushButton(" " + libelle)
            b.setProperty("menu", True)
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.setIcon(icone(ico, t["texte_primaire"], 20))
            b.setAccessibleName(libelle)
            b.setToolTip(f"Ouvrir : {libelle}")
            groupe.addButton(b, i)
            ml.addWidget(b)
            self.pages.addWidget(page)
        groupe.button(0).setChecked(True)
        groupe.idClicked.connect(self.pages.setCurrentIndex)
        ml.addStretch(1)

        u_nom = QLabel(utilisateur.nom_utilisateur)
        u_nom.setStyleSheet("font-weight: 600;")
        u_role = QLabel("Administrateur" if utilisateur.est_admin else "Gestionnaire")
        u_role.setProperty("role", "aide")
        ml.addWidget(u_nom)
        ml.addWidget(u_role)
        out = QPushButton(" Déconnexion")
        out.setProperty("menu", True)
        out.setCursor(Qt.PointingHandCursor)
        out.setIcon(icone("deconnexion", t["texte_primaire"], 20))
        out.setAccessibleName("Déconnexion")
        out.setToolTip("Se déconnecter")
        out.clicked.connect(self._se_deconnecter)
        ml.addWidget(out)

        centre = QWidget()
        cl = QHBoxLayout(centre)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(0)
        cl.addWidget(menu)
        cl.addWidget(self.pages, 1)
        self.setCentralWidget(centre)

        if utilisateur.est_admin:
            QTimer.singleShot(400, self._alerte_demarrage)

    def _alerte_demarrage(self):
        """Module 4 : nombre d'articles en stock faible au démarrage de l'administrateur."""
        try:
            n = articles.nb_stock_faible()
        except ErreurBaseDeDonnees:
            return
        if n > 0:
            QMessageBox.warning(self, "Stock faible",
                f"{n} article{'s sont' if n > 1 else ' est'} en stock faible ou épuisé{'s' if n > 1 else ''}. "
                "Ouvrez le Catalogue pour les voir (lignes en rouge).")

    def _recharger_theme(self):
        self.recharger = True
        self.close()

    def _se_deconnecter(self):
        self.deconnecte = True
        self.close()
