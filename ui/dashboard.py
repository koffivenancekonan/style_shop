"""Module 3 : tableau de bord (administrateur uniquement)."""
from PySide6.QtCore import QDate, QTimer, Qt
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (QApplication, QButtonGroup, QDateEdit, QFrame, QHBoxLayout, QLabel, QMessageBox,
                               QPushButton, QStackedWidget, QTabWidget, QToolTip, QVBoxLayout, QWidget)
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from database.connexion import ErreurBaseDeDonnees
from services import rapports
from services.auth import AccesRefuse
from ui.graphiques import tracer_benefices, tracer_stock
from ui.icons import icone
from ui.tables import NumItem, creer_table, texte
from ui.theme import jetons
from utils.format import format_fcfa, nombre

GRANS = [("Jour", "jour"), ("Semaine", "semaine"), ("Mois", "mois"), ("Année", "annee")]
DEFAUT_JOURS = {"jour": 13, "semaine": 83, "mois": 364, "annee": 1824}  # durée proposée avant aujourd'hui


class Carte(QFrame):
    """Carte de synthèse : titre, grande valeur, précision."""
    def __init__(self, titre: str):
        super().__init__()
        self.setProperty("carte", True)
        v = QVBoxLayout(self)
        v.setContentsMargins(16, 12, 16, 12)
        v.setSpacing(2)
        self.titre = QLabel(titre)
        self.titre.setProperty("role", "aide")
        self.valeur = QLabel("—")
        self.valeur.setStyleSheet("font-size: 24px; font-weight: 700;")
        self.sous = QLabel("")
        self.sous.setProperty("role", "aide")
        ligne = QHBoxLayout()
        self.ico = QLabel()
        self.ico.hide()
        ligne.addWidget(self.ico)
        ligne.addWidget(self.valeur, 1)
        v.addWidget(self.titre)
        v.addLayout(ligne)
        v.addWidget(self.sous)

    def definir(self, valeur: str, sous: str = "", alerte: bool = False):
        t = jetons()
        self.valeur.setText(valeur)
        self.sous.setText(sous)
        self.ico.setVisible(alerte)  # alerte = icône + texte, jamais la couleur seule
        if alerte:
            self.ico.setPixmap(icone("alerte", t["danger"], 22).pixmap(22, 22))
        self.valeur.setStyleSheet("font-size: 24px; font-weight: 700;" + (f"color: {t['danger']};" if alerte else ""))


class ZoneGraphique(QStackedWidget):
    """Graphique Matplotlib intégré, avec message « aucune donnée » et info-bulles au survol."""
    def __init__(self, message: str):
        super().__init__()
        self.fig = Figure(figsize=(5, 3), dpi=100, layout="constrained")
        self.canvas = FigureCanvasQTAgg(self.fig)
        self.canvas.setMinimumHeight(220)
        self.canvas.mpl_connect("motion_notify_event", self._survol)
        self.textes: list[str] = []
        self.msg = QLabel(message)
        self.msg.setAlignment(Qt.AlignCenter)
        self.msg.setStyleSheet("font-size: 16px;")
        self.addWidget(self.msg)
        self.addWidget(self.canvas)

    def vide(self, oui: bool):
        self.setCurrentIndex(0 if oui else 1)

    def _survol(self, ev):
        if ev.inaxes is None or ev.xdata is None or not self.textes:
            QToolTip.hideText()
            return
        i = round(ev.xdata)
        if 0 <= i < len(self.textes) and abs(ev.xdata - i) <= 0.45:
            QToolTip.showText(QCursor.pos(), self.textes[i], self.canvas)
        else:
            QToolTip.hideText()


