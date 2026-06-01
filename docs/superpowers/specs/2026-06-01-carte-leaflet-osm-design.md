# Bascule de la carte vers Leaflet / OpenStreetMap — Design

**Date :** 2026-06-01
**Statut :** Validé (design)
**Périmètre :** V1 — remplacer l'affichage Google Maps de la carte des banques par
Leaflet + OpenStreetMap, sans clé ni facturation. Le géocodage reste sur Google.

## Contexte / motivation

Google Maps affiche « cette page ne s'est pas chargée correctement » car les APIs
Maps ne sont pas activées dans le projet Google Cloud (et exigent une facturation).
Leaflet + OpenStreetMap fournit le même affichage (marqueurs + popups) sans clé,
sans facturation et sans activation d'API.

## Décisions

- **Affichage uniquement** bascule vers Leaflet. Le géocodage serveur
  (`geocoding.py`, `BanqueDeSang.save()`, commande `geocoder_banques`) reste sur
  Google et `GOOGLE_MAPS_API_KEY` est conservée pour cet usage.
- **Leaflet via CDN** (1.9.4) avec `integrity` (SRI) + `crossorigin` — possible car
  les fichiers sont versionnés et stables (contrairement au loader dynamique Google).

## Composants

### 1. Template — `frontend/templates/frontend/serviceMedicaux/carte_banques_de_sang.html`

- Charger Leaflet **CSS** et **JS** depuis le CDN unpkg, version 1.9.4, avec les
  attributs `integrity` et `crossorigin="anonymous"`.
- Conserver l'îlot de données `{{ banques|json_script:"banques-data" }}` (déjà sûr).
- Au chargement du DOM :
  - créer une carte `L.map('carte-banques')` ;
  - ajouter une couche de tuiles OpenStreetMap
    `https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png` avec l'**attribution
    obligatoire** « © OpenStreetMap contributors » ;
  - pour chaque banque, ajouter un `L.marker([lat, lng])` et `bindPopup(...)` ;
  - le contenu du popup est construit avec des nœuds DOM et `textContent`
    (anti-XSS : nom, adresse + ville, téléphone en lien `tel:`) ;
  - `map.fitBounds(...)` sur l'ensemble des marqueurs ;
  - si la liste est vide : masquer la carte et afficher « Aucune banque de sang
    localisée pour le moment. »
- Plus de clé API, plus de callback asynchrone Google.

### 2. Vue — `serviceMedicaux/views.py`

- `carteBanques` ne passe plus `google_maps_api_key` au contexte (l'affichage n'en
  a plus besoin). Le contexte se réduit à `{'banques': donnees}`.

### 3. Tests — `serviceMedicaux/tests.py`

- `test_role_medical_voit_la_carte` : ne vérifie plus la clé ; vérifie `status 200`
  et la présence de l'îlot `id="banques-data"` dans le HTML rendu.
- `test_seules_les_banques_geocodees_sont_envoyees` : inchangé (lit `context['banques']`).
- `test_role_non_medical_est_redirige` : inchangé.

## Hors périmètre (inchangé)

- `geocoding.py`, `BanqueDeSang.save()`, commande `geocoder_banques` (restent Google).
- `GOOGLE_MAPS_API_KEY` dans `info.py` (toujours utilisée par le géocodage serveur).
- Le lien sidebar et le reste du dashboard.
- Auto-hébergement des assets Leaflet, clustering, recherche, itinéraire (YAGNI).

## Critères de succès

1. `/serviceMedicaux/carteBanques/` affiche une carte OpenStreetMap avec un marqueur
   par banque géolocalisée — sans aucune clé et sans erreur de chargement.
2. Le clic sur un marqueur ouvre un popup nom / adresse / téléphone.
3. Aucune donnée n'est injectée en HTML brut (popups construits via `textContent`).
4. Les balises Leaflet portent `integrity` + `crossorigin`.
5. Les tests de `serviceMedicaux` passent.
