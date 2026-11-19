"""Lecture de la configuration depuis le fichier .env (aucun identifiant en dur)."""
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

# Dossier du projet, ou dossier de l'exécutable une fois packagé avec PyInstaller
RACINE = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent.parent
load_dotenv(RACINE / ".env")


@dataclass(frozen=True)
class ProfilBD:
    utilisateur: str
    mot_de_passe: str


@dataclass(frozen=True)
class Config:
    hote: str
    port: int
    base: str
    admin: ProfilBD
    vendeur: ProfilBD


def charger_config() -> Config:
    """Construit la configuration ; lève une erreur claire si le .env est incomplet."""
    requis = ["DB_ADMIN_USER", "DB_ADMIN_PASSWORD", "DB_VENDEUR_USER", "DB_VENDEUR_PASSWORD"]
    manquants = [k for k in requis if not os.getenv(k)]
    if manquants:
        raise RuntimeError("Fichier .env incomplet ou absent. Variables manquantes : " + ", ".join(manquants))
    return Config(
        hote=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", "3306")),
        base=os.getenv("DB_NAME", "style_shop_db"),
        admin=ProfilBD(os.environ["DB_ADMIN_USER"], os.environ["DB_ADMIN_PASSWORD"]),
        vendeur=ProfilBD(os.environ["DB_VENDEUR_USER"], os.environ["DB_VENDEUR_PASSWORD"]),
    )
