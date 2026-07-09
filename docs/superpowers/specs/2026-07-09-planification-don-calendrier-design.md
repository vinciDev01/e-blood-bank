# Planifier un don sur calendrier (donneur)

Date : 2026-07-09
Branche : feature/carte-banques-de-sang

## Objectif

Sur sa page, le donneur peut **planifier un don** en choisissant une **banque de sang**
et une **date** sur un **calendrier mensuel**, puis **voir** ses rendez-vous à venir et
les **annuler**.

## Décisions

- Lieu : le donneur choisit une **BanqueDeSang**.
- Calendrier : **mensuel « maison »**, rendu serveur (module `calendar` de Python),
  zéro dépendance JS externe (compatible CSP).
- Portée : **planifier + voir + annuler**.

## Architecture

### 1. Modèle `RendezVousDon` (donneur/models.py)

Les enregistrements transactionnels vivent dans leur app (comme `DemandeDeSang` dans
serviceMedicaux). `donneur/models.py` est activé.

- `donneur = FK(_auth.Donneur, on_delete=CASCADE, related_name='rendez_vous')`
- `banque = FK(_auth.BanqueDeSang, on_delete=CASCADE)`
- `date = DateField`
- `creneau = CharField(choices=CRENEAUX)` — ex. `08:00-10:00`, `10:00-12:00`,
  `14:00-16:00`, `16:00-18:00`
- `statut = CharField(choices)` — `Planifié` (défaut) / `Annulé` / `Effectué`
- `date_creation = DateTimeField(auto_now_add)`
- `Meta.ordering = ['date', 'creneau']`
- Helpers : `est_a_venir()` (date >= aujourd'hui et statut Planifié).
- Migration `donneur 0001`.

### 2. Créneaux

Constante `CRENEAUX` (liste de tuples) dans donneur/models.py, réutilisée par la vue.

### 3. Vues (donneur/views.py, `@login_required` + `@check_role('donor')`)

- `planifierDon` :
  - GET : calcule le mois affiché depuis `?annee=&mois=` (défaut = mois courant),
    construit la grille via `calendar.Calendar(firstweekday=0).monthdatescalendar`,
    passe : semaines, mois précédent/suivant, aujourd'hui, banques, créneaux.
  - POST : lit `banque_id`, `date` (ISO), `creneau`. Valide : banque existe, date
    parseable et **>= aujourd'hui**, créneau valide. Crée le `RendezVousDon`
    (statut Planifié). `messages.success` + redirect dashboard. Sinon
    `messages.error` + redirect planifierDon.
- `annulerRendezVous` (POST) : `get_object_or_404(RendezVousDon, id, donneur=<courant>)`,
  passe `statut='Annulé'`, `messages.success`, redirect dashboard.

### 4. Calendrier mensuel « maison » (template)

- Grille 7 colonnes (Lun→Dim), en-têtes jours, cases = jours du mois.
- Jours hors mois : estompés. Jours passés : désactivés (non cliquables).
- Clic sur un jour : petit JS vanilla → renseigne `<input type="hidden" name="date">`
  et surligne la case sélectionnée.
- Navigation mois précédent/suivant : liens `?annee=&mois=`.
- Sélecteur `banque_id` + `creneau` + bouton « Planifier le don ».

### 5. Dashboard donneur (accueil_donneur.html)

- `accueilDonneur` passe `rdv_a_venir` (statut Planifié, date >= today) et
  `rdv_passes` (date < today ou statut Effectué) du donneur courant.
- Bouton mock « Schedule Donation » → lien vers `planifierDon`.
- « Upcoming Donations » (fictif) → vrais `rdv_a_venir` avec bouton **Annuler**
  (POST vers `annulerRendezVous`, CSRF).
- « Past Donations » → `rdv_passes`.

### 6. URLs (donneur/urls.py)

- `donneur:planifierDon` → `planifier/`
- `donneur:annulerRendezVous` → `rendezvous/<int:rdv_id>/annuler/`

## Hors périmètre

- Rappels email / notifications.
- Limite de places par créneau (pas de capacité).
- Reprogrammation (= annuler + recréer).

## Tests

- Modèle : création d'un `RendezVousDon` ; `est_a_venir()`.
- `planifierDon` GET : 200, calendrier rendu (banques + créneaux), refus rôle non-donor.
- POST : crée un rdv (date future) ; refuse date passée ; refuse banque invalide.
- Dashboard : liste les rdv à venir du donneur, pas ceux d'un autre donneur.
- `annulerRendezVous` : passe à Annulé ; refuse d'annuler le rdv d'autrui (404).
