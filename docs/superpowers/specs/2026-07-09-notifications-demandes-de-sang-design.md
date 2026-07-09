# Compteur + alertes temps réel sur les demandes de sang

Date : 2026-07-09
Branche : feature/carte-banques-de-sang (ou branche dédiée)

## Objectif

Quand une demande de sang est émise (ou répond change d'état), afficher :
1. un **badge incrémenteur** sur l'item de menu « demandes de sang » ;
2. une **alerte temps réel** in-app (toast) ;
3. une **notification système** navigateur si besoin (onglet en arrière-plan).

Cible : tableau de bord **banque de sang** (destinataire) ET **service médical** (émetteur).

## Contexte existant

- `DemandeDeSang` (serviceMedicaux/models.py) : `etat` (`En attente`/…), `serviceMedicaux` FK, champ `notification_envoyee`.
- `DemandeDeSang.nbre_demande_en_attente_service_medicaux()` compte déjà les demandes en attente rattachées à un service.
- Gabarits `frontend/templates/frontend/bankDeSang/base.html` et `.../serviceMedicaux/base.html` : Alpine.js + Tailwind (CDN), classe `.ebb-nav-badge` déjà stylée, items de menu dédiés (`listeDemandesDeSang` côté banque ; `mesDemandesDeSang` côté service).
- Un toast factice codé en dur existe (~ligne 995 bankDeSang/base.html).
- **Aucun** Django Channels/ASGI/WebSocket : Django 4.2 synchrone.

## Décisions

- **Mécanisme temps réel** : polling AJAX (~20 s). Aucune dépendance nouvelle.
- **Portée** : banque de sang + service médical.
- **Sémantique du compteur** : total « En attente » (pas de suivi lu/non-lu par utilisateur).

## Architecture

### 1. Context processor — badge au premier rendu

Nouveau `serviceMedicaux/context_processors.py` : fonction `demandes_badge(request)` qui renvoie
`{'demandes_badge_count': N, 'demandes_badge_url_name': '<nom_item>'}` selon `request.user.role` :

- `blood_bank` → `DemandeDeSang.objects.filter(etat='En attente', serviceMedicaux__isnull=False).count()`, item `listeDemandesDeSang`.
- `medical` → demandes du service courant en attente, item `mesDemandesDeSang`.
- autre / anonyme → count 0.

Enregistré dans `settings.TEMPLATES['OPTIONS']['context_processors']`.

Rendu dans chaque `base.html` : `<span class="ebb-nav-badge" id="demandes-badge" ...>` sur le bon item, masqué (`display:none`) si count == 0.

### 2. Endpoints de flux JSON

Côté banque — `bankDeSang/views.py` `demandes_flux(request)` (`@login_required` + `@check_role('blood_bank')`), URL `bankDeSang/api/demandes/flux/` nom `demandesFlux` :
```json
{ "count": N, "max_id": M, "recentes": [ {"id":.., "etablissement":"..", "groupe":"..", "urgence":".."} ] }
```
`count` = total en attente (serviceMedicaux non nul) ; `max_id` = plus grand id de demande (détecte une nouveauté) ; `recentes` = jusqu'à 5 dernières pour le texte du toast.

Côté service — `serviceMedicaux/views.py` `mes_demandes_flux(request)` (`@login_required` + `@check_role('medical')`), URL `serviceMedicaux/api/demandes/flux/` nom `mesDemandesFlux` :
```json
{ "count": N, "etats": [ [id, "etat"], ... ] }
```
`count` = demandes du service en attente ; `etats` = snapshot (id → etat) pour détecter une réponse de la banque (changement d'état).

Isolation : le service ne voit que `serviceMedicaux == request.user.service_medical`.

### 3. Script de polling (vanilla, un par base.html)

- Baseline initialisée depuis des attributs `data-*` rendus serveur → aucune fausse alerte au 1er chargement.
- Toutes les ~20 s : `fetch(endpoint)`, met à jour le nombre du badge (affiche si > 0, masque si 0).
- Détection de nouveauté :
  - banque : `max_id` reçu > baseline → au moins une nouvelle demande.
  - service : un couple `[id, etat]` diffère du snapshot → réponse reçue.
- Sur nouveauté → `afficherToast(message, url)` + `notifierSysteme(titre, corps)`.
- Le polling continue même onglet caché (permet la notif système en arrière-plan).
- GET only → pas de CSRF.

### 4. Notification système (« si besoin »)

- `Notification.requestPermission()` demandé au 1er clic utilisateur (contrainte navigateurs).
- Émise **uniquement** si `Notification.permission === 'granted'` **et** `document.hidden` — sinon le toast in-app suffit (pas de doublon). Dégradation silencieuse si API absente/refusée.

### 5. Toast in-app

- Conteneur dédié piloté par le script (remplace le toast factice codé en dur). Message : « Nouvelle demande — {groupe} / {urgence} de {établissement} » (banque) ou « Votre demande {groupe} est {etat} » (service). Auto-disparition ~6 s, clic → item de liste.

## Hors périmètre (YAGNI)

- WebSockets / Channels / ASGI / Redis / SSE.
- Son par défaut.
- Persistance « lu/non-lu » par utilisateur.
- Modification du modèle (aucune migration).

## Tests

- Context processor : compte correct par rôle (blood_bank, medical, autre) ; 0 si anonyme.
- Endpoint banque : JSON attendu, `max_id`/`count` cohérents, refus si rôle ≠ blood_bank.
- Endpoint service : n'expose que les demandes du service courant ; refus si rôle ≠ medical.
- Détection : `max_id` croissant ⇒ nouveauté ; changement d'`etat` ⇒ réponse.
