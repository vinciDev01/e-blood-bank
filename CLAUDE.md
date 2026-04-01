# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

eBloodBank is a Django 4.2 blood bank management system (French-language UI). It manages blood donations, blood bag inventory, medical service requests, and donor tracking. The database is MySQL (configured for `root:root@localhost:3306/ebloodbank`). A `db.sqlite3` exists but is not the configured database.

## Commands

```bash
# Install dependencies (virtual env at .venv/)
pip install -r requirements.txt

# Run development server
python manage.py runserver

# Run migrations
python manage.py makemigrations
python manage.py migrate

# Run tests (no tests written yet - test files are empty)
python manage.py test
python manage.py test <app_name>  # e.g. python manage.py test bankDeSang
```

## Architecture

### Django Apps

- **eBloodBank/** — Project settings. `settings.py` imports email config from `info.py`. Custom user model is `_auth.CustomUser`.
- **_auth/** — Authentication and user models. Contains ALL domain entity models (`CustomUser`, `Utilisateur`, `Donneur`, `BanqueDeSang`, `ServiceMedicaux`) in `_auth/models.py`. Uses a custom auth backend (`CustomUserBackend`) and token-based email activation (`token.py`).
- **bankDeSang/** — Blood bag management. Models: `PocheDeSang` (blood bags with QR codes), `DonDeSang` (donations), `StockDeSang` (inventory by blood type). References models from `_auth.models`.
- **serviceMedicaux/** — Medical service operations. Models: `Patient`, `DemandeDeSang` (blood requests with JSON fields for multi-group tracking), `Stock_de_sang` (per-service stock).
- **donneur/** — Donor-specific views. Models are in `_auth/models.py`, not here (`donneur/models.py` is entirely commented out).
- **frontend/** — Public-facing pages, templates, and static assets. Templates are under `frontend/templates/frontend/` with subdirectories per domain (bankDeSang/, serviceMedicaux/, donneur/).

### Key Design Decisions

- **All user-related models live in `_auth/models.py`**, not in their respective apps. `Donneur`, `BanqueDeSang`, `ServiceMedicaux`, and `Utilisateur` all have a `OneToOneField` to `CustomUser`.
- **Role-based routing**: Login (`_auth/views.py:logIn`) redirects to different dashboards based on `CustomUser.role` (generic, medical, donor, blood_bank, admin).
- **Role-based access control** via `decorateurs.py:check_role()` decorator.
- **Blood requests use JSON fields** (`groupe_sanguin`, `nombre_poches`, `nombre_poches_allouees`, `poches_recues`, `etat_groupes` in `DemandeDeSang`) to track multiple blood types per request.
- **QR codes** are auto-generated for blood bags (`PocheDeSang.generate_qr_code()`) using the `qrcode` library, saved to `media/QR code/`.
- **Email activation** for user registration via Gmail SMTP (config in `eBloodBank/info.py`).

### URL Structure

- `/` — Frontend public pages
- `/admin/` — Django admin
- `/_auth/` — Authentication (login, register, activation)
- `/bankDeSang/` — Blood bank operations
- `/serviceMedicaux/` — Medical service operations
- `/donneur/` — Donor operations

## Important Notes

- `eBloodBank/info.py` contains email credentials — treat as sensitive.
- The codebase is French: model names, field names, comments, and UI text are in French.
- Blood types used throughout: A+, A-, B+, B-, AB+, AB-, O+, O-.
- Blood bag expiration defaults to 42 days from collection date.
