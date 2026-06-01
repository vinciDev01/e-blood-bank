"""Géocodage d'adresses via la Google Geocoding API (sans dépendance externe)."""
import json
from urllib.parse import urlencode
from urllib.request import urlopen

from django.conf import settings

GEOCODE_URL = 'https://maps.googleapis.com/maps/api/geocode/json'


def geocoder_adresse(adresse, ville, code_postal, pays):
    """Retourne (lat, lng) pour l'adresse donnée, ou None si échec.

    Ne lève jamais d'exception : toute erreur (réseau, clé absente,
    statut non OK) renvoie None pour ne pas bloquer un enregistrement.
    """
    cle = getattr(settings, 'GOOGLE_MAPS_API_KEY', '')
    if not cle:
        return None

    adresse_complete = ', '.join(
        p for p in [adresse, ville, code_postal, pays] if p
    )
    if not adresse_complete:
        return None

    params = urlencode({'address': adresse_complete, 'key': cle})
    try:
        with urlopen(f'{GEOCODE_URL}?{params}', timeout=10) as reponse:
            donnees = json.loads(reponse.read().decode('utf-8'))
    except Exception:
        return None

    if donnees.get('status') != 'OK' or not donnees.get('results'):
        return None

    loc = donnees['results'][0]['geometry']['location']
    return (loc['lat'], loc['lng'])
