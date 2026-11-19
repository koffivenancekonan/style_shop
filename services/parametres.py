"""Paramètres de la boutique (administrateur uniquement)."""
from services.articles import _exec as executer
from services.auth import exiger_role


def valider_seuil(texte: str) -> tuple[int | None, str | None]:
    t = str(texte).strip()
    if not t.isdigit() or not (1 <= int(t) <= 999):
        return None, "Saisissez un nombre entier entre 1 et 999."
    return int(t), None


@exiger_role("admin")
def definir_seuil(valeur: int) -> None:
    n, erreur = valider_seuil(str(valeur))
    if erreur:
        raise ValueError(erreur)
    executer("admin", "INSERT INTO parametres (cle, valeur) VALUES ('seuil_stock_faible', %s) "
                      "ON DUPLICATE KEY UPDATE valeur = VALUES(valeur)", [str(n)], lecture=False)
