"""Authentification, hachage bcrypt et contrôle des rôles."""
import functools
import secrets
import bcrypt
from database.connexion import ouvrir, ErreurBaseDeDonnees, traduire_erreur
from models.utilisateur import Utilisateur


class ErreurAuthentification(Exception):
    pass


class AccesRefuse(Exception):
    pass


# Hash factice : vérifié même si l'utilisateur n'existe pas (temps de réponse constant)
_HASH_FACTICE = bcrypt.hashpw(b"factice", bcrypt.gensalt(12)).decode()


def hacher(mot_de_passe: str) -> str:
    return bcrypt.hashpw(mot_de_passe.encode("utf-8"), bcrypt.gensalt(12)).decode()


def verifier(mot_de_passe: str, hash_stocke: str) -> bool:
    try:
        return bcrypt.checkpw(mot_de_passe.encode("utf-8"), hash_stocke.encode("utf-8"))
    except ValueError:
        return False


def valider_nouveau_mdp(mdp: str, ancien_hash: str | None = None) -> str | None:
    """Retourne un message d'erreur en français, ou None si le mot de passe est valide."""
    if len(mdp) < 8:
        return "Le mot de passe doit contenir au moins 8 caractères."
    if len(mdp.encode("utf-8")) > 72:
        return "Le mot de passe est trop long (72 caractères maximum)."
    if not any(c.isdigit() for c in mdp) or not any(c.isalpha() for c in mdp):
        return "Utilisez au moins une lettre et un chiffre."
    if ancien_hash and verifier(mdp, ancien_hash):
        return "Le nouveau mot de passe doit être différent de l'ancien."
    return None


def authentifier(nom: str, mot_de_passe: str) -> Utilisateur:
    """Vérifie les identifiants via la connexion vendeur (procédure obtenir_utilisateur)."""
    conn = ouvrir("vendeur")
    try:
        cur = conn.cursor(dictionary=True)
        cur.callproc("obtenir_utilisateur", [nom.strip()])
        ligne = next((r.fetchone() for r in cur.stored_results()), None)
    except Exception as e:
        raise traduire_erreur(e) from e
    finally:
        conn.close()
    hash_stocke = ligne["mot_de_passe_hash"] if ligne else _HASH_FACTICE
    ok = verifier(mot_de_passe, hash_stocke)
    if not ligne or not ok or not ligne["actif"]:
        raise ErreurAuthentification("Identifiant ou mot de passe incorrect.")
    return Utilisateur(ligne["id"], ligne["nom_utilisateur"], ligne["role"],
                       bool(ligne["doit_changer_mdp"]), ligne["mot_de_passe_hash"])


def changer_mot_de_passe(utilisateur: Utilisateur, nouveau: str) -> None:
    erreur = valider_nouveau_mdp(nouveau, utilisateur.mot_de_passe_hash)
    if erreur:
        raise ErreurAuthentification(erreur)
    nouveau_hash = hacher(nouveau)
    conn = ouvrir("vendeur")
    try:
        cur = conn.cursor()
        cur.callproc("changer_mot_de_passe", [utilisateur.id, utilisateur.mot_de_passe_hash, nouveau_hash])
        modifie = next((r.fetchone()[0] for r in cur.stored_results()), 0)
    except Exception as e:
        raise traduire_erreur(e) from e
    finally:
        conn.close()
    if not modifie:
        raise ErreurAuthentification("Le changement a échoué. Reconnectez-vous et réessayez.")
    utilisateur.mot_de_passe_hash = nouveau_hash
    utilisateur.doit_changer_mdp = False


def creer_admin_defaut() -> str | None:
    """Premier lancement : crée le compte 'admin' s'il n'existe aucun administrateur.
    Retourne le mot de passe temporaire généré (affiché une seule fois), sinon None."""
    conn = ouvrir("admin")
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM utilisateurs WHERE role = %s", ("admin",))
        if cur.fetchone()[0] > 0:
            return None
        temporaire = secrets.token_urlsafe(9)
        cur.execute(
            "INSERT INTO utilisateurs (nom_utilisateur, mot_de_passe_hash, role, actif, doit_changer_mdp) "
            "VALUES (%s, %s, 'admin', 1, 1)", ("admin", hacher(temporaire)))
        return temporaire
    except Exception as e:
        raise traduire_erreur(e) from e
    finally:
        conn.close()


# --- Contrôle des rôles côté code (revérifié sur chaque fonction sensible) ---
_courant: Utilisateur | None = None


def definir_utilisateur(u: Utilisateur | None) -> None:
    global _courant
    _courant = u


def utilisateur_courant() -> Utilisateur | None:
    return _courant


def exiger_role(*roles: str):
    """Décorateur : refuse l'appel si l'utilisateur connecté n'a pas l'un des rôles."""
    def deco(fonction):
        @functools.wraps(fonction)
        def enveloppe(*a, **k):
            if _courant is None or _courant.role not in roles:
                raise AccesRefuse("Action réservée à l'administrateur.")
            return fonction(*a, **k)
        return enveloppe
    return deco
