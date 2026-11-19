"""Crée 2 comptes de démo (hash bcrypt généré ici, jamais de mot de passe en clair en base).
Usage : python scripts/creer_comptes_demo.py  (à lancer depuis la racine du projet)"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.connexion import ouvrir
from services.auth import hacher

COMPTES = [("admin_demo", "Admin2025demo", "admin"), ("vendeur_demo", "Vendeur2025demo", "gestionnaire")]
conn = ouvrir("admin")
cur = conn.cursor()
for nom, mdp, role in COMPTES:
    cur.execute("INSERT IGNORE INTO utilisateurs (nom_utilisateur, mot_de_passe_hash, role, actif, doit_changer_mdp) "
                "VALUES (%s, %s, %s, 1, 1)", (nom, hacher(mdp), role))
    print(f"{nom} / {mdp} ({role}) : changement du mot de passe exigé à la première connexion")
conn.close()
