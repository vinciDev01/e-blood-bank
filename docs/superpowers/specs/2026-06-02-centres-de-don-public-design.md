# Page publique « Centres de don » + accès admin depuis l'accueil — Design

**Date :** 2026-06-02
**Statut :** Validé (design)
**Périmètre :** Rendre l'input « Trouver un lieu de don » de l'accueil fonctionnel
(redirige vers une page publique listant les centres + carte/itinéraire), et
ajouter un bouton « Administration » dans l'en-tête de l'accueil.

## Contexte

`accueil.html` (étend `frontend/base.html`, public) contient un input
« Trouver un lieu de don » inerte. Les centres = `BanqueDeSang`. On dispose déjà du
partial `frontend/_carte_banques_contenu.html` (carte Leaflet/OSM + itinéraire) et
de `BanqueDeSang.donnees_carte()`. `administrationDashboard` est protégé
(`@login_required` + `@check_role('admin')`).

## Composants

### 1. Vue + URL — `frontend/views.py`, `frontend/urls.py`
`centresDeDon(request)` — **publique** (pas de `login_required`) :
- `centres = BanqueDeSang.objects.all()` (liste textuelle) ;
- `banques = BanqueDeSang.donnees_carte()` (carte) ;
- `response = render('frontend/centres_de_don.html', {'centres': centres, 'banques': banques})` ;
- `response['Referrer-Policy'] = 'strict-origin-when-cross-origin'` (tuiles OSM) ;
- retourne `response`.

URL : `path('centres/', centresDeDon, name='centresDeDon')` (app_name `frontend`).

### 2. Template — `frontend/templates/frontend/centres_de_don.html`
- Étend `frontend/base.html`.
- Titre + **liste des centres** (`{% for c in centres %}` : `nom_etablissement`,
  `adresse`, `ville`, `telephone` ; message si vide).
- `{% include 'frontend/_carte_banques_contenu.html' %}` pour la carte + itinéraire.

### 3. `accueil.html`
- Le conteneur de recherche devient un `<form method="get"
  action="{% url 'frontend:centresDeDon' %}">` ; le bouton loupe est `type="submit"`.
- L'input `#input` reçoit `onfocus`/`onclick` → `window.location.href` vers
  `centresDeDon` (clic = redirection, conforme à la demande).
- Ajout d'un bouton/lien **« Administration »** dans l'en-tête, href vers
  `{% url '_auth:administrationDashboard' %}`.

## Sécurité

- `centresDeDon` est publique mais ne fait que lister des établissements (données
  déjà destinées au public) — aucune donnée sensible.
- Le bouton Administration mène à une vue protégée ; un non-admin est redirigé vers
  la connexion. Aucune élévation de privilège.

## Tests — `frontend/tests.py`
- `centresDeDon` répond **200 sans authentification**, contient le nom d'un centre
  et l'îlot `id="banques-data"`, et renvoie l'en-tête `Referrer-Policy`.
- `accueil` contient le lien vers `administrationDashboard` et l'action du form
  pointe vers `centresDeDon`.

## Hors périmètre (YAGNI)
- Autocomplétion / recherche filtrée (on a choisi la redirection).
- Tri par distance, pagination.

## Critères de succès
1. Cliquer l'input « Trouver un lieu de don » mène à `/centres/`.
2. La page liste les centres et affiche la carte avec itinéraire, sans connexion.
3. Le bouton « Administration » de l'accueil mène au dashboard admin (protégé).
4. Tests verts.
