"""Logique métier des articles : lecture, validation, création, modification, suppression/archivage."""
from database.connexion import ErreurBaseDeDonnees, ouvrir, traduire_erreur
from services.auth import exiger_role
from utils.format import format_fcfa, nombre

CATEGORIES_DEFAUT = ["T-shirt", "Jean", "Bermuda", "Body", "Chaussure", "Accessoire"]
OBLIGATOIRES = {"nom": "le nom de l'article", "categorie": "la catégorie", "taille": "la taille",
                "couleur": "la couleur", "marque": "la marque"}
PRIX = ["prix_achat_min", "prix_achat_max", "prix_achat_reel", "prix_vente"]


class ErreurValidation(Exception):
    def __init__(self, erreurs: dict):
        super().__init__("Données invalides")
        self.erreurs = erreurs


def _exec(profil: str, sql: str, params=(), lecture: bool = True):
    """Requête paramétrée (jamais de concaténation de valeurs)."""
    conn = ouvrir(profil)
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(sql, params)
        return cur.fetchall() if lecture else (cur.lastrowid, cur.rowcount)
    except ErreurBaseDeDonnees:
        raise
    except Exception as e:
        raise traduire_erreur(e) from e
    finally:
        conn.close()


# ---------- Calculs et validation (sans base de données) ----------
def benefice_unitaire(prix_vente: int, prix_achat_reel: int) -> int:
    return prix_vente - prix_achat_reel


def valider(d: dict) -> dict:
    """Retourne {champ: message en français}. Dictionnaire vide = données valides."""
    e = {}
    for champ, lib in OBLIGATOIRES.items():
        if not str(d.get(champ) or "").strip():
            e[champ] = f"Saisissez {lib}."
    if len(str(d.get("nom") or "")) > 120:
        e["nom"] = "Le nom est trop long (120 caractères maximum)."
    for champ in PRIX:
        if d.get(champ) is None:
            e[champ] = "Saisissez un montant en FCFA (chiffres uniquement)."
    if d.get("quantite_stock") is None:
        e["quantite_stock"] = "Saisissez une quantité (0 ou plus)."
    mn, mx, rl = d.get("prix_achat_min"), d.get("prix_achat_max"), d.get("prix_achat_reel")
    if mn is not None and mx is not None:
        if mn > mx:
            e["prix_achat_max"] = f"Le prix d'achat maximum doit être supérieur ou égal au minimum ({format_fcfa(mn)})."
        elif rl is not None and not (mn <= rl <= mx):
            e["prix_achat_reel"] = f"Le prix d'achat doit être compris entre {nombre(mn)} et {format_fcfa(mx)}."
    return e


def avertissement_prix(d: dict) -> str | None:
    pv, rl = d.get("prix_vente"), d.get("prix_achat_reel")
    if pv is not None and rl is not None and pv < rl:
        return f"Attention : le prix de vente est inférieur au coût de revient ({format_fcfa(rl)}). Vous vendrez à perte."
    return None


# ---------- Lecture ----------
def seuil() -> int:
    """Seuil de stock faible (lisible par les deux rôles via une vue)."""
    lignes = _exec("vendeur", "SELECT valeur FROM vue_parametres_vendeur WHERE cle = %s", ("seuil_stock_faible",))
    try:
        return int(lignes[0]["valeur"])
    except (IndexError, ValueError, KeyError):
        return 5


def categories() -> list[str]:
    lignes = _exec("vendeur", "SELECT DISTINCT categorie FROM vue_articles_vendeur ORDER BY categorie")
    existantes = [l["categorie"] for l in lignes]
    return CATEGORIES_DEFAUT + sorted(c for c in existantes if c not in CATEGORIES_DEFAUT)


def _filtre(recherche: str, categorie: str | None):
    sql, params = "", []
    if recherche.strip():
        like = f"%{recherche.strip()}%"
        sql += " AND (nom LIKE %s OR marque LIKE %s OR categorie LIKE %s)"
        params += [like, like, like]
    if categorie:
        sql += " AND categorie = %s"
        params.append(categorie)
    return sql, params


@exiger_role("admin")
def lister_admin(recherche: str = "", categorie: str | None = None) -> list[dict]:
    """Catalogue complet avec prix d'achat : administrateur uniquement."""
    filtre, params = _filtre(recherche, categorie)
    return _exec("admin",
        "SELECT id, nom, categorie, taille, couleur, marque, prix_achat_min, prix_achat_max, "
        "prix_achat_reel, prix_vente, quantite_stock FROM articles WHERE actif = 1" + filtre + " ORDER BY nom",
        params)


def lister_vendeur(recherche: str = "", categorie: str | None = None) -> list[dict]:
    """Stock sans aucune donnée d'achat (la vue MySQL ne les contient pas)."""
    filtre, params = _filtre(recherche, categorie)
    return _exec("vendeur",
        "SELECT id, nom, categorie, taille, couleur, marque, prix_vente, quantite_stock "
        "FROM vue_articles_vendeur WHERE 1 = 1" + filtre + " ORDER BY nom", params)


@exiger_role("admin")
def nb_stock_faible() -> int:
    n = seuil()
    return _exec("admin", "SELECT COUNT(*) AS n FROM articles WHERE actif = 1 AND quantite_stock < %s", (n,))[0]["n"]


# ---------- Écriture (administrateur uniquement) ----------
_CHAMPS = ["nom", "categorie", "taille", "couleur", "marque", "prix_achat_min", "prix_achat_max",
           "prix_achat_reel", "prix_vente", "quantite_stock"]


def _nettoyer(d: dict) -> list:
    erreurs = valider(d)
    if erreurs:
        raise ErreurValidation(erreurs)
    return [d[c].strip() if isinstance(d[c], str) else d[c] for c in _CHAMPS]


@exiger_role("admin")
def creer(d: dict) -> int:
    valeurs = _nettoyer(d)
    id_, _ = _exec("admin", "INSERT INTO articles (" + ", ".join(_CHAMPS) + ") VALUES (" +
                   ", ".join(["%s"] * len(_CHAMPS)) + ")", valeurs, lecture=False)
    return id_


@exiger_role("admin")
def modifier(id_article: int, d: dict) -> None:
    valeurs = _nettoyer(d)
    _exec("admin", "UPDATE articles SET " + ", ".join(f"{c} = %s" for c in _CHAMPS) + " WHERE id = %s",
          valeurs + [id_article], lecture=False)


@exiger_role("admin")
def a_ete_vendu(id_article: int) -> bool:
    return _exec("admin", "SELECT COUNT(*) AS n FROM lignes_vente WHERE article_id = %s", (id_article,))[0]["n"] > 0


@exiger_role("admin")
def supprimer(id_article: int) -> str:
    """Supprime l'article, ou l'archive s'il a déjà été vendu (historique conservé). Retourne 'supprime' ou 'archive'."""
    if a_ete_vendu(id_article):
        _exec("admin", "UPDATE articles SET actif = 0 WHERE id = %s", (id_article,), lecture=False)
        return "archive"
    _exec("admin", "DELETE FROM articles WHERE id = %s", (id_article,), lecture=False)
    return "supprime"
