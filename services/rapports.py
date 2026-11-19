"""Module 3 : rapports (administrateur uniquement). Bénéfices par période et valeur du stock."""
from datetime import date, datetime, time, timedelta
from services.articles import _exec as executer, seuil
from services.auth import exiger_role

# Regroupements SQL (DATE, YEARWEEK, MONTH, YEAR). Constantes fixes : jamais de saisie utilisateur dans le SQL.
GROUPES = {
    "jour": "DATE(v.date_heure)",
    "semaine": "YEARWEEK(v.date_heure, 3)",
    "mois": "YEAR(v.date_heure) * 100 + MONTH(v.date_heure)",
    "annee": "YEAR(v.date_heure)",
}
MOIS = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."]
# CAST SIGNED : une vente à perte donne un bénéfice négatif (sinon MySQL refuse la soustraction UNSIGNED)
_CA = "SUM(CAST(l.quantite AS SIGNED) * CAST(l.prix_vente_unitaire AS SIGNED))"
_BENEF = ("SUM((CAST(l.prix_vente_unitaire AS SIGNED) - CAST(l.prix_achat_unitaire AS SIGNED)) "
          "* CAST(l.quantite AS SIGNED))")


# ---------- Calculs purs (testables sans base) ----------
def benefice_lignes(lignes) -> int:
    """lignes = [(prix_vente, prix_achat, quantité)] ; bénéfice = Σ (vente - achat) × quantité."""
    return sum((pv - pa) * q for pv, pa, q in lignes)


def ca_lignes(lignes) -> int:
    return sum(pv * q for pv, _pa, q in lignes)


def valeur_stock(articles) -> int:
    """Capital immobilisé = Σ prix d'achat réel × quantité restante."""
    return sum(a["prix_achat_reel"] * a["quantite_stock"] for a in articles)


def bornes(debut: date, fin: date) -> tuple[datetime, datetime]:
    """Intervalle [début 00:00, lendemain de fin 00:00[ : la date de fin est incluse."""
    return datetime.combine(debut, time.min), datetime.combine(fin + timedelta(days=1), time.min)


def libelle(gran: str, cle, court: bool = False) -> str:
    if gran == "jour":
        return cle.strftime("%d/%m" if court else "%d/%m/%Y")
    if gran == "semaine":
        return f"S{int(cle) % 100:02d} {int(cle) // 100}"
    if gran == "mois":
        return f"{MOIS[int(cle) % 100 - 1]} {int(cle) // 100}"
    return str(cle)


def completer_jours(rows: list[dict], debut: date, fin: date) -> list[dict]:
    """Ajoute les jours sans vente (à zéro) pour que le graphique ne cache pas les jours vides."""
    par_jour = {r["cle"]: r for r in rows}
    sortie, j = [], debut
    while j <= fin:
        sortie.append(par_jour.get(j) or {"cle": j, "ca": 0, "benefice": 0, "nb_ventes": 0,
                                          "libelle": libelle("jour", j), "libelle_court": libelle("jour", j, True)})
        j += timedelta(days=1)
    return sortie


# ---------- Requêtes ----------
@exiger_role("admin")
def ventes_par_periode(gran: str, debut: date, fin: date) -> list[dict]:
    expr = GROUPES[gran]
    d, f = bornes(debut, fin)
    lignes = executer("admin",
        f"SELECT {expr} AS cle, {_CA} AS ca, {_BENEF} AS benefice, COUNT(DISTINCT v.id) AS nb_ventes "
        "FROM ventes v JOIN lignes_vente l ON l.vente_id = v.id "
        f"WHERE v.date_heure >= %s AND v.date_heure < %s GROUP BY {expr} ORDER BY {expr}", (d, f))
    rows = [{"cle": l["cle"], "ca": int(l["ca"]), "benefice": int(l["benefice"]), "nb_ventes": int(l["nb_ventes"]),
             "libelle": libelle(gran, l["cle"]), "libelle_court": libelle(gran, l["cle"], True)} for l in lignes]
    if gran == "jour" and (fin - debut).days <= 62:
        rows = completer_jours(rows, debut, fin)
    return rows


@exiger_role("admin")
def cartes() -> dict:
    """Cartes de synthèse : chiffre d'affaires et bénéfice du jour, stock, alertes."""
    v = executer("admin",
        f"SELECT COALESCE({_CA}, 0) AS ca, COALESCE({_BENEF}, 0) AS benefice "
        "FROM ventes v JOIN lignes_vente l ON l.vente_id = v.id "
        "WHERE v.date_heure >= CURDATE() AND v.date_heure < CURDATE() + INTERVAL 1 DAY")[0]
    s = executer("admin",
        "SELECT COALESCE(SUM(quantite_stock), 0) AS pieces, COUNT(*) AS refs, "
        "COALESCE(SUM(quantite_stock < %s), 0) AS alertes FROM articles WHERE actif = 1", (seuil(),))[0]
    return {"ca_jour": int(v["ca"]), "benefice_jour": int(v["benefice"]), "pieces": int(s["pieces"]),
            "references": int(s["refs"]), "alertes": int(s["alertes"])}


@exiger_role("admin")
def stock_par_categorie() -> list[dict]:
    """Valeur du stock par catégorie (articles actifs)."""
    lignes = executer("admin",
        "SELECT categorie, SUM(prix_achat_reel * quantite_stock) AS valeur, SUM(quantite_stock) AS pieces "
        "FROM articles WHERE actif = 1 GROUP BY categorie ORDER BY valeur DESC")
    return [{"categorie": l["categorie"], "valeur": int(l["valeur"]), "pieces": int(l["pieces"])} for l in lignes]
