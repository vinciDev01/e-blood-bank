# OTP paramétrable via `.env` — Design

**Date :** 2026-06-01
**Statut :** Validé (design)
**Périmètre :** Permettre de désactiver l'OTP au login via un réglage
d'environnement, pour éviter de saisir un code à chaque connexion en test/dev.

## Décisions

- Réglage **`OTP_ENABLED`** lu depuis l'environnement, **défaut `True`** (prod sûre).
- Désactivation = login direct (sans code) ; activation = flux OTP actuel inchangé.
- Contrôle global via `.env` (pas d'UI, pas de migration).

## Composants

### 1. Réglage — `eBloodBank/info.py`
```python
OTP_ENABLED = os.environ.get('OTP_ENABLED', 'True') == 'True'
```
Ajouté à `.env.example` avec la valeur `True`. En dev, `OTP_ENABLED=False` dans `.env`.

### 2. Vue `logIn` — `_auth/views.py`
- Après authentification réussie :
  - si `settings.OTP_ENABLED` est **False** : `login(request, user, backend=...)`
    puis redirection via le helper `_rediriger_apres_login(user)` — aucun OTPCode,
    aucun email.
  - sinon : comportement actuel (invalider anciens codes, générer, envoyer l'email,
    stocker `otp_user_id`, rediriger vers `verifyOTP`).

### 3. Helper partagé — `_auth/views.py`
`_rediriger_apres_login(user)` centralise la redirection par rôle (admin/medical/
generic/donor/blood_bank) aujourd'hui dupliquée dans `verifyOTP`. Utilisé par le
login direct **et** par `verifyOTP` après validation du code.

### 4. Tests — `_auth/tests.py`
- `@override_settings(OTP_ENABLED=False)` : POST login valide → utilisateur connecté
  (`_auth.get_user(client).is_authenticated`), redirection 302 vers le dashboard du
  rôle, **0 `OTPCode`** créé.
- `@override_settings(OTP_ENABLED=True)` : POST login valide (envoi email mocké) →
  redirection vers `verifyOTP`, **1 `OTPCode`** créé, utilisateur **pas** encore connecté.

## Hors périmètre (inchangé)

- `verifyOTP`, `resendOTP`, modèle `OTPCode`, templates.
- Aucune modification du flux quand `OTP_ENABLED=True`.

## Sécurité

- Défaut `True` ⇒ aucun affaiblissement en production.
- Le bypass exige `OTP_ENABLED=False` explicite dans l'environnement (généralement
  le `.env` de dev, non versionné).

## Critères de succès

1. `OTP_ENABLED=False` : la connexion ne demande plus de code (login direct, bon dashboard).
2. `OTP_ENABLED=True` : flux OTP identique à l'actuel.
3. Tests verts pour les deux modes.