class PageDashboard(QWidget):
    def __init__(self):
        super().__init__()
        t = jetons()
        self._gran = "jour"
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(12)
        titre = QLabel("Tableau de bord")
        titre.setProperty("role", "titre")
        lay.addWidget(titre)

        # Cartes de synthèse
        cartes = QHBoxLayout()
        cartes.setSpacing(12)
        self.c_ca = Carte("Chiffre d'affaires du jour")
        self.c_benef = Carte("Bénéfice du jour")
        self.c_stock = Carte("Articles en stock")
        self.c_alerte = Carte("Articles en alerte")
        for c in (self.c_ca, self.c_benef, self.c_stock, self.c_alerte):
            cartes.addWidget(c, 1)
        lay.addLayout(cartes)

        # Sélecteur de période + dates
        sel = QHBoxLayout()
        sel.setSpacing(8)
        self.groupe = QButtonGroup(self)
        self.groupe.setExclusive(True)
        for libelle, cle in GRANS:
            b = QPushButton(libelle)
            b.setProperty("chip", True)
            b.setCheckable(True)
            b.setChecked(cle == "jour")
            b.setProperty("cle", cle)
            b.setCursor(Qt.PointingHandCursor)
            b.setAccessibleName(f"Période : {libelle}")
            b.setToolTip(f"Regrouper les ventes par {libelle.lower()}")
            self.groupe.addButton(b)
            sel.addWidget(b)
        sel.addSpacing(16)
        self.d_debut = self._champ_date("Du", sel)
        self.d_fin = self._champ_date("Au", sel)
        sel.addStretch(1)
        lay.addLayout(sel)

        err = QHBoxLayout()
        self.ico_err = QLabel()
        self.ico_err.setPixmap(icone("erreur", t["danger"], 16).pixmap(16, 16))
        self.lbl_err = QLabel("La date de début doit être avant la date de fin.")
        self.lbl_err.setProperty("role", "erreur")
        err.addWidget(self.ico_err)
        err.addWidget(self.lbl_err, 1)
        lay.addLayout(err)
        self._erreur_dates(False)

        kpi = QHBoxLayout()
        self.k_ca = QLabel()
        self.k_ben = QLabel()
        for k in (self.k_ca, self.k_ben):
            k.setStyleSheet("font-size: 16px; font-weight: 600;")
            kpi.addWidget(k)
        kpi.addStretch(1)
        lay.addLayout(kpi)

        # Onglets : bénéfices / valeur du stock
        self.onglets = QTabWidget()
        self.zone_b = ZoneGraphique("Aucune vente sur cette période")
        self.table_b = creer_table(["Période", "Chiffre d'affaires (FCFA)", "Bénéfice (FCFA)"])
        self.onglets.addTab(self._page(self.zone_b, self.table_b), "Bénéfices")
        self.zone_s = ZoneGraphique("Aucun article en stock")
        self.table_s = creer_table(["Catégorie", "Pièces", "Valeur (FCFA)"])
        self.lbl_capital = QLabel()
        self.lbl_capital.setStyleSheet("font-size: 16px; font-weight: 600;")
        self.onglets.addTab(self._page(self.zone_s, self.table_s, self.lbl_capital), "Valeur du stock")
        lay.addWidget(self.onglets, 1)

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(300)
        self._timer.timeout.connect(self.rafraichir)
        self.groupe.buttonClicked.connect(self._changer_periode)
        self.d_debut.dateChanged.connect(lambda _: self._timer.start())
        self.d_fin.dateChanged.connect(lambda _: self._timer.start())
        self._appliquer_dates("jour")

    def _champ_date(self, libelle: str, parent_layout) -> QDateEdit:
        box = QVBoxLayout()
        box.setSpacing(2)
        box.addWidget(QLabel(libelle))
        d = QDateEdit()
        d.setCalendarPopup(True)
        d.setDisplayFormat("dd/MM/yyyy")
        d.setAccessibleName(f"Date {libelle.lower()}")
        d.setMinimumWidth(150)
        box.addWidget(d)
        parent_layout.addLayout(box)
        return d

    def _page(self, zone, table, entete=None) -> QWidget:
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(12, 12, 12, 12)
        h.setSpacing(12)
        h.addWidget(zone, 3)
        droite = QVBoxLayout()
        if entete:
            droite.addWidget(entete)
        droite.addWidget(table, 1)
        h.addLayout(droite, 2)
        return w

    def _erreur_dates(self, visible: bool):
        self.ico_err.setVisible(visible)
        self.lbl_err.setVisible(visible)

    def _appliquer_dates(self, gran: str):
        self._gran = gran
        for d in (self.d_debut, self.d_fin):
            d.blockSignals(True)
        self.d_fin.setDate(QDate.currentDate())
        self.d_debut.setDate(QDate.currentDate().addDays(-DEFAUT_JOURS[gran]))
        for d in (self.d_debut, self.d_fin):
            d.blockSignals(False)

    def _changer_periode(self, bouton):
        self._appliquer_dates(bouton.property("cle"))
        self.rafraichir()

    def showEvent(self, e):
        super().showEvent(e)
        self.rafraichir()

    def rafraichir(self):
        debut, fin = self.d_debut.date().toPython(), self.d_fin.date().toPython()
        dates_ok = debut <= fin
        self._erreur_dates(not dates_ok)
        QApplication.setOverrideCursor(Qt.WaitCursor)
        erreur, c, rows, stock = None, None, None, None
        try:
            c = rapports.cartes()
            stock = rapports.stock_par_categorie()
            if dates_ok:
                rows = rapports.ventes_par_periode(self._gran, debut, fin)
        except (ErreurBaseDeDonnees, AccesRefuse) as e:
            erreur = e
        finally:
            QApplication.restoreOverrideCursor()
        if erreur:
            QMessageBox.critical(self, "Tableau de bord", str(erreur))
            return
        self._maj_cartes(c)
        self._maj_stock(stock)
        if rows is not None:
            self._maj_benefices(rows)

    def _maj_cartes(self, c: dict):
        self.c_ca.definir(format_fcfa(c["ca_jour"]))
        self.c_benef.definir(format_fcfa(c["benefice_jour"]))
        self.c_stock.definir(f"{nombre(c['pieces'])} pièces", f"{c['references']} références")
        n = c["alertes"]
        self.c_alerte.definir(str(n), "stock faible ou épuisé" if n else "aucune alerte", alerte=n > 0)

    def _maj_benefices(self, rows: list[dict]):
        t = jetons()
        ca = sum(r["ca"] for r in rows)
        be = sum(r["benefice"] for r in rows)
        self.k_ca.setText(f"Chiffre d'affaires de la période : {format_fcfa(ca)}")
        self.k_ben.setText(f"Bénéfice net de la période : {format_fcfa(be)}")
        self.k_ben.setStyleSheet(f"font-size: 16px; font-weight: 600; color: {t['succes'] if be >= 0 else t['danger']};")
        sans_vente = not any(r["nb_ventes"] for r in rows)
        self.zone_b.vide(sans_vente)
        self.table_b.setSortingEnabled(False)
        self.table_b.setRowCount(0 if sans_vente else len(rows))
        if sans_vente:
            self.zone_b.textes = []
            self.table_b.setSortingEnabled(True)
            return
        self.zone_b.textes = tracer_benefices(self.zone_b.fig, rows, self._gran, t)
        self.zone_b.canvas.draw_idle()
        for i, r in enumerate(rows):
            p = NumItem(r["libelle"], i)
            p.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            for c, it in enumerate((p, NumItem(nombre(r["ca"]), r["ca"]), NumItem(nombre(r["benefice"]), r["benefice"]))):
                self.table_b.setItem(i, c, it)
        self.table_b.setSortingEnabled(True)

    def _maj_stock(self, rows: list[dict]):
        t = jetons()
        total = sum(r["valeur"] for r in rows)
        self.lbl_capital.setText(f"Capital immobilisé : {format_fcfa(total)}")
        vide = not rows or total == 0
        self.zone_s.vide(vide)
        self.table_s.setSortingEnabled(False)
        self.table_s.setRowCount(len(rows))
        for i, r in enumerate(rows):
            for c, it in enumerate((texte(r["categorie"]), NumItem(nombre(r["pieces"]), r["pieces"]),
                                    NumItem(nombre(r["valeur"]), r["valeur"]))):
                self.table_s.setItem(i, c, it)
        self.table_s.setSortingEnabled(True)
        if not vide:
            self.zone_s.textes = tracer_stock(self.zone_s.fig, rows, t)
            self.zone_s.canvas.draw_idle()
