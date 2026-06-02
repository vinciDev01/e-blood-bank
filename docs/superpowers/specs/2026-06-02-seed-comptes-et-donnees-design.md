# Seed `seed_comptes` — comptes par rôle + données de démo — Design

**Date :** 2026-06-02
**Statut :** Validé (design)
**Périmètre :** Commande de management qui crée un utilisateur connectable par rôle
(emails prévisibles) avec son profil, plus un jeu de données métier de démonstration.

## Décisions

- Un utilisateur par rôle, `username = email`, mot de passe `00000000`
  (surchargeable via `SEED_PASSWORD`).
- Idempotent ; garde production (refus hors `DEBUG` sauf `--force`), comme `seed_banques`.
- Les données métier sont créées en même temps que chaque compte (donc sautées au re-run).

## Comptes (`_auth/management/commands/seed_comptes.py`)

| Email | Rôle | Profil |
|---|---|---|
| `donneur@ebloodbank.com` | `donor` | `Donneur` |
| `banque@ebloodbank.com` | `blood_bank` | `BanqueDeSang` (coordonnées posées) |
| `medical@ebloodbank.com` | `medical` | `ServiceMedicaux` (email profil = même) |
| `generic@ebloodbank.com` | `generic` | `Utilisateur` |
| `admin@ebloodbank.com` | `admin` | superuser (`is_staff`+`is_superuser`) |

Tous : `is_active=True`.

## Données métier

- **Banque** : ~4 `PocheDeSang` (`bulk_create` avec `date_expiration` explicite →
  pas de génération QR), `est_disponible=True`, `bank_de_sang` = la banque. Pour
  chaque poche, `StockDeSang.enregistrer_stock(poche, 1)`. Une entrée
  `HistoriqueStock` (`action='ajout'`).
- **Service médical** : 1 `Patient` (rattaché à l'`Utilisateur` generic ou nul) +
  1 `DemandeDeSang` `etat='En attente'` avec
  `groupe_sanguin={service.email: [grp]}`, `nombre_poches={service.email: [qte]}`,
  `etat_groupes={grp: 'En attente'}`, `type_produit`, `urgence`, `motif`.
- **Donneur** : 1 `DonDeSang` (donneur, type_produit) — `date_don` auto.

## Géocodage banque

Créer la `BanqueDeSang`, puis fixer `latitude`/`longitude` via
`BanqueDeSang.objects.filter(pk=...).update(...)` pour qu'elle apparaisse sur la
carte sans dépendre d'un appel réseau au géocodage.

## Tests (`_auth/tests.py`)

- Après `call_command('seed_comptes', force=True)` :
  - un `CustomUser` existe pour chaque email attendu avec le bon `role` ;
  - les profils liés existent (Donneur/BanqueDeSang/ServiceMedicaux/Utilisateur) ;
  - `admin@` est superuser ;
  - au moins une `DemandeDeSang`, des `PocheDeSang`/`StockDeSang` et un `DonDeSang` existent.
- Idempotent : un 2ᵉ appel ne crée pas de doublon d'utilisateur.
- Refus hors `DEBUG` sans `--force` (`CommandError`).

## Hors périmètre (YAGNI)
- Plusieurs utilisateurs par rôle, gros volumes, données aléatoires.
- `seed_banques` (banques de la carte) reste une commande séparée.

## Critères de succès
1. `python manage.py seed_comptes` crée les 5 comptes connectables + leurs profils.
2. Des données métier (demande, poches/stock, don) sont présentes et visibles dans
   les écrans correspondants.
3. Idempotent ; tests verts.
