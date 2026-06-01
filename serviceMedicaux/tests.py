import json
from unittest.mock import patch
from django.test import TestCase, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model
from _auth.models import BanqueDeSang

User = get_user_model()


@override_settings(GOOGLE_MAPS_API_KEY='TEST_KEY')
class CarteBanquesViewTest(TestCase):
    def setUp(self):
        self.medical = User.objects.create_user(
            username='med', password='x', role='medical'
        )
        with patch('_auth.models.geocoder_adresse', return_value=(6.13, 1.22)):
            BanqueDeSang.objects.create(
                nom_etablissement='Banque Visible', responsable='R', adresse='Rue 1',
                ville='Lomé', code_postal='00000', pays='Togo', telephone='90000000',
                user=User.objects.create_user(username='bv', password='x', role='blood_bank'),
            )
        with patch('_auth.models.geocoder_adresse', return_value=None):
            BanqueDeSang.objects.create(
                nom_etablissement='Banque Cachee', responsable='R', adresse='Rue 2',
                ville='Lomé', code_postal='00000', pays='Togo', telephone='90000001',
                user=User.objects.create_user(username='bc', password='x', role='blood_bank'),
            )

    def test_role_medical_voit_la_carte(self):
        self.client.force_login(self.medical)
        resp = self.client.get(reverse('serviceMedicaux:carteBanques'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['google_maps_api_key'], 'TEST_KEY')

    def test_seules_les_banques_geocodees_sont_envoyees(self):
        self.client.force_login(self.medical)
        resp = self.client.get(reverse('serviceMedicaux:carteBanques'))
        banques = json.loads(resp.context['banques_json'])
        noms = [b['nom'] for b in banques]
        self.assertIn('Banque Visible', noms)
        self.assertNotIn('Banque Cachee', noms)

    def test_role_non_medical_est_redirige(self):
        autre = User.objects.create_user(username='autre', password='x', role='donor')
        self.client.force_login(autre)
        resp = self.client.get(reverse('serviceMedicaux:carteBanques'))
        self.assertEqual(resp.status_code, 302)
