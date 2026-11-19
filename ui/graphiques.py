"""Graphiques Matplotlib (sans dépendance à Qt). Titres, axes nommés, légende, étiquettes, FCFA, motifs."""
from matplotlib.ticker import FuncFormatter
from utils.format import nombre

NOMS = {"jour": "jour", "semaine": "semaine", "mois": "mois", "annee": "année"}


def _styler(ax, t, titre, xlabel, ylabel):
    ax.set_facecolor(t["carte"])
    ax.set_title(titre, color=t["texte"], fontsize=11, fontweight="bold")
    ax.set_xlabel(xlabel, color=t["texte"], fontsize=9)
    ax.set_ylabel(ylabel, color=t["texte"], fontsize=9)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: nombre(v)))  # séparateur de milliers
    ax.tick_params(colors=t["texte"], labelsize=8)
    for s in ax.spines.values():
        s.set_color(t["bordure"])
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", color=t["bordure"], linewidth=0.6)
    ax.set_axisbelow(True)


def _xticks(ax, libelles, t):
    ax.set_xticks(range(len(libelles)))
    long = len(libelles) > 6
    ax.set_xticklabels(libelles, rotation=45 if long else 0, ha="right" if long else "center", color=t["texte"])


def tracer_benefices(fig, rows: list[dict], gran: str, t: dict) -> list[str]:
    """Barres groupées : chiffre d'affaires (hachuré) et bénéfice net (plein). Retourne les textes d'info-bulle."""
    fig.clear()
    fig.set_facecolor(t["carte"])
    ax = fig.add_subplot(111)
    n, w = len(rows), 0.38
    xs = list(range(n))
    ca = [r["ca"] for r in rows]
    be = [r["benefice"] for r in rows]
    b1 = ax.bar([x - w / 2 for x in xs], ca, w, label="Chiffre d'affaires", color=t["texte2"],
                hatch="//", edgecolor=t["carte"], linewidth=0)
    b2 = ax.bar([x + w / 2 for x in xs], be, w, label="Bénéfice net", color=t["accent"])
    if n <= 5:  # étiquettes de valeurs (au-delà : info-bulles au survol)
        ax.bar_label(b1, labels=[nombre(v) for v in ca], fontsize=7, padding=2, color=t["texte"])
        ax.bar_label(b2, labels=[nombre(v) for v in be], fontsize=7, padding=2, color=t["texte"])
    ax.axhline(0, color=t["texte2"], linewidth=0.8)
    _xticks(ax, [r["libelle_court"] for r in rows], t)
    _styler(ax, t, f"Chiffre d'affaires et bénéfice net par {NOMS[gran]}", "Période", "Montant (FCFA)")
    ax.legend(frameon=False, labelcolor=t["texte"], fontsize=8, loc="upper left")
    return [f"{r['libelle']}\nChiffre d'affaires : {nombre(r['ca'])} FCFA\nBénéfice net : {nombre(r['benefice'])} FCFA"
            for r in rows]


def tracer_stock(fig, rows: list[dict], t: dict) -> list[str]:
    fig.clear()
    fig.set_facecolor(t["carte"])
    ax = fig.add_subplot(111)
    vals = [r["valeur"] for r in rows]
    barres = ax.bar(range(len(rows)), vals, 0.6, color=t["accent"], label="Valeur du stock (prix d'achat × quantité)")
    if len(rows) <= 6:
        ax.bar_label(barres, labels=[nombre(v) for v in vals], fontsize=7, padding=2, color=t["texte"])
    _xticks(ax, [r["categorie"] for r in rows], t)
    _styler(ax, t, "Valeur du stock par catégorie", "Catégorie", "Valeur (FCFA)")
    ax.legend(frameon=False, labelcolor=t["texte"], fontsize=8, loc="upper right")
    return [f"{r['categorie']}\n{r['pieces']} pièce(s)\nValeur : {nombre(r['valeur'])} FCFA" for r in rows]
