"""Enregistrement des ventes : une seule transaction MySQL, verrouillage des articles, ROLLBACK en cas d'erreur."""
from database.connexion import ErreurBaseDeDonnees, ouvrir, traduire_erreur
from services.auth import exiger_role, utilisateur_courant


class ErreurStock(ErreurBaseDeDonnees):
    """Stock devenu insuffisant (ex. vente simultanée sur un autre poste)."""


@exiger_role("admin", "gestionnaire")
def enregistrer_vente(lignes: list[tuple[int, int]]) -> int:
    """lignes = [(id_article, quantité)]. Retourne l'identifiant de la vente.
    Tout est annulé si une seule ligne échoue (le stock ne peut jamais devenir négatif)."""
    if not lignes:
        raise ErreurBaseDeDonnees("Le panier est vide.")
    u = utilisateur_courant()
    conn = ouvrir("vendeur")
    try:
        conn.start_transaction()
        cur = conn.cursor()
        cur.execute("CALL creer_vente(%s, @vente_id)", (u.id,))
        cur.execute("SELECT @vente_id")
        vente_id = int(cur.fetchone()[0])
        for id_article, qte in sorted(lignes):  # ordre fixe : évite les blocages entre ventes simultanées
            cur.execute("CALL ajouter_ligne_vente(%s, %s, %s)", (vente_id, int(id_article), int(qte)))
        cur.execute("CALL finaliser_vente(%s)", (vente_id,))
        conn.commit()
        return vente_id
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        err = traduire_erreur(e)
        if "Stock insuffisant" in str(err):
            raise ErreurStock("Le stock d'un article a changé (une autre vente vient peut-être d'avoir lieu). "
                              "Rien n'a été enregistré : vérifiez les quantités et recommencez.") from e
        raise err from e
    finally:
        conn.close()


def lire_recu(vente_id: int) -> dict:
    """Données du reçu : jamais de prix d'achat ni de bénéfice."""
    conn = ouvrir("vendeur")
    try:
        cur = conn.cursor(dictionary=True)
        cur.callproc("lire_recu", [vente_id])
        lignes = next((r.fetchall() for r in cur.stored_results()), [])
    except Exception as e:
        raise traduire_erreur(e) from e
    finally:
        conn.close()
    if not lignes:
        raise ErreurBaseDeDonnees("Reçu introuvable.")
    return {"id": vente_id, "date_heure": lignes[0]["date_heure"], "total": lignes[0]["total"],
            "nb_articles": lignes[0]["nb_articles"],
            "lignes": [{k: l[k] for k in ("nom", "taille", "couleur", "quantite", "prix_unitaire")} for l in lignes]}
