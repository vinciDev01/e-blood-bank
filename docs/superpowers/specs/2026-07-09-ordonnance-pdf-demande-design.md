# Ordonnance PDF de demande de sang

Date : 2026-07-09
Branche : feature/carte-banques-de-sang

## Objectif

Quand une demande de sang est faite, générer une **ordonnance numérique PDF** au format
professionnel, stockée à la création et téléchargeable par le service émetteur ET la banque.

## Décisions

- Bibliothèque : **ReportLab** (pur Python, aucune dépendance système).
- Livraison : **fichier sauvegardé à la création** (FileField + migration) ; génération
  paresseuse au téléchargement si le fichier manque (demandes antérieures).
- Portée : **service médical (propriétaire) + banque de sang**.
- **QR de vérification** encodant la référence.

## Architecture

### 1. Modèle `DemandeDeSang` (serviceMedicaux/models.py)

- `ordonnance_pdf = models.FileField(upload_to='ordonnances/', null=True, blank=True)`
- `reference()` → `f"DEM-{id}-{année}"` (année de `date_demande` sinon année courante).
- `generer_ordonnance()` → construit le PDF via le générateur et l'enregistre dans
  `ordonnance_pdf` (`FileField.save(nom, ContentFile(bytes), save=True)`).
- Migration d'ajout du champ.

### 2. Générateur `serviceMedicaux/ordonnance.py` (ReportLab + qrcode)

`construire_pdf(demande) -> bytes` — document A4, Platypus :

- En-tête : logo `img/Logo_eBloodBank.png` (via staticfiles finders), titre
  « ORDONNANCE DE DEMANDE DE SANG », référence + date, QR (référence).
- Bloc « Établissement demandeur » : nom, adresse, ville, téléphone, responsable, email.
- Bloc « Patient » (si présent) : nom complet, date de naissance, groupe sanguin.
- Tableau « Détails de la demande » : type de produit, groupe(s) sanguin(s),
  nombre de poches, urgence, motif, état.
- Zone cachet/signature du responsable + date d'émission.
- Pied de page : mention document électronique + vérification par QR.

Helper `_valeurs(dict_json)` : aplatit les valeurs d'un JSONField indexé par email
(gère les 3 rôles) pour l'affichage des groupes/quantités.

### 3. Génération à la création

Dans `faireDemandeDeSang` (serviceMedicaux/views.py), après la création de la demande
pour chaque rôle → `demande.generer_ordonnance()`. Enveloppé pour ne pas casser la
création si la génération échoue (log + poursuite).

### 4. Vues de téléchargement (`FileResponse`, `as_attachment=True`)

- `serviceMedicaux:telechargerOrdonnance` `/ordonnance/<int:demande_id>/` — rôle medical
  ET `demande.serviceMedicaux == request.user.service_medical`.
- `bankDeSang:telechargerOrdonnance` `/ordonnance/<int:demande_id>/` — rôle blood_bank.
- Si `not demande.ordonnance_pdf` → `demande.generer_ordonnance()` puis servir.
- Nom fichier : `Ordonnance_{reference}.pdf`.

### 5. Boutons

Lien « Ordonnance PDF » par ligne :
- Service : `frontend/templates/frontend/serviceMedicaux/liste_demande_de_sang.html`.
- Banque : `frontend/templates/frontend/bankDeSang/liste_demandes_de_sang.html`.

### 6. Dépendance

Ajouter `reportlab` à `requirements.txt` + installer dans `.venv`.

## Hors périmètre

- Envoi email du PDF.
- Signature électronique cryptographique (seule une zone cachet/signature figure).

## Tests

- Génération : `construire_pdf` renvoie des octets commençant par `%PDF`.
- `generer_ordonnance()` remplit `ordonnance_pdf`.
- Download service : 200, `Content-Type: application/pdf`, `attachment`.
- Isolation : un service ne peut pas télécharger la demande d'un autre (302/404).
- Refus de rôle sur chaque endpoint.
- Génération paresseuse : demande sans `ordonnance_pdf` → téléchargement la crée.
