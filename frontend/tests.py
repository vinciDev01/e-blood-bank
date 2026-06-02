from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

from _auth.models import BanqueDeSang

User = get_user_model()


class CentresDeDonTest(TestCase):
    def setUp(self):
        u = User.objects.create_user(username='centre1', password='x', role='blood_bank')
        with patch('_auth.models.geocoder_adresse', return_value=(6.13, 1.22)):
            BanqueDeSang.objects.create(
                nom_etablissement='Centre Public Test', responsable='R', adresse='Rue 1',
                ville='Lomé', code_postal='0', pays='Togo', telephone='90000000', user=u,
            )

    def test_page_centres_est_publique(self):
        resp = self.client.get(reverse('frontend:centresDeDon'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Centre Public Test')
        self.assertContains(resp, 'id="banques-data"')
        self.assertEqual(resp.headers['Referrer-Policy'], 'strict-origin-when-cross-origin')

    def test_accueil_a_le_lien_admin_et_la_redirection_centres(self):
        resp = self.client.get(reverse('frontend:accueil'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, reverse('_auth:administrationDashboard'))
        self.assertContains(resp, reverse('frontend:centresDeDon'))

    def test_accueil_montre_le_dashboard_medical_si_connecte(self):
        medecin = User.objects.create_user(username='med_acc', password='x', role='medical')
        self.client.force_login(medecin)
        resp = self.client.get(reverse('frontend:accueil'))
        self.assertContains(resp, reverse('serviceMedicaux:accueilServiceMedicaux'))

    def test_accueil_sans_dashboard_pour_anonyme(self):
        resp = self.client.get(reverse('frontend:accueil'))
        self.assertNotContains(resp, reverse('serviceMedicaux:accueilServiceMedicaux'))
