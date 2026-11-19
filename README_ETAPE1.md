# Étape 1 : schéma MySQL + authentification

## Installation (Windows)
1. Installer Python 3.11+ (cocher "Add to PATH") et XAMPP.
2. Dans le dossier du projet :
   python -m venv venv && venv\Scripts\activate && pip install -r requirements.txt
3. Copier `.env.example` en `.env`.

## Base de données
1. Panneau XAMPP : démarrer **MySQL** uniquement (Apache inutile pour l'application).
2. Ouvrir http://localhost/phpmyadmin > onglet **Importer** > `database/schema.sql` > Exécuter.
3. (Optionnel) Importer `database/donnees_demo.sql` de la même façon.
4. Pour changer les mots de passe MySQL : modifier les 2 lignes CREATE USER avant l'import
   (ou onglet "Comptes d'utilisateurs"), puis reporter les valeurs dans `.env`.

## Lancer
python main.py   -> au 1er lancement, une fenêtre affiche le mot de passe temporaire du compte "admin".

## Tester l'étape 1
- Tests unitaires : `python -m pytest tests -v`
- Arrêter MySQL puis lancer l'app : message "Démarrez MySQL dans le panneau de contrôle XAMPP".
- Connexion avec admin : changement de mot de passe obligatoire, puis fenêtre "Connecté : admin (admin)".
- 5 mauvais mots de passe : pause de 30 s.
- Sécurité côté MySQL (phpMyAdmin > SQL, connecté en style_vendeur) :
  `SELECT prix_achat_reel FROM articles;`  -> doit être REFUSÉ
  `SELECT * FROM vue_articles_vendeur;`    -> doit fonctionner, sans colonnes d'achat.
