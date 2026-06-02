# Historique des actions sur le stock (banque) — Design

**Date :** 2026-06-02
**Statut :** Validé (design)
**Périmètre :** Journaliser les actions de stock (ajout, modification, suppression)
dans une table et les afficher dans une page d'historique du dashboard banque.

## Contexte

Aucun modèle d'audit n'existe. La vue `historiqueDemandes` ne couvre que les
demandes de sang. Les actions de stock (`gestionStock` ajout de poche,
`modifierStock`, `supprimerStock`) ne sont pas tracées → l'utilisateur ne voit
aucun historique.

## Décisions

- Périmètre **stock uniquement** : ajout, modification, suppression.
- Historique **par banque** (FK `banque`), contrairement à `StockDeSang` (global).

## Composants

### 1. Modèle — `bankDeSang/models.py`
```python
class HistoriqueStock(models.Model):
    ACTION_CHOICES = [('ajout','Ajout'), ('modification','Modification'), ('suppression','Suppression')]
    banque = models.ForeignKey(BanqueDeSang, on_delete=models.CASCADE, null=True, related_name='historique_stock')
    utilisateur = models.ForeignKey('_auth.CustomUser', on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    groupe_sanguin = models.CharField(max_length=3, null=True, blank=True)
    description = models.TextField()
    date = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']

    @classmethod
    def enregistrer(cls, banque, utilisateur, action, groupe_sanguin, description):
        return cls.objects.create(banque=banque, utilisateur=utilisateur,
            action=action, groupe_sanguin=groupe_sanguin, description=description)
```
+ migration.

### 2. Instrumentation — `bankDeSang/views.py`
- `gestionStock` (après création de poche réussie) → `enregistrer(..., 'ajout',
  poche.groupe_sanguin, "Ajout poche {matricule} ({groupe})")`.
- `modifierStock` → capturer l'ancien nombre avant save, puis `enregistrer(...,
  'modification', stock.groupe_sanguin, "Stock {groupe} : {ancien} → {nouveau} poches")`.
- `supprimerStock` → compter les poches retirées, puis `enregistrer(...,
  'suppression', groupe, "Suppression du stock {groupe} ({n} poches retirées)")`.
- La banque = `request.user.banque_de_sang` ; l'utilisateur = `request.user`.

### 3. Vue + URL — `bankDeSang/`
- `historiqueStock(request)` `@login_required @check_role('blood_bank')` :
  `HistoriqueStock.objects.filter(banque=request.user.banque_de_sang)` (déjà trié
  par `-date` via Meta).
- URL `historiqueStock/` name `historiqueStock`.

### 4. Template — `frontend/templates/frontend/bankDeSang/historique_stock.html`
- Étend `bankDeSang/base.html`. Tableau : Date, Action (badge couleur), Groupe,
  Description, Utilisateur. Message « Aucune action enregistrée » si vide.

### 5. Sidebar — `bankDeSang/base.html`
- Lien « Historique des stocks » dans le groupe **Gestion**, état `active` géré.

## Tests — `bankDeSang/tests.py`
- Un ajout de poche via `gestionStock` crée une entrée `ajout`.
- `modifierStock` crée une entrée `modification` avec l'ancien et le nouveau nombre.
- `supprimerStock` crée une entrée `suppression`.
- La page `historiqueStock` (200) liste les entrées de la banque connectée ; un
  rôle non-banque est redirigé.

## Hors périmètre (YAGNI)
- Décisions de demandes, réception de poches.
- Pagination, filtres, export.

## Critères de succès
1. Chaque ajout/modif/suppression de stock crée une entrée d'historique.
2. La page « Historique des stocks » affiche ces entrées (banque connectée), plus
   récentes d'abord.
3. Tests verts.
