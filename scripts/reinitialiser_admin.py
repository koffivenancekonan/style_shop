"""Réinitialise le compte 'admin' avec un nouveau mot de passe temporaire affiché dans la console.
Usage (depuis la racine du projet, venv activé, MySQL démarré) : python scripts/reinitialiser_admin.py"""
import os, secrets, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.connexion import ouvrir
from services.auth import hacher

temporaire = secrets.token_urlsafe(9)
conn = ouvrir("admin")
cur = conn.cursor()
cur.execute("UPDATE utilisateurs SET mot_de_passe_hash = %s, doit_changer_mdp = 1, actif = 1 "
            "WHERE nom_utilisateur = %s", (hacher(temporaire), "admin"))
if cur.rowcount == 0:
    cur.execute("INSERT INTO utilisateurs (nom_utilisateur, mot_de_passe_hash, role, actif, doit_changer_mdp) "
                "VALUES (%s, %s, 'admin', 1, 1)", ("admin", hacher(temporaire)))
conn.close()
print("\nCompte réinitialisé.")
print("Identifiant          : admin")
print("Mot de passe temporaire :", temporaire)
print("(Vous devrez le changer à la prochaine connexion.)\n")
