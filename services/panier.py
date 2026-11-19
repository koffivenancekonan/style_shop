"""Panier de la caisse : logique pure (sans interface), avec contrôle du stock disponible."""


class ErreurPanier(Exception):
    pass


class Panier:
    def __init__(self):
        self._lignes: dict[int, dict] = {}

    def _verifier(self, article: dict, qte: int):
        if qte < 1:
            raise ErreurPanier("La quantité doit être d'au moins 1.")
        stock = article["quantite_stock"]
        if stock == 0:
            raise ErreurPanier(f"« {article['nom']} » est épuisé.")
        if qte > stock:
            raise ErreurPanier(f"Stock insuffisant pour « {article['nom']} » : il n'en reste que {stock}.")

    def ajouter(self, article: dict, qte: int = 1) -> None:
        actuel = self._lignes.get(article["id"], {}).get("qte", 0)
        self._verifier(article, actuel + qte)
        self._lignes[article["id"]] = {"article": article, "qte": actuel + qte}

    def definir_qte(self, id_article: int, qte: int) -> None:
        if qte <= 0:
            self.retirer(id_article)
            return
        ligne = self._lignes[id_article]
        self._verifier(ligne["article"], qte)
        ligne["qte"] = qte

    def retirer(self, id_article: int) -> None:
        self._lignes.pop(id_article, None)

    def vider(self) -> None:
        self._lignes.clear()

    def lignes(self) -> list[dict]:
        return list(self._lignes.values())

    @property
    def est_vide(self) -> bool:
        return not self._lignes

    @property
    def total(self) -> int:
        return sum(l["qte"] * l["article"]["prix_vente"] for l in self._lignes.values())

    @property
    def nb_articles(self) -> int:
        return sum(l["qte"] for l in self._lignes.values())
