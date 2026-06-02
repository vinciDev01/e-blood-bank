# Modifier / Supprimer un stock (banque) — Design

**Date :** 2026-06-02
**Statut :** Validé (design)
**Périmètre :** Rendre fonctionnels « Modifier le stock » et « Supprimer le stock »
sur la page détail d'un stock (`detail_stock.html`), avec popup de confirmation
pour la suppression.

## Contexte

`StockDeSang` = inventaire agrégé par groupe sanguin (`groupe_sanguin`,
`nombre_de_poches`, `date_enregistrement`). `PocheDeSang` = poches individuelles
(matricule, QR, `est_disponible`, `bank_de_sang`). La page détail affiche un
`StockDeSang` et les poches du groupe pour la banque connectée. Les boutons
« Modifier/Supprimer le stock » pointaient vers `gestionStock` (non fonctionnels).

## Décisions

- Niveau **groupe** (`StockDeSang`), pas par poche.
- **Modifier** = changer `nombre_de_poches`.
- **Supprimer** = supprimer la ligne `StockDeSang` **et** marquer les poches du
  groupe **de cette banque** `est_disponible=False` (retirées, non effacées —
  traçabilité conservée, pas de poche orpheline disponible).
- **Popup de confirmation** avant suppression.
- Actions en **POST + CSRF**, rôle `blood_bank`.

## Composants

### 1. Vues — `bankDeSang/views.py`

`modifierStock(request, stock_id)` :
- `@login_required @check_role('blood_bank')`, **POST uniquement** (sinon redirige).
- `stock = get_object_or_404(StockDeSang, id=stock_id)`.
- Lit `nombre_de_poches` (POST), valide entier ≥ 0 ; sinon message d'erreur.
- Met à jour et enregistre ; message succès ; redirige vers `detailStock`.

`supprimerStock(request, stock_id)` :
- `@login_required @check_role('blood_bank')`, **POST uniquement**.
- `stock = get_object_or_404(StockDeSang, id=stock_id)`.
- `PocheDeSang.objects.filter(groupe_sanguin=stock.groupe_sanguin,
  bank_de_sang=request.user.banque_de_sang).update(est_disponible=False)`.
- `stock.delete()` ; message succès ; redirige vers `gestionStock`.

### 2. URLs — `bankDeSang/urls.py`
```python
path('modifierStock/<int:stock_id>/', views.modifierStock, name='modifierStock'),
path('supprimerStock/<int:stock_id>/', views.supprimerStock, name='supprimerStock'),
```

### 3. Template — `frontend/templates/frontend/bankDeSang/detail_stock.html`
- Section actions enveloppée dans un composant Alpine.js
  (`x-data="{ editOpen:false, supprOpen:false }"`).
- « Modifier le stock » → ouvre un modal : champ `number` (valeur initiale
  `stock.nombre_de_poches`, min 0), form `method="post"` vers `modifierStock`,
  `{% csrf_token %}`, boutons Annuler / Enregistrer.
- « Supprimer le stock » → ouvre un **popup de confirmation** : texte « Êtes-vous
  sûr ? Les poches de ce groupe seront retirées (sans être effacées). », form
  `method="post"` vers `supprimerStock`, `{% csrf_token %}`, boutons Annuler /
  Confirmer la suppression.
- Les anciens `<a href="...gestionStock">` sont remplacés par des `<button>` qui
  basculent `editOpen` / `supprOpen`.

## Sécurité

- Plus de suppression/modif via simple lien GET : tout passe en POST + CSRF.
- `get_object_or_404` évite les 500 sur id inexistant.
- Restreint au rôle `blood_bank`.

## Tests — `bankDeSang/tests.py`

- `modifierStock` (POST) met à jour `nombre_de_poches` ; un GET ne modifie rien.
- `supprimerStock` (POST) supprime le `StockDeSang` et passe les poches du groupe
  de la banque à `est_disponible=False` (les poches existent toujours).
- Un POST `supprimerStock` par un non-`blood_bank` est redirigé (302) sans effet.

## Hors périmètre (YAGNI)

- Édition du groupe sanguin ou de la date.
- Modification/suppression d'une poche individuelle.
- Resynchronisation automatique du compteur avec le nombre réel de poches.

## Critères de succès

1. « Modifier le stock » ouvre un modal et enregistre le nouveau nombre de poches.
2. « Supprimer le stock » demande confirmation, puis supprime la ligne et retire
   (sans effacer) les poches du groupe de la banque.
3. Aucune action destructive en GET ; tests verts.
