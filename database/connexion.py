"""Connexions MySQL (XAMPP) avec messages d'erreur en français."""
import mysql.connector
from mysql.connector import errors
from config.settings import charger_config


class ErreurBaseDeDonnees(Exception):
    """Erreur affichable telle quelle à l'utilisateur."""


def _traduire(e: errors.Error) -> ErreurBaseDeDonnees:
    code = getattr(e, "errno", None)
    if code in (2003, 2002, 2006, 2013):
        return ErreurBaseDeDonnees("MySQL est inaccessible. Démarrez MySQL dans le panneau de contrôle XAMPP, puis réessayez.")
    if code == 1045:
        return ErreurBaseDeDonnees("MySQL a refusé les identifiants. Vérifiez le fichier .env.")
    if code == 1049:
        return ErreurBaseDeDonnees("La base style_shop_db est introuvable. Importez database/schema.sql dans phpMyAdmin.")
    if code == 1062:
        return ErreurBaseDeDonnees("Cette valeur existe déjà (doublon).")
    if code == 1644:  # SIGNAL SQLSTATE 45000 : message métier
        return ErreurBaseDeDonnees(e.msg)
    return ErreurBaseDeDonnees(f"Erreur de base de données : {e.msg}")


def ouvrir(profil: str):
    """Ouvre une connexion. profil = 'admin' (tous droits) ou 'vendeur' (droits restreints)."""
    cfg = charger_config()
    p = cfg.admin if profil == "admin" else cfg.vendeur
    try:
        return mysql.connector.connect(
            host=cfg.hote, port=cfg.port, database=cfg.base,
            user=p.utilisateur, password=p.mot_de_passe,
            charset="utf8mb4", connection_timeout=5, autocommit=True,
        )
    except errors.Error as e:
        raise _traduire(e) from e


def verifier_mysql() -> None:
    """Vérifie au démarrage que MySQL répond ; lève ErreurBaseDeDonnees sinon."""
    ouvrir("vendeur").close()


def traduire_erreur(e: Exception) -> ErreurBaseDeDonnees:
    return _traduire(e) if isinstance(e, errors.Error) else ErreurBaseDeDonnees(str(e))
