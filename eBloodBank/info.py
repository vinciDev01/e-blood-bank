"""Configuration sensible chargée depuis l'environnement.

Les valeurs réelles ne sont PAS versionnées : placez-les dans un fichier
`.env` à la racine du projet (ignoré par git) ou dans l'environnement système.
Voir `.env.example` pour la liste des variables attendues.
"""
import os
from pathlib import Path


def _charger_env():
    """Charge un fichier `.env` (lignes `CLE=valeur`) à la racine du projet.

    Implémentation volontairement minimale (aucune dépendance externe).
    N'écrase pas une variable déjà définie dans l'environnement système.
    """
    chemin = Path(__file__).resolve().parent.parent / '.env'
    if not chemin.exists():
        return
    for ligne in chemin.read_text(encoding='utf-8').splitlines():
        ligne = ligne.strip()
        if not ligne or ligne.startswith('#') or '=' not in ligne:
            continue
        cle, _, valeur = ligne.partition('=')
        os.environ.setdefault(cle.strip(), valeur.strip())


_charger_env()

EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True') == 'True'
EMAIL_USE_SSL = os.environ.get('EMAIL_USE_SSL', 'False') == 'True'

ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', '')

# Clé Google Maps (Geocoding API côté serveur + Maps JavaScript API côté client).
GOOGLE_MAPS_API_KEY = os.environ.get('GOOGLE_MAPS_API_KEY', '')

# Vérification OTP au login. Désactivée par défaut (login direct, pratique en
# dev/démo). Mettre OTP_ENABLED=True dans .env pour l'activer (sécurité en prod).
OTP_ENABLED = os.environ.get('OTP_ENABLED', 'False').strip().lower() == 'true'
