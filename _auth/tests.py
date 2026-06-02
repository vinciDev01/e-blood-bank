import json
from unittest.mock import patch, MagicMock
from django.test import TestCase, override_settings
from django.urls import reverse
from _auth.geocoding import geocoder_adresse


class GeocoderAdresseTest(TestCase):
    def _fake_response(self, payload):
        fake = MagicMock()
        fake.read.return_value = json.dumps(payload).encode('utf-8')
        fake.__enter__.return_value = fake
        fake.__exit__.return_value = False
        return fake

    @patch('_auth.geocoding.urlopen')
    def test_retourne_coordonnees_quand_ok(self, mock_urlopen):
        mock_urlopen.return_value = self._fake_response({
            'status': 'OK',
            'results': [{'geometry': {'location': {'lat': 6.13, 'lng': 1.22}}}],
        })
        coords = geocoder_adresse('Rue 1', 'Lomé', '00000', 'Togo')
        self.assertEqual(coords, (6.13, 1.22))

    @patch('_auth.geocoding.urlopen')
    def test_retourne_none_quand_zero_result(self, mock_urlopen):
        mock_urlopen.return_value = self._fake_response({
            'status': 'ZERO_RESULTS', 'results': [],
        })
        self.assertIsNone(geocoder_adresse('xxx', '', '', ''))

    @patch('_auth.geocoding.urlopen', side_effect=Exception('réseau coupé'))
    def test_retourne_none_si_exception(self, mock_urlopen):
        self.assertIsNone(geocoder_adresse('Rue 1', 'Lomé', '00000', 'Togo'))


from unittest.mock import patch
from django.contrib.auth import get_user_model
from _auth.models import BanqueDeSang

User = get_user_model()


class BanqueDeSangSaveTest(TestCase):
    def _user(self, username):
        return User.objects.create_user(
            username=username, password='x', role='blood_bank'
        )

    @patch('_auth.models.geocoder_adresse', return_value=(6.13, 1.22))
    def test_save_remplit_coordonnees(self, mock_geo):
        banque = BanqueDeSang.objects.create(
            nom_etablissement='Banque A', responsable='R', adresse='Rue 1',
            ville='Lomé', code_postal='00000', pays='Togo', telephone='90000000',
            user=self._user('b1'),
        )
        self.assertEqual(banque.latitude, 6.13)
        self.assertEqual(banque.longitude, 1.22)
        mock_geo.assert_called_once()

    @patch('_auth.models.geocoder_adresse', return_value=None)
    def test_save_sans_geocodage_reste_none(self, mock_geo):
        banque = BanqueDeSang.objects.create(
            nom_etablissement='Banque B', responsable='R', adresse='Rue 2',
            ville='Lomé', code_postal='00000', pays='Togo', telephone='90000001',
            user=self._user('b2'),
        )
        self.assertIsNone(banque.latitude)
        self.assertIsNone(banque.longitude)

    @patch('_auth.models.geocoder_adresse', return_value=(6.13, 1.22))
    def test_save_ne_regeocode_pas_si_coords_presentes(self, mock_geo):
        banque = BanqueDeSang.objects.create(
            nom_etablissement='Banque C', responsable='R', adresse='Rue 3',
            ville='Lomé', code_postal='00000', pays='Togo', telephone='90000002',
            user=self._user('b3'),
        )
        mock_geo.reset_mock()
        banque.telephone = '90000099'  # adresse inchangée
        banque.save()
        mock_geo.assert_not_called()


from io import StringIO
from django.core.management import call_command


class GeocoderBanquesCommandTest(TestCase):
    @patch('_auth.models.geocoder_adresse', return_value=None)
    def test_commande_geocode_banques_sans_coords(self, mock_save_geo):
        # Créée sans coords (géocodage save renvoie None)
        banque = BanqueDeSang.objects.create(
            nom_etablissement='Banque D', responsable='R', adresse='Rue 4',
            ville='Lomé', code_postal='00000', pays='Togo', telephone='90000003',
            user=User.objects.create_user(username='b4', password='x', role='blood_bank'),
        )
        self.assertIsNone(banque.latitude)

        with patch('_auth.management.commands.geocoder_banques.geocoder_adresse',
                   return_value=(6.13, 1.22)):
            out = StringIO()
            call_command('geocoder_banques', stdout=out)

        banque.refresh_from_db()
        self.assertEqual(banque.latitude, 6.13)
        self.assertEqual(banque.longitude, 1.22)


class SeedBanquesCommandTest(TestCase):
    def test_seed_cree_banques_avec_coordonnees(self):
        call_command('seed_banques', force=True, stdout=StringIO())
        banques = BanqueDeSang.objects.all()
        self.assertGreater(banques.count(), 0)
        # Toutes les banques seedées ont des coordonnées renseignées.
        self.assertFalse(banques.filter(latitude__isnull=True).exists())
        self.assertFalse(banques.filter(longitude__isnull=True).exists())

    def test_seed_est_idempotent(self):
        call_command('seed_banques', force=True, stdout=StringIO())
        total_apres_premier_run = BanqueDeSang.objects.count()
        call_command('seed_banques', force=True, stdout=StringIO())
        total_apres_second_run = BanqueDeSang.objects.count()
        self.assertEqual(total_apres_premier_run, total_apres_second_run)

    def test_seed_refuse_hors_debug_sans_force(self):
        from django.core.management.base import CommandError
        with self.settings(DEBUG=False):
            with self.assertRaises(CommandError):
                call_command('seed_banques', stdout=StringIO())


