"""Reçu PDF au format ticket de caisse 80 mm (ReportLab). Aucun prix d'achat ni bénéfice."""
from reportlab.lib.units import mm
from reportlab.lib.utils import simpleSplit
from reportlab.pdfgen import canvas
from utils.format import NBSP, nombre

LARGEUR = 80 * mm
MARGE = 5 * mm
UTILE = LARGEUR - 2 * MARGE
NORMAL, GRAS = "Helvetica", "Helvetica-Bold"


def _m(n: int) -> str:
    return nombre(n).replace(NBSP, " ")


def _elements(recu: dict) -> list:
    """Construit la liste des éléments à dessiner : (type, ..., police, taille)."""
    e = [("c", "STYLE SHOP PORT-BOUËT", GRAS, 12), ("esp", 4),
         ("c", recu["date_heure"].strftime("%d/%m/%Y %H:%M"), NORMAL, 9),
         ("c", f"Reçu n° {recu['id']}", NORMAL, 9), ("sep",)]
    for l in recu["lignes"]:
        intitule = f"{l['nom']} ({l['taille']}, {l['couleur']})"
        for morceau in simpleSplit(intitule, NORMAL, 9, UTILE):
            e.append(("g", morceau, NORMAL, 9))
        e.append(("lr", f"{l['quantite']} x {_m(l['prix_unitaire'])} FCFA",
                  f"{_m(l['quantite'] * l['prix_unitaire'])} FCFA", NORMAL, 9))
        e.append(("esp", 4))
    e += [("sep",), ("lr", "Articles achetés", str(recu["nb_articles"]), NORMAL, 10), ("esp", 4),
          ("lr", "TOTAL À PAYER", f"{_m(recu['total'])} FCFA", GRAS, 11), ("sep",),
          ("c", "Merci de votre visite !", GRAS, 10), ("c", "À bientôt chez STYLE SHOP PORT-BOUËT", NORMAL, 8)]
    return e


def _hauteur(el: tuple) -> float:
    if el[0] == "esp":
        return el[1]
    if el[0] == "sep":
        return 8
    return el[-1] * 1.4


def generer_recu_pdf(recu: dict, chemin: str) -> str:
    """recu = {id, date_heure, total, nb_articles, lignes: [{nom, taille, couleur, quantite, prix_unitaire}]}"""
    els = _elements(recu)
    hauteur = sum(_hauteur(x) for x in els) + 2 * MARGE
    c = canvas.Canvas(chemin, pagesize=(LARGEUR, hauteur), pageCompression=0)
    c.setTitle(f"Reçu {recu['id']}")
    y = hauteur - MARGE
    for el in els:
        y -= _hauteur(el)
        t = el[0]
        if t == "c":
            c.setFont(el[2], el[3])
            c.drawCentredString(LARGEUR / 2, y + 3, el[1])
        elif t == "g":
            c.setFont(el[2], el[3])
            c.drawString(MARGE, y + 3, el[1])
        elif t == "lr":
            c.setFont(el[3], el[4])
            c.drawString(MARGE, y + 3, el[1])
            c.drawRightString(LARGEUR - MARGE, y + 3, el[2])
        elif t == "sep":
            c.setDash(1, 2)
            c.line(MARGE, y + 4, LARGEUR - MARGE, y + 4)
            c.setDash()
    c.showPage()
    c.save()
    return chemin
