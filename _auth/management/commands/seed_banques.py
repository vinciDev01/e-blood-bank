"""Seed de banques de sang de démonstration, avec leurs géolocalisations.

Crée un jeu de banques de sang réparties au Togo, chacune avec des
coordonnées (latitude/longitude) déjà renseignées — elles apparaissent donc
immédiatement sur la carte sans appel à l'API de géocodage.

Idempotent : relancer la commande n'ajoute pas de doublons (chaque banque est
identifiée par le `username` de son utilisateur lié).

Usage :
    python manage.py seed_banques
"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from _auth.models import BanqueDeSang

User = get_user_model()

# Mot de passe par défaut des comptes de démonstration (à changer en production).
MOT_DE_PASSE_DEMO = 'ChangeMoi123!'

BANQUES = [
    {
        'username': 'banque_cnts_lome',
        'email': 'cnts.lome@ebloodbank.tg',
        'nom_etablissement': 'Centre National de Transfusion Sanguine',
        'responsable': 'Dr. Kossi Adjévi',
        'adresse': 'Avenue de Calais, Tokoin',
        'ville': 'Lomé', 'code_postal': '01BP', 'pays': 'Togo',
        'telephone': '+228 22 21 45 67',
        'latitude': 6.1710, 'longitude': 1.2089,
    },
    {
        'username': 'banque_chu_sylvanus',
        'email': 'banque.sylvanus@ebloodbank.tg',
        'nom_etablissement': 'Banque de Sang — CHU Sylvanus Olympio',
        'responsable': 'Dr. Améyo Dossou',
        'adresse': 'Boulevard Jean-Paul II, Tokoin',
        'ville': 'Lomé', 'code_postal': '01BP', 'pays': 'Togo',
        'telephone': '+228 22 21 25 01',
        'latitude': 6.1383, 'longitude': 1.2186,
    },
    {
        'username': 'banque_chu_campus',
        'email': 'banque.campus@ebloodbank.tg',
        'nom_etablissement': 'Banque de Sang — CHU Campus',
        'responsable': 'Dr. Yawo Agbéko',
        'adresse': 'Boulevard Eyadéma, Agoè',
        'ville': 'Lomé', 'code_postal': '03BP', 'pays': 'Togo',
        'telephone': '+228 22 25 44 10',
        'latitude': 6.1736, 'longitude': 1.2136,
    },
    {
        'username': 'banque_chr_tsevie',
        'email': 'banque.tsevie@ebloodbank.tg',
        'nom_etablissement': 'Banque de Sang — CHR Tsévié',
        'responsable': 'Dr. Komlan Mensah',
        'adresse': 'Route Nationale 1',
        'ville': 'Tsévié', 'code_postal': '00000', 'pays': 'Togo',
        'telephone': '+228 23 30 01 22',
        'latitude': 6.4253, 'longitude': 1.2136,
    },
    {
        'username': 'banque_chr_atakpame',
        'email': 'banque.atakpame@ebloodbank.tg',
        'nom_etablissement': 'Banque de Sang — CHR Atakpamé',
        'responsable': 'Dr. Afi Lawson',
        'adresse': 'Quartier Hôpital',
        'ville': 'Atakpamé', 'code_postal': '00000', 'pays': 'Togo',
        'telephone': '+228 24 40 02 33',
        'latitude': 7.5333, 'longitude': 1.1167,
    },
    {
        'username': 'banque_chr_sokode',
        'email': 'banque.sokode@ebloodbank.tg',
        'nom_etablissement': 'Banque de Sang — CHR Sokodé',
        'responsable': 'Dr. Issifou Tchaba',
        'adresse': 'Avenue de la Kozah',
        'ville': 'Sokodé', 'code_postal': '00000', 'pays': 'Togo',
        'telephone': '+228 25 50 03 44',
        'latitude': 8.9833, 'longitude': 1.1333,
    },
    {
        'username': 'banque_chr_kara',
        'email': 'banque.kara@ebloodbank.tg',
        'nom_etablissement': 'Banque de Sang — CHR Kara',
        'responsable': 'Dr. Essossimna Pana',
        'adresse': 'Boulevard du 13 Janvier',
        'ville': 'Kara', 'code_postal': '00000', 'pays': 'Togo',
        'telephone': '+228 26 60 04 55',
        'latitude': 9.5511, 'longitude': 1.1861,
    },
    {
        'username': 'banque_chr_dapaong',
        'email': 'banque.dapaong@ebloodbank.tg',
        'nom_etablissement': 'Banque de Sang — CHR Dapaong',
        'responsable': 'Dr. Nadjombe Gnandi',
        'adresse': 'Quartier Administratif',
        'ville': 'Dapaong', 'code_postal': '00000', 'pays': 'Togo',
        'telephone': '+228 27 70 05 66',
        'latitude': 10.8620, 'longitude': 0.2075,
    },
]


class Command(BaseCommand):
    help = "Crée des banques de sang de démonstration avec leurs géolocalisations."

    def handle(self, *args, **options):
        crees, ignores = 0, 0
        with transaction.atomic():
            for data in BANQUES:
                if User.objects.filter(username=data['username']).exists():
                    ignores += 1
                    self.stdout.write(self.style.WARNING(
                        f"Ignoré (existe déjà) : {data['nom_etablissement']}"
                    ))
                    continue

                user = User.objects.create_user(
                    username=data['username'],
                    email=data['email'],
                    password=MOT_DE_PASSE_DEMO,
                    role='blood_bank',
                )
                # bulk_create contourne BanqueDeSang.save() : les coordonnées
                # fournies sont enregistrées telles quelles, sans géocodage réseau.
                BanqueDeSang.objects.bulk_create([
                    BanqueDeSang(
                        user=user,
                        nom_etablissement=data['nom_etablissement'],
                        responsable=data['responsable'],
                        adresse=data['adresse'],
                        ville=data['ville'],
                        code_postal=data['code_postal'],
                        pays=data['pays'],
                        telephone=data['telephone'],
                        latitude=data['latitude'],
                        longitude=data['longitude'],
                    )
                ])
                crees += 1
                self.stdout.write(self.style.SUCCESS(
                    f"Créé : {data['nom_etablissement']} "
                    f"({data['latitude']}, {data['longitude']})"
                ))

        self.stdout.write(f"Terminé : {crees} créée(s), {ignores} ignorée(s).")
