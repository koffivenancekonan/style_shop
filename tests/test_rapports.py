"""Tests sans MySQL : bénéfice, chiffre d'affaires, valeur du stock, périodes."""
from datetime import date, datetime
from models.utilisateur import Utilisateur
import pytest
from services import auth, rapports

LIGNES = [(20000, 13000, 2), (9000, 6000, 1), (6000, 7000, 1)]  # la dernière est vendue à perte


def test_benefice_somme_des_marges():
    assert rapports.benefice_lignes(LIGNES) == 14000 + 3000 - 1000


def test_chiffre_d_affaires():
    assert rapports.ca_lignes(LIGNES) == 40000 + 9000 + 6000


def test_benefice_utilise_le_prix_d_achat_de_la_ligne():
    # un changement de prix ultérieur ne modifie pas une vente passée : on calcule avec les prix copiés
    assert rapports.benefice_lignes([(15000, 10000, 1)]) == 5000


def test_valeur_du_stock():
    stock = [{"prix_achat_reel": 10000, "quantite_stock": 3}, {"prix_achat_reel": 7000, "quantite_stock": 0},
             {"prix_achat_reel": 2500, "quantite_stock": 10}]
    assert rapports.valeur_stock(stock) == 30000 + 0 + 25000


def test_bornes_incluent_le_dernier_jour():
    d, f = rapports.bornes(date(2026, 11, 1), date(2026, 11, 3))
    assert d == datetime(2026, 11, 1) and f == datetime(2026, 11, 4)


def test_libelles():
    assert rapports.libelle("jour", date(2026, 11, 9)) == "09/11/2026"
    assert rapports.libelle("semaine", 202645) == "S45 2026"
    assert rapports.libelle("mois", 202611) == "nov. 2026"
    assert rapports.libelle("annee", 2026) == "2026"


def test_jours_sans_vente_completes():
    rows = [{"cle": date(2026, 11, 2), "ca": 5000, "benefice": 1000, "nb_ventes": 1, "libelle": "", "libelle_court": ""}]
    sortie = rapports.completer_jours(rows, date(2026, 11, 1), date(2026, 11, 3))
    assert [r["ca"] for r in sortie] == [0, 5000, 0]


def test_gestionnaire_bloque_sur_les_rapports():
    auth.definir_utilisateur(Utilisateur(2, "vendeur", "gestionnaire", False))
    for appel in (rapports.cartes, rapports.stock_par_categorie,
                  lambda: rapports.ventes_par_periode("jour", date(2026, 11, 1), date(2026, 11, 2))):
        with pytest.raises(auth.AccesRefuse):
            appel()
    auth.definir_utilisateur(None)
