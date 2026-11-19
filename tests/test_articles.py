"""Tests sans MySQL : validation, bénéfice, formats, blocage du gestionnaire."""
import pytest
from models.utilisateur import Utilisateur
from services import articles, auth
from utils.format import format_fcfa

BON = {"nom": "Jean slim", "categorie": "Jean", "taille": "40", "couleur": "Bleu", "marque": "Levi's",
       "prix_achat_min": 8000, "prix_achat_max": 12000, "prix_achat_reel": 10000, "prix_vente": 15000,
       "quantite_stock": 5}


def test_article_valide():
    assert articles.valider(BON) == {}


def test_prix_reel_hors_intervalle():
    e = articles.valider({**BON, "prix_achat_reel": 13000})
    assert "entre 8\u00a0000 et 12\u00a0000\u00a0FCFA" in e["prix_achat_reel"]


def test_min_superieur_au_max():
    assert "prix_achat_max" in articles.valider({**BON, "prix_achat_min": 13000})


def test_champs_obligatoires_et_quantite():
    e = articles.valider({**BON, "nom": " ", "marque": "", "quantite_stock": None})
    assert {"nom", "marque", "quantite_stock"} <= set(e)


def test_benefice_unitaire():
    assert articles.benefice_unitaire(15000, 10000) == 5000
    assert articles.benefice_unitaire(8000, 10000) == -2000


def test_avertissement_vente_a_perte():
    assert articles.avertissement_prix({**BON, "prix_vente": 9000})
    assert articles.avertissement_prix(BON) is None


def test_format_fcfa():
    assert format_fcfa(15000) == "15\u00a0000\u00a0FCFA"


def test_gestionnaire_ne_peut_pas_lire_ni_modifier_le_catalogue():
    auth.definir_utilisateur(Utilisateur(2, "vendeur", "gestionnaire", False))
    for appel in (lambda: articles.lister_admin(), lambda: articles.creer(BON),
                  lambda: articles.modifier(1, BON), lambda: articles.supprimer(1)):
        with pytest.raises(auth.AccesRefuse):
            appel()
    auth.definir_utilisateur(None)
