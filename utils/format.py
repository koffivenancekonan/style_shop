"""Formats d'affichage : montants en FCFA sans décimales, séparateur de milliers."""
NBSP = "\u00a0"


def nombre(n: int) -> str:
    return f"{int(n):,}".replace(",", NBSP)


def format_fcfa(n: int) -> str:
    return f"{nombre(n)}{NBSP}FCFA"
