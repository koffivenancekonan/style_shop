"""Tests sans MySQL : identifiants, mots de passe temporaires, seuil, accès réservé à l'administrateur."""
import pytest
from models.utilisateur import Utilisateur
from services import auth, parametres, utilisateurs


@pytest.mark.parametrize("nom", ["ab", "avec espace", "", "x" * 51, "a;b", "é-vendeur"])
def test_identifiant_refuse(nom):
    assert utilisateurs.valider_nom(nom) is not None


@pytest.mark.parametrize("nom", ["vendeur1", "marie.k", "jean_p-2"])
def test_identifiant_accepte(nom):
    assert utilisateurs.valider_nom(nom) is None


def test_mot_de_passe_temporaire_respecte_la_regle():
    for _ in range(50):
        m = utilisateurs.generer_mdp_temporaire()
        assert len(m) == 10 and auth.valider_nouveau_mdp(m) is None


def test_seuil_valide():
    assert parametres.valider_seuil("5") == (5, None)
    assert parametres.valider_seuil("0")[1] is not None
    assert parametres.valider_seuil("abc")[1] is not None
    assert parametres.valider_seuil("1000")[1] is not None


def test_gestionnaire_ne_peut_pas_gerer_les_comptes():
    auth.definir_utilisateur(Utilisateur(2, "vendeur", "gestionnaire", False))
    for appel in (utilisateurs.lister, lambda: utilisateurs.creer_gestionnaire("abc", "Motdepasse1"),
                  lambda: utilisateurs.definir_actif(1, False), lambda: parametres.definir_seuil(3)):
        with pytest.raises(auth.AccesRefuse):
            appel()
    auth.definir_utilisateur(None)
