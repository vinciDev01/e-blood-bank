# Itinéraire « ma position → banque » (OSRM, gratuit) — Design

**Date :** 2026-06-01
**Statut :** Validé (design)
**Périmètre :** V1 — afficher l'itinéraire routier entre la position de
l'utilisateur (géolocalisation navigateur) et une banque de sang choisie, sur la
carte Leaflet/OpenStreetMap, sans clé ni facturation.

## Décisions

- **Origine** : position du navigateur (`navigator.geolocation`).
  **Destination** : la banque dont le popup contient le bouton « Itinéraire ».
- **Moteur de routage** : **OSRM** serveur démo public `router.project-osrm.org`
  (gratuit, sans clé). Profil `driving`. *Limite assumée : serveur démo « test/dev »,
  sans garantie de disponibilité — à remplacer par un OSRM auto-hébergé ou un
  fournisseur à clé en production.*
- **Affichage** : tracé `L.polyline` de la route + marqueur de départ + distance
  (km) et durée (min). Un seul itinéraire à la fois (on efface le précédent).
- **Changement template uniquement**, aucun changement backend.

## Composant — `frontend/templates/frontend/serviceMedicaux/carte_banques_de_sang.html`

### Bouton dans le popup
Pour chaque banque, le contenu du popup (construit en DOM/`textContent`) reçoit un
bouton **« Itinéraire »** portant les coordonnées de la banque.

### Au clic du bouton
1. `navigator.geolocation.getCurrentPosition(succes, erreur, {timeout})`.
   - **erreur** (refus de permission, position indisponible, timeout) → afficher
     un message dans le popup, ne rien planter.
2. Sur succès, appeler OSRM :
   `https://router.project-osrm.org/route/v1/driving/{lonDep},{latDep};{lonDest},{latDest}?overview=full&geometries=geojson`
   via `fetch`.
   - réponse non OK / `code !== 'Ok'` / aucune route → message d'erreur, pas de plantage.
3. Sur succès OSRM :
   - effacer l'itinéraire précédent (polyline + marqueur de départ) s'il existe ;
   - dessiner `L.polyline(geometry)` dans une couleur distincte ;
   - ajouter un marqueur « Départ » à la position de l'utilisateur ;
   - `carte.fitBounds(polyline.getBounds())` (dans les limites Togo déjà en place) ;
   - afficher distance (`route.distance` m → km) et durée (`route.duration` s → min)
     dans le popup (texte, via `textContent`).

### État partagé
Une variable de portée module (au sein de `initCarteBanques`) garde la couche
d'itinéraire courante pour pouvoir l'effacer avant d'en tracer une nouvelle.

## Sécurité

- La géométrie OSRM = tableaux de nombres dessinés par Leaflet → aucune injection.
- Bouton et textes ajoutés via DOM/`textContent` (cohérent avec l'anti-XSS existant).
- Aucune donnée sensible envoyée : seules des coordonnées partent vers OSRM.

## Tests

- Test de présence léger : la page rendue contient le bouton « Itinéraire » et la
  logique de routage (ex. l'URL OSRM `router.project-osrm.org`).
- Les 15 tests existants de `serviceMedicaux`/`_auth` restent verts.
- La logique réseau (géoloc + OSRM) n'est pas testable en unité côté Django :
  vérification manuelle au navigateur.

## Hors périmètre (YAGNI)

- Panneau turn-by-turn (Leaflet Routing Machine).
- Choix du mode (piéton/vélo) — `driving` uniquement.
- Saisie manuelle d'un point de départ / géocodage d'adresse de départ.
- Itinéraire entre deux banques.

## Critères de succès

1. Un service médical ouvre le popup d'une banque, clique « Itinéraire »,
   autorise la géolocalisation → la route s'affiche jusqu'à la banque.
2. Distance et durée sont affichées.
3. Refus de géolocalisation ou panne OSRM → message clair, aucune erreur JS bloquante.
4. Cliquer « Itinéraire » sur une autre banque remplace l'itinéraire précédent.
