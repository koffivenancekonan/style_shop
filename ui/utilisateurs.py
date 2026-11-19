"""Gestion des comptes gestionnaires (administrateur uniquement)."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QApplication, QDialog, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
                               QPushButton, QVBoxLayout, QWidget)
from database.connexion import ErreurBaseDeDonnees
from services import utilisateurs
from services.articles import ErreurValidation
from services.auth import AccesRefuse
from ui.icons import icone
from ui.tables import creer_table, texte
from ui.theme import jetons
from ui.widgets import ChampForm, confirmer


def _bouton(libelle, ico, couleur, action, role=None):
    b = QPushButton(" " + libelle)
    b.setIcon(icone(ico, couleur, 18))
    b.setCursor(Qt.PointingHandCursor)
    b.setAccessibleName(libelle)
    if role:
        b.setProperty("role", role)
    b.clicked.connect(action)
    return b


class DialogUtilisateur(QDialog):
    """mode = 'creer' (identifiant + mot de passe), 'modifier' (identifiant) ou 'mdp' (nouveau mot de passe)."""
    def __init__(self, parent, mode: str, utilisateur: dict | None = None):
        super().__init__(parent)
        self.mode, self.u = mode, utilisateur
        self.mdp_saisi = None
        titres = {"creer": "Ajouter un gestionnaire", "modifier": "Modifier le compte",
                  "mdp": "Réinitialiser le mot de passe"}
        self.setWindowTitle(titres[mode])
        self.setMinimumWidth(460)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(12)
        t = QLabel(titres[mode])
        t.setProperty("role", "titre")
        lay.addWidget(t)
        self.champs = {}
        if mode in ("creer", "modifier"):
            self.nom = QLineEdit(utilisateur["nom_utilisateur"] if utilisateur else "")
            self.nom.setAccessibleName("Identifiant")
            self.nom.editingFinished.connect(self._valider_nom)
            self.champs["nom"] = ChampForm("Identifiant", self.nom, aide="Lettres, chiffres, point, tiret ou tiret bas (3 à 50).")
            lay.addLayout(self.champs["nom"])
        else:
            lay.addWidget(QLabel(f"Compte : {utilisateur['nom_utilisateur']}"))
        if mode in ("creer", "mdp"):
            self.mdp = QLineEdit(utilisateurs.generer_mdp_temporaire())
            self.mdp.setAccessibleName("Mot de passe temporaire")
            self.champs["mdp"] = ChampForm("Mot de passe temporaire", self.mdp,
                aide="Communiquez-le au gestionnaire : il devra le changer à sa première connexion.")
            lay.addLayout(self.champs["mdp"])
            gen = QPushButton("Générer un autre mot de passe")
            gen.setCursor(Qt.PointingHandCursor)
            gen.setAccessibleName("Générer un autre mot de passe")
            gen.clicked.connect(lambda: self.mdp.setText(utilisateurs.generer_mdp_temporaire()))
            lay.addWidget(gen)
        annuler = QPushButton("Annuler")
        annuler.setCursor(Qt.PointingHandCursor)
        annuler.setAccessibleName("Annuler")
        annuler.clicked.connect(self.reject)
        libelle_ok = {"creer": "Créer le compte", "modifier": "Enregistrer", "mdp": "Réinitialiser le mot de passe"}[mode]
        ok = QPushButton(libelle_ok)
        ok.setProperty("role", "accent")
        ok.setCursor(Qt.PointingHandCursor)
        ok.setAccessibleName(libelle_ok)
        ok.setDefault(True)
        ok.clicked.connect(self._enregistrer)
        bas = QHBoxLayout()
        bas.addStretch(1)
        bas.addWidget(annuler)
        bas.addWidget(ok)
        lay.addLayout(bas)
        (self.nom if "nom" in self.champs else self.mdp).setFocus()

    def _valider_nom(self):
        m = utilisateurs.valider_nom(self.nom.text())
        self.champs["nom"].erreur(m) if m else self.champs["nom"].effacer()

    def _afficher(self, erreurs: dict):
        for n, c in self.champs.items():
            c.erreur(erreurs[n]) if n in erreurs else c.effacer()

    def _enregistrer(self):
        nom = self.nom.text().strip() if "nom" in self.champs else None
        mdp = self.mdp.text() if "mdp" in self.champs else None
        QApplication.setOverrideCursor(Qt.WaitCursor)  # le hachage bcrypt prend un instant
        try:
            if self.mode == "creer":
                utilisateurs.creer_gestionnaire(nom, mdp)
            elif self.mode == "modifier":
                utilisateurs.renommer(self.u["id"], nom)
            else:
                utilisateurs.reinitialiser_mdp(self.u["id"], mdp)
        except ErreurValidation as e:
            self._afficher(e.erreurs)
            return
        except (ErreurBaseDeDonnees, AccesRefuse) as e:
            QMessageBox.critical(self, "Enregistrement impossible", str(e))
            return
        finally:
            QApplication.restoreOverrideCursor()
        self.nom_saisi, self.mdp_saisi = nom, mdp
        self.accept()


class PageUtilisateurs(QWidget):
    def __init__(self):
        super().__init__()
        t = jetons()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(12)
        haut = QHBoxLayout()
        titre = QLabel("Utilisateurs")
        titre.setProperty("role", "titre")
        haut.addWidget(titre)
        haut.addStretch(1)
        haut.addWidget(_bouton("Ajouter un gestionnaire", "plus", t["texte_accent"], self._ajouter, "accent"))
        lay.addLayout(haut)
        aide = QLabel("Le gestionnaire peut vendre et consulter le stock, sans voir les prix d'achat ni les bénéfices.")
        aide.setProperty("role", "aide")
        lay.addWidget(aide)
        self.table = creer_table(["Identifiant", "Rôle", "État", "Mot de passe"])
        lay.addWidget(self.table, 1)
        bas = QHBoxLayout()
        bas.addStretch(1)
        self.b_modif = _bouton("Modifier", "modifier", t["texte"], self._modifier)
        self.b_mdp = _bouton("Réinitialiser le mot de passe", "cle", t["texte"], self._mdp)
        self.b_actif = _bouton("Désactiver", "interdit", t["texte"], self._basculer)
        for b in (self.b_modif, self.b_mdp, self.b_actif):
            bas.addWidget(b)
        lay.addLayout(bas)
        self.table.itemSelectionChanged.connect(self._maj_boutons)
        self.table.doubleClicked.connect(self._modifier)
        self._maj_boutons()

    def showEvent(self, e):
        super().showEvent(e)
        self.rafraichir()

    def _selection(self):
        l = self.table.selectionModel().selectedRows()
        return self.table.item(l[0].row(), 0).data(Qt.UserRole + 1) if l else None

    def _maj_boutons(self):
        u = self._selection()
        ok = bool(u) and u["role"] == "gestionnaire"  # les comptes administrateur ne se gèrent pas ici
        for b in (self.b_modif, self.b_mdp, self.b_actif):
            b.setEnabled(ok)
        t = jetons()
        if ok and not u["actif"]:
            self.b_actif.setText(" Réactiver")
            self.b_actif.setIcon(icone("coche", t["texte"], 18))
        else:
            self.b_actif.setText(" Désactiver")
            self.b_actif.setIcon(icone("interdit", t["texte"], 18))

    def rafraichir(self):
        try:
            lignes = utilisateurs.lister()
        except (ErreurBaseDeDonnees, AccesRefuse) as e:
            QMessageBox.critical(self, "Utilisateurs", str(e))
            return
        t = jetons()
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(lignes))
        for r, u in enumerate(lignes):
            c0 = texte(u["nom_utilisateur"])
            c0.setData(Qt.UserRole + 1, u)
            etat = texte("Actif" if u["actif"] else "Désactivé")
            if not u["actif"]:
                etat.setIcon(icone("interdit", t["danger"], 18))  # icône + texte, pas la couleur seule
            cells = (c0, texte("Administrateur" if u["role"] == "admin" else "Gestionnaire"), etat,
                     texte("À changer à la connexion" if u["doit_changer_mdp"] else "Défini"))
            for c, it in enumerate(cells):
                self.table.setItem(r, c, it)
        self.table.setSortingEnabled(True)
        self._maj_boutons()

    def _ajouter(self):
        d = DialogUtilisateur(self, "creer")
        if d.exec():
            QMessageBox.information(self, "Compte créé",
                f"Identifiant : {d.nom_saisi}\nMot de passe temporaire : {d.mdp_saisi}\n\n"
                "Notez-le et communiquez-le au gestionnaire : il devra le changer à sa première connexion.")
            self.rafraichir()

    def _modifier(self, *_):
        u = self._selection()
        if u and u["role"] == "gestionnaire" and DialogUtilisateur(self, "modifier", u).exec():
            self.rafraichir()

    def _mdp(self):
        u = self._selection()
        if not u:
            return
        d = DialogUtilisateur(self, "mdp", u)
        if d.exec():
            QMessageBox.information(self, "Mot de passe réinitialisé",
                f"Compte : {u['nom_utilisateur']}\nNouveau mot de passe temporaire : {d.mdp_saisi}\n\n"
                "Notez-le : le gestionnaire devra le changer à sa prochaine connexion.")
            self.rafraichir()

    def _basculer(self):
        u = self._selection()
        if not u:
            return
        if u["actif"] and not confirmer(self, "Désactiver le compte",
                f"Le compte « {u['nom_utilisateur']} » ne pourra plus se connecter. "
                "Ses ventes passées sont conservées. Vous pourrez le réactiver à tout moment.", "Désactiver le compte"):
            return
        try:
            utilisateurs.definir_actif(u["id"], not u["actif"])
        except (ErreurBaseDeDonnees, AccesRefuse) as e:
            QMessageBox.critical(self, "Utilisateurs", str(e))
            return
        self.rafraichir()
