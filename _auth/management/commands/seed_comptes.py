"""Seed de comptes de démonstration par rôle + données métier.

Crée un utilisateur connectable pour chaque rôle (emails prévisibles) avec son
profil, ainsi qu'un petit jeu de données (poches/stock, demande de sang, don).

Idempotent : un compte dont le `username` existe déjà est ignoré (et ses données
associées ne sont pas recréées).

Usage :
    python manage.py seed_comptes
"""
import os
from datetime import date, timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from _auth.models import Donneur, BanqueDeSang, ServiceMedicaux, Utilisateur
from serviceMedicaux.models import Patient, DemandeDeSang
from bankDeSang.models import PocheDeSang, StockDeSang, DonDeSang, HistoriqueStock

User = get_user_model()

# Mot de passe commun des comptes de démonstration (surchargeable).
MOT_DE_PASSE = os.environ.get('SEED_PASSWORD', '00000000')


class Command(BaseCommand):
    help = "Crée des comptes de démonstration par rôle + des données métier."

    def add_arguments(self, parser):
        parser.add_argument(
            '--force', action='store_true',
            help="Autorise l'exécution même hors mode DEBUG (production).",
        )

    def handle(self, *args, **options):
        if not settings.DEBUG and not options['force']:
            raise CommandError(
                "Commande de démonstration : refus de seeder hors mode DEBUG. "
                "Relancez avec --force si c'est volontaire."
            )

        with transaction.atomic():
            self._donneur()
            self._banque()
            self._medical()
            self._generic()
            self._admin()

        self.stdout.write(self.style.SUCCESS(
            f"Seed des comptes terminé. Mot de passe commun : {MOT_DE_PASSE}"
        ))

    # -- utilitaire ---
    def _creer_user(self, email, role, **extra):
        if User.objects.filter(username=email).exists():
            self.stdout.write(self.style.WARNING(f"Ignoré (existe déjà) : {email}"))
            return None
        return User.objects.create_user(
            username=email, email=email, password=MOT_DE_PASSE,
            role=role, is_active=True, **extra,
        )

    # -- comptes 
    def _donneur(self):
        u = self._creer_user('donneur@ebloodbank.com', 'donor')
        if not u:
            return
        donneur = Donneur.objects.create(
            user=u, nom='Doe', prenom='Jean', date_naissance=date(1995, 5, 12),
            sexe='M', groupe_sanguin='O+', adresse='Rue des Dons', ville='Lomé',
            code_postal='01BP', pays='Togo', telephone='+228 90 00 00 01',
        )
        DonDeSang.objects.create(donneur=donneur, type_produit='Sang total')
        self.stdout.write(self.style.SUCCESS('Créé : donneur@ebloodbank.com (+ 1 don)'))

    def _banque(self):
        u = self._creer_user('banque@ebloodbank.com', 'blood_bank')
        if not u:
            return
        # bulk_create contourne le save() géocodant : coordonnées posées telles quelles.
        BanqueDeSang.objects.bulk_create([
            BanqueDeSang(
                user=u, nom_etablissement='Banque Centrale eBloodBank',
                responsable='Dr. Kossi Adjévi', adresse='Avenue de la Santé',
                ville='Lomé', code_postal='01BP', pays='Togo',
                telephone='+228 90 00 00 02', latitude=6.1725, longitude=1.2314,
            )
        ])
        banque = BanqueDeSang.objects.get(user=u)
        poches = [
            PocheDeSang(
                matricule=f'PS-DEMO-{i:03d}', groupe_sanguin=grp, type_produit='Sang total',
                date_de_prelevement=date.today(), date_expiration=date.today() + timedelta(days=42),
                est_disponible=True, bank_de_sang=banque,
            )
            for i, grp in enumerate(['O+', 'A+', 'B+', 'O-'], start=1)
        ]
        PocheDeSang.objects.bulk_create(poches)
        for poche in poches:
            StockDeSang.enregistrer_stock(poche, 1)
        HistoriqueStock.enregistrer(
            banque=banque, utilisateur=u, action='ajout', groupe_sanguin='O+',
            description='Ajout initial de poches (seed de démonstration).',
        )
        self.stdout.write(self.style.SUCCESS('Créé : banque@ebloodbank.com (+ poches, stock, historique)'))

    def _medical(self):
        u = self._creer_user('medical@ebloodbank.com', 'medical')
        if not u:
            return
        service = ServiceMedicaux.objects.create(
            user=u, nom_etablissement='Hôpital de Démonstration', type_etablissement='Public',
            responsable='Dr. Améyo Dossou', adresse='Boulevard Central', email='medical@ebloodbank.com',
            ville='Lomé', code_postal='01BP', pays='Togo', telephone='+228 90 00 00 03',
            numero_licence='LIC-DEMO', numero_enregistrement='ENR-DEMO',
        )
        groupes = ['O+', 'A+', 'B+', 'AB+', 'O-', 'A-', 'B-', 'AB-']
        urgences = ['Immédiate', '24 heures', 'Non urgent']
        motifs = ['Chirurgie', 'Accident', 'Maladie', 'Autre']
        produits = ['Sang total', 'Plasma', 'Plaquettes', 'Concentré de globules rouges']
        for i in range(12):
            grp = groupes[i % len(groupes)]
            patient = Patient.objects.create(
                nom_complet=f'Patient Démo {i + 1}', date_de_naissance=date(1990, 1, 1),
                proche='Proche Démo', groupe_sanguin=grp, telephone_proche='+228 90 00 00 09',
            )
            DemandeDeSang.objects.create(
                serviceMedicaux=service, patient=patient,
                groupe_sanguin={service.email: [grp]}, type_produit=produits[i % len(produits)],
                nombre_poches={service.email: [(i % 4) + 1]}, urgence=urgences[i % len(urgences)],
                motif=motifs[i % len(motifs)], etat='En attente',
                etat_groupes={grp: 'En attente'}, notification_envoyee=False,
            )
        self.stdout.write(self.style.SUCCESS('Créé : medical@ebloodbank.com (+ patients, 12 demandes)'))

    def _generic(self):
        u = self._creer_user('generic@ebloodbank.com', 'generic')
        if not u:
            return
        Utilisateur.objects.create(user=u, nom='Public', prenom='Visiteur', email='generic@ebloodbank.com')
        self.stdout.write(self.style.SUCCESS('Créé : generic@ebloodbank.com'))

    def _admin(self):
        u = self._creer_user('admin@ebloodbank.com', 'admin', is_staff=True, is_superuser=True)
        if not u:
            return
        self.stdout.write(self.style.SUCCESS('Créé : admin@ebloodbank.com (superuser)'))
