"""Tests de la caisse : panier (stock), reçu PDF (jamais de prix d'achat), vente en base (si MySQL disponible)."""
import datetime
import pytest
from models.utilisateur import Utilisateur
from services import auth
from services.panier import ErreurPanier, Panier

JEAN = {"id": 1, "nom": "Jean slim", "marque": "Levi's", "taille": "40", "couleur": "Bleu",
        "prix_vente": 15000, "quantite_stock": 3}
TSHIRT = {"id": 2, "nom": "T-shirt", "marque": "Local", "taille": "M", "couleur": "Blanc",
          "prix_vente": 6000, "quantite_stock": 0}


def test_total_et_nombre_d_articles():
    p = Panier()
    p.ajouter(JEAN, 2)
    p.ajouter(JEAN, 1)
    assert p.total == 45000 and p.nb_articles == 3


def test_refus_quantite_superieure_au_stock():
    p = Panier()
    p.ajouter(JEAN, 3)
    with pytest.raises(ErreurPanier):
        p.ajouter(JEAN, 1)  # 4 > 3 en stock
    with pytest.raises(ErreurPanier):
        p.definir_qte(1, 4)


def test_article_epuise_refuse():
    with pytest.raises(ErreurPanier):
        Panier().ajouter(TSHIRT, 1)


def test_retrait_et_quantite_zero():
    p = Panier()
    p.ajouter(JEAN, 2)
    p.definir_qte(1, 0)
    assert p.est_vide


def test_recu_pdf_sans_prix_d_achat(tmp_path):
    pytest.importorskip("reportlab")
    from services.recu import generer_recu_pdf
    recu = {"id": 7, "date_heure": datetime.datetime(2026, 11, 9, 14, 30), "total": 21000, "nb_articles": 3,
            "lignes": [{"nom": "Jean slim", "taille": "40", "couleur": "Bleu", "quantite": 1, "prix_unitaire": 15000},
                       {"nom": "T-shirt", "taille": "M", "couleur": "Blanc", "quantite": 1, "prix_unitaire": 6000}]}
    chemin = generer_recu_pdf(recu, str(tmp_path / "recu.pdf"))
    data = open(chemin, "rb").read()
    assert data.startswith(b"%PDF") and b"TOTAL" in data
    assert b"achat" not in data.lower().replace(b"achet\xe9s", b"") and b"b\xe9n\xe9fice" not in data.lower()


def test_decrementation_du_stock_en_base():
    """Nécessite MySQL + schema.sql + maj_etape3.sql ; ignoré sinon. Nettoie ses données."""
    from database.connexion import ouvrir
    from services import ventes
    try:
        conn = ouvrir("admin")
    except Exception:
        pytest.skip("MySQL indisponible")
    cur = conn.cursor()
    cur.execute("SELECT MIN(id) FROM utilisateurs")
    uid = cur.fetchone()[0]
    if uid is None:
        conn.close()
        pytest.skip("Aucun utilisateur en base")
    cur.execute("INSERT INTO articles (nom, categorie, taille, couleur, marque, prix_achat_min, prix_achat_max, "
                "prix_achat_reel, prix_vente, quantite_stock) VALUES ('TEST_PYTEST','Test','M','Noir','X',5000,9000,7000,12000,5)")
    aid = cur.lastrowid
    auth.definir_utilisateur(Utilisateur(uid, "test", "gestionnaire", False))
    try:
        vid = ventes.enregistrer_vente([(aid, 2)])
        cur.execute("SELECT quantite_stock FROM articles WHERE id=%s", (aid,))
        assert cur.fetchone()[0] == 3
        cur.execute("SELECT prix_vente_unitaire, prix_achat_unitaire FROM lignes_vente WHERE vente_id=%s", (vid,))
        assert cur.fetchone() == (12000, 7000)  # prix copiés dans la ligne de vente
        with pytest.raises(ventes.ErreurStock):
            ventes.enregistrer_vente([(aid, 10)])
        cur.execute("SELECT quantite_stock FROM articles WHERE id=%s", (aid,))
        assert cur.fetchone()[0] == 3  # ROLLBACK : stock inchangé
    finally:
        auth.definir_utilisateur(None)
        cur.execute("SELECT DISTINCT vente_id FROM lignes_vente WHERE article_id=%s", (aid,))
        ids = [r[0] for r in cur.fetchall()]
        cur.execute("DELETE FROM lignes_vente WHERE article_id=%s", (aid,))
        for i in ids:
            cur.execute("DELETE FROM ventes WHERE id=%s", (i,))
        cur.execute("DELETE FROM articles WHERE id=%s", (aid,))
        conn.close()
