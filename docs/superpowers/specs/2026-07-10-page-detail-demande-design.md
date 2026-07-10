# Page de détail d'une demande (au lieu d'un déroulé en bas de liste)

Date : 2026-07-10

## Objectif

Remplacer l'affichage des détails d'une demande « en dépliant une section en bas de la
liste » par une **page de détail dédiée**, côté **banque** ET **service médical**.
La page est en **lecture seule** ; les actions Accepter/Refuser (banque) **restent sur la liste**.

## Architecture

### Modèle (serviceMedicaux/models.py)
`DemandeDeSang.details_groupes()` → liste de `{groupe, quantite, etat}` (zip de
`groupeSanguin()` / `nombrePoches()` + `get_etat_groupe()`), réutilisable par la page.

### Vues + URLs
- `bankDeSang:detailDemande` `/demande/<int:demande_id>/` — `@check_role('blood_bank')`,
  demande globale (cohérent avec la liste banque). Contexte : demande, `details_groupes`,
  `retour_url`, `pdf_url`.
- `serviceMedicaux:detailDemande` `/demande/<int:demande_id>/` — `@check_role('medical')`,
  **scopé au service propriétaire** (404 sinon).

### Templates
- Partiel `frontend/_detail_demande.html` (lecture seule) : établissement, patient,
  tableau groupes/quantités/états, type produit, urgence, motif, dates, référence,
  bouton « Télécharger l'ordonnance », bouton retour.
- `bankDeSang/detail_demande.html` (extends base banque) + `serviceMedicaux/detail_demande.html`
  (extends base service) : incluent le partiel avec les URLs role-spécifiques.

### Listes
- **Service** (`liste_demande_de_sang.html`) : l'œil « Voir détails » → lien vers la page ;
  suppression de la ligne dépliée `detail-<id>` et de son JS de bascule.
- **Banque** (`liste_demandes_de_sang.html`) : l'œil → lien vers la page (infos) ;
  bouton « Traiter » qui déplie **uniquement** le tableau d'actions Accepter/Refuser
  (retrait de la grille d'infos du déroulé, désormais sur la page).

## Hors périmètre
- Pas de changement du workflow Accepter/Refuser lui-même (mêmes endpoints/modales).

## Tests
- `details_groupes()` : mapping groupe/quantité/état.
- detailDemande banque : 200, contenu attendu ; refus rôle non-banque.
- detailDemande service : 200 pour le propriétaire ; 404 pour la demande d'un autre service ;
  refus rôle non-medical.