from _auth.models import OTPCode


class OtpParametrableTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='login_test', password='motdepasse123', role='generic'
        )

    @override_settings(OTP_ENABLED=False)
    def test_login_direct_quand_otp_desactive(self):
        resp = self.client.post(reverse('_auth:login'), {
            'email': 'login_test', 'password': 'motdepasse123',
        })
        self.assertEqual(resp.status_code, 302)
        # Aucun code OTP généré, utilisateur connecté directement.
        self.assertEqual(OTPCode.objects.count(), 0)
        self.assertIn('_auth_user_id', self.client.session)

    @override_settings(OTP_ENABLED=True)
    @patch('_auth.views.send_html_email')
    def test_flux_otp_quand_active(self, mock_send):
        resp = self.client.post(reverse('_auth:login'), {
            'email': 'login_test', 'password': 'motdepasse123',
        })
        self.assertEqual(resp.status_code, 302)
        # Un code OTP est créé, l'utilisateur n'est PAS encore connecté.
        self.assertEqual(OTPCode.objects.count(), 1)
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertEqual(self.client.session.get('otp_user_id'), self.user.pk)


from datetime import date as _date
from _auth.models import Donneur, ServiceMedicaux


class NomAffichageTest(TestCase):
    def test_donneur_renvoie_nom_prenom(self):
        u = User.objects.create_user(username='d1', password='x', role='donor')
        Donneur.objects.create(
            nom='Doe', prenom='John', date_naissance=_date(2000, 1, 1), sexe='M',
            groupe_sanguin='A+', adresse='A', ville='Lomé', code_postal='0',
            pays='Togo', telephone='0', user=u,
        )
        self.assertEqual(u.nom_affichage, 'Doe John')

    @patch('_auth.models.geocoder_adresse', return_value=None)
    def test_banque_renvoie_nom_etablissement(self, _geo):
        u = User.objects.create_user(username='b1', password='x', role='blood_bank')
        BanqueDeSang.objects.create(
            nom_etablissement='Ma Banque', responsable='R', adresse='A', ville='Lomé',
            code_postal='0', pays='Togo', telephone='0', user=u,
        )
        self.assertEqual(u.nom_affichage, 'Ma Banque')

    def test_service_medical_renvoie_nom_etablissement(self):
        u = User.objects.create_user(username='s1', password='x', role='medical')
        ServiceMedicaux.objects.create(
            nom_etablissement='Mon Hôpital', type_etablissement='Public', responsable='R',
            adresse='A', email='s1@example.com', ville='Lomé', code_postal='0',
            pays='Togo', telephone='0', numero_licence='L', numero_enregistrement='E', user=u,
        )
        self.assertEqual(u.nom_affichage, 'Mon Hôpital')

    def test_sans_profil_renvoie_username(self):
        u = User.objects.create_user(username='solo', password='x', role='generic')
        self.assertEqual(u.nom_affichage, 'solo')


from _auth.models import Donneur, ServiceMedicaux, Utilisateur


class SeedComptesCommandTest(TestCase):
    COMPTES = [
        ('donneur@ebloodbank.com', 'donor'),
        ('banque@ebloodbank.com', 'blood_bank'),
        ('medical@ebloodbank.com', 'medical'),
        ('generic@ebloodbank.com', 'generic'),
        ('admin@ebloodbank.com', 'admin'),
    ]

    def test_cree_un_compte_par_role_avec_profil(self):
        call_command('seed_comptes', force=True, stdout=StringIO())
        for email, role in self.COMPTES:
            u = User.objects.filter(username=email).first()
            self.assertIsNotNone(u, email)
            self.assertEqual(u.role, role)
        self.assertTrue(User.objects.get(username='admin@ebloodbank.com').is_superuser)
        self.assertTrue(Donneur.objects.filter(user__username='donneur@ebloodbank.com').exists())
        self.assertTrue(BanqueDeSang.objects.filter(user__username='banque@ebloodbank.com').exists())
        self.assertTrue(ServiceMedicaux.objects.filter(user__username='medical@ebloodbank.com').exists())
        self.assertTrue(Utilisateur.objects.filter(user__username='generic@ebloodbank.com').exists())

    def test_cree_les_donnees_metier(self):
        from serviceMedicaux.models import DemandeDeSang
        from bankDeSang.models import PocheDeSang, StockDeSang, DonDeSang
        call_command('seed_comptes', force=True, stdout=StringIO())
        self.assertTrue(DemandeDeSang.objects.exists())
        self.assertTrue(PocheDeSang.objects.exists())
        self.assertTrue(StockDeSang.objects.exists())
        self.assertTrue(DonDeSang.objects.exists())

    def test_est_idempotent(self):
        call_command('seed_comptes', force=True, stdout=StringIO())
        n = User.objects.count()
        call_command('seed_comptes', force=True, stdout=StringIO())
        self.assertEqual(User.objects.count(), n)

    def test_refuse_hors_debug_sans_force(self):
        from django.core.management.base import CommandError
        with self.settings(DEBUG=False):
            with self.assertRaises(CommandError):
                call_command('seed_comptes', stdout=StringIO())
