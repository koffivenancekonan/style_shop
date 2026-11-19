"""Tests sans MySQL : hachage, validation des mots de passe, contrôle des rôles."""
import pytest
from models.utilisateur import Utilisateur
from services import auth


def test_hash_bcrypt_jamais_en_clair():
    h = auth.hacher("Secret123")
    assert h != "Secret123" and h.startswith("$2")
    assert auth.verifier("Secret123", h)
    assert not auth.verifier("autre", h)


@pytest.mark.parametrize("mdp", ["court1", "sansChiffreAA", "12345678"])
def test_mot_de_passe_refuse(mdp):
    assert auth.valider_nouveau_mdp(mdp) is not None


def test_nouveau_mdp_different_de_l_ancien():
    h = auth.hacher("Secret123")
    assert auth.valider_nouveau_mdp("Secret123", h) is not None
    assert auth.valider_nouveau_mdp("Autre12345", h) is None


def test_gestionnaire_bloque_sur_fonction_admin():
    @auth.exiger_role("admin")
    def voir_prix_achat():
        return "secret"
    auth.definir_utilisateur(Utilisateur(2, "vendeur", "gestionnaire", False))
    with pytest.raises(auth.AccesRefuse):
        voir_prix_achat()
    auth.definir_utilisateur(Utilisateur(1, "admin", "admin", False))
    assert voir_prix_achat() == "secret"
    auth.definir_utilisateur(None)
