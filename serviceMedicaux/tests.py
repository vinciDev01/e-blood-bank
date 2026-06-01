from unittest.mock import patch
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from _auth.models import BanqueDeSang

User = get_user_model()


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
        # L'îlot de données JSON est présent (carte rendue côté client par Leaflet).
        self.assertContains(resp, 'id="banques-data"')

    def test_seules_les_banques_geocodees_sont_envoyees(self):
        self.client.force_login(self.medical)
        resp = self.client.get(reverse('serviceMedicaux:carteBanques'))
        banques = resp.context['banques']
        noms = [b['nom'] for b in banques]
        self.assertIn('Banque Visible', noms)
        self.assertNotIn('Banque Cachee', noms)

    def test_role_non_medical_est_redirige(self):
        autre = User.objects.create_user(username='autre', password='x', role='donor')
        self.client.force_login(autre)
        resp = self.client.get(reverse('serviceMedicaux:carteBanques'))
        self.assertEqual(resp.status_code, 302)

    def test_carte_transmet_referer_pour_tuiles_osm(self):
        # OpenStreetMap exige un Referer ; la politique globale 'same-origin'
        # n'en envoie aucun en cross-origin. La page doit transmettre l'origine.
        self.client.force_login(self.medical)
        resp = self.client.get(reverse('serviceMedicaux:carteBanques'))
        self.assertEqual(resp.headers['Referrer-Policy'], 'strict-origin-when-cross-origin')
