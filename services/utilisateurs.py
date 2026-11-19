"""Gestion des comptes gestionnaires (administrateur uniquement). Aucun hash n'est jamais renvoyé à l'interface."""
import re
import secrets
import string
from database.connexion import ErreurBaseDeDonnees
from services.articles import ErreurValidation, _exec as executer
from services.auth import exiger_role, hacher, valider_nouveau_mdp

_NOM = re.compile(r"^[A-Za-z0-9._-]{3,50}$")


def valider_nom(nom: str) -> str | None:
    if not _NOM.match(nom.strip()):
        return "L'identifiant doit contenir 3 à 50 caractères : lettres, chiffres, point, tiret ou tiret bas."
    return None


def generer_mdp_temporaire(longueur: int = 10) -> str:
    """Mot de passe lisible (sans caractères ambigus), avec au moins une lettre et un chiffre."""
    lettres = "".join(c for c in string.ascii_letters if c not in "lIO")
    chiffres = "23456789"
    mdp = [secrets.choice(lettres), secrets.choice(chiffres)] + \
          [secrets.choice(lettres + chiffres) for _ in range(longueur - 2)]
    secrets.SystemRandom().shuffle(mdp)
    return "".join(mdp)


def _erreurs(nom: str | None, mdp: str | None) -> dict:
    e = {}
    if nom is not None and (m := valider_nom(nom)):
        e["nom"] = m
    if mdp is not None and (m := valider_nouveau_mdp(mdp)):
        e["mdp"] = m
    return e


def _ecrire(sql: str, params: list):
    try:
        return executer("admin", sql, params, lecture=False)
    except ErreurBaseDeDonnees as e:
        if "existe déjà" in str(e):
            raise ErreurValidation({"nom": "Cet identifiant existe déjà. Choisissez-en un autre."}) from e
        raise


@exiger_role("admin")
def lister() -> list[dict]:
    return executer("admin", "SELECT id, nom_utilisateur, role, actif, doit_changer_mdp, cree_le "
                             "FROM utilisateurs ORDER BY role, nom_utilisateur")


@exiger_role("admin")
def creer_gestionnaire(nom: str, mdp_temporaire: str) -> int:
    e = _erreurs(nom, mdp_temporaire)
    if e:
        raise ErreurValidation(e)
    id_, _ = _ecrire("INSERT INTO utilisateurs (nom_utilisateur, mot_de_passe_hash, role, actif, doit_changer_mdp) "
                     "VALUES (%s, %s, 'gestionnaire', 1, 1)", [nom.strip(), hacher(mdp_temporaire)])
    return id_


@exiger_role("admin")
def renommer(id_utilisateur: int, nom: str) -> None:
    e = _erreurs(nom, None)
    if e:
        raise ErreurValidation(e)
    _ecrire("UPDATE utilisateurs SET nom_utilisateur = %s WHERE id = %s AND role = 'gestionnaire'",
            [nom.strip(), id_utilisateur])


@exiger_role("admin")
def reinitialiser_mdp(id_utilisateur: int, mdp_temporaire: str) -> None:
    e = _erreurs(None, mdp_temporaire)
    if e:
        raise ErreurValidation(e)
    _ecrire("UPDATE utilisateurs SET mot_de_passe_hash = %s, doit_changer_mdp = 1 "
            "WHERE id = %s AND role = 'gestionnaire'", [hacher(mdp_temporaire), id_utilisateur])


@exiger_role("admin")
def definir_actif(id_utilisateur: int, actif: bool) -> None:
    """Désactive ou réactive un gestionnaire (un compte administrateur ne peut pas être désactivé ici)."""
    _ecrire("UPDATE utilisateurs SET actif = %s WHERE id = %s AND role = 'gestionnaire'",
            [1 if actif else 0, id_utilisateur])
