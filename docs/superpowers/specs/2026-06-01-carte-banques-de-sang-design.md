# Carte des banques de sang — Design

**Date :** 2026-06-01
**Statut :** Validé (design)
**Périmètre :** V1 — afficher les banques de sang sur une carte Google Maps dans le tableau de bord du service médical.

## Objectif

Permettre à un service médical connecté de visualiser les banques de sang sur
une carte interactive afin de localiser géographiquement où trouver du sang.

## Décisions

- **Emplacement :** tableau de bord `serviceMedicaux` (rôle `medical`, connecté).
- **Coordonnées :** champs `latitude`/`longitude` ajoutés au modèle `BanqueDeSang`,
  remplis par géocodage de l'adresse au moment du `save()` (et via une commande de
  backfill pour les banques déjà en base).
- **Contenu d'un marqueur :** nom de l'établissement, adresse, téléphone (lien `tel:`).
  Pas de stock, pas de lien de détail (aucune page de détail de banque n'existe).

## Composants

### 1. Modèle — `_auth/models.py`

Ajout sur `BanqueDeSang` :

```python
latitude  = models.FloatField(null=True, blank=True)
longitude = models.FloatField(null=True, blank=True)
```

Champs nullables : aucune donnée existante n'est invalidée. Une migration est générée.

### 2. Géocodage — `_auth/geocoding.py` (nouveau)

- `geocoder_adresse(adresse, ville, code_postal, pays) -> tuple[float, float] | None`
- Appelle la **Geocoding API** de Google via `urllib.request` (stdlib — aucune
  nouvelle dépendance). Clé lue depuis `settings.GOOGLE_MAPS_API_KEY`.
- En cas d'erreur réseau, de statut non `OK`, ou de clé absente : retourne `None`
  (jamais d'exception qui bloquerait un enregistrement).

`BanqueDeSang.save()` est surchargé :
- Si l'adresse a changé, ou si `latitude`/`longitude` sont vides, on tente le
  géocodage et on remplit les coordonnées.
- Si le géocodage échoue, on sauve quand même sans coordonnées ; la banque
  n'apparaîtra simplement pas sur la carte tant qu'elle n'est pas géocodée.

### 3. Commande de backfill — `_auth/management/commands/geocoder_banques.py` (nouveau)

`python manage.py geocoder_banques` parcourt les `BanqueDeSang` sans coordonnées,
les géocode et les enregistre. Affiche un résumé (géocodées / échouées).

### 4. Clé API — `eBloodBank/info.py`

- `GOOGLE_MAPS_API_KEY = "..."` (le fichier `info.py` est déjà traité comme sensible).
- Importée dans `settings.py` (via `from .info import *`, déjà en place).
- Utilisée à la fois pour le géocodage (serveur) et le chargement de la carte (navigateur).

**Recommandation sécurité (documentée, hors périmètre code V1) :** à terme, utiliser
deux clés Google restreintes — une restreinte par *referrer HTTP* pour le JavaScript
Maps, une restreinte par *IP* pour le géocodage serveur — car la clé JS est exposée
dans le HTML rendu.

### 5. Vue + URL — `serviceMedicaux/`

Vue `carteBanques(request)` :
- Décorée `@login_required` et `@check_role('medical')`.
- Récupère les `BanqueDeSang` ayant `latitude` et `longitude` non nuls.
- Sérialise en JSON la liste `{nom, adresse, ville, telephone, lat, lng}`.
- Passe au template : le JSON des banques et `GOOGLE_MAPS_API_KEY`.

URL dans `serviceMedicaux/urls.py` :
```python
path('carteBanques/', views.carteBanques, name='carteBanques'),
```

### 6. Template — `frontend/templates/frontend/serviceMedicaux/carte_banques_de_sang.html`

- Étend `serviceMedicaux/base.html`.
- Un conteneur `<div>` pour la carte (plein cadre du contenu).
- Charge la **Maps JavaScript API** avec la clé passée par la vue.
- Pour chaque banque : un marqueur ; au clic, une `InfoWindow` affichant
  nom, adresse, et téléphone (lien `tel:`).
- Centrage automatique sur l'ensemble des marqueurs (`fitBounds`). S'il n'y a
  aucune banque géocodée, afficher un message « Aucune banque localisée ».

### 7. Navigation — `serviceMedicaux/base.html`

Ajout d'un lien « Carte des banques » dans la sidebar (groupe **Général**),
avec gestion de l'état `active` (via `url_name == 'carteBanques'`).

## Hors périmètre (YAGNI)

- Stock disponible par banque sur les marqueurs.
- Filtre / recherche / regroupement (clustering) de marqueurs.
- Calcul d'itinéraire ou de distance.
- Page publique de détail d'une banque de sang.

## Critères de succès

1. Un service médical connecté accède à `/serviceMedicaux/carteBanques/` et voit
   une carte avec un marqueur par banque géocodée.
2. Le clic sur un marqueur affiche nom, adresse et téléphone.
3. La création/modification d'une banque avec adresse renseigne automatiquement
   ses coordonnées.
4. `python manage.py geocoder_banques` géocode les banques existantes.
5. Une banque sans coordonnées (géocodage échoué) n'apparaît pas mais ne provoque
   aucune erreur.
