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


class FiltreGroupeCentresTest(TestCase):
    def _banque(self, username, nom):
        u = User.objects.create_user(username=username, password='x', role='blood_bank')
        with patch('_auth.models.geocoder_adresse', return_value=(6.13, 1.22)):
            return BanqueDeSang.objects.create(
                nom_etablissement=nom, responsable='R', adresse='Rue',
                ville='Lomé', code_postal='0', pays='Togo', telephone='90000000', user=u,
            )

    def _poche(self, banque, groupe, dispo=True, matricule='P-1'):
        from datetime import date, timedelta
        from bankDeSang.models import PocheDeSang
        return PocheDeSang.objects.create(
            matricule=matricule, type_produit='Sang total', groupe_sanguin=groupe,
            date_expiration=date.today() + timedelta(days=42), est_disponible=dispo,
            bank_de_sang=banque,
        )

    def test_donnees_carte_filtre_par_groupe(self):
        b_on = self._banque('bq_on', 'Banque O-')
        b_off = self._banque('bq_off', 'Banque A+')
        self._poche(b_on, 'O-', matricule='PO-1')
        self._poche(b_off, 'A+', matricule='PA-1')

        toutes = BanqueDeSang.donnees_carte()
        self.assertEqual(len(toutes), 2)
        self.assertTrue(all('dispo' in d for d in toutes))

        filtre = BanqueDeSang.donnees_carte('O-')
        noms = [d['nom'] for d in filtre]
        self.assertEqual(noms, ['Banque O-'])
        self.assertEqual(filtre[0]['dispo_groupe'], 1)

    def test_poche_non_disponible_exclue(self):
        b = self._banque('bq_u', 'Banque O- indispo')
        self._poche(b, 'O-', dispo=False, matricule='PO-U')
        self.assertEqual(BanqueDeSang.donnees_carte('O-'), [])

    def test_vue_centres_filtre_par_parametre_groupe(self):
        b_on = self._banque('bq_v1', 'Centre O-')
        b_off = self._banque('bq_v2', 'Centre A+')
        self._poche(b_on, 'O-', matricule='PV-O')
        self._poche(b_off, 'A+', matricule='PV-A')

        resp = self.client.get(reverse('frontend:centresDeDon'), {'groupe': 'O-'})
        self.assertEqual(resp.status_code, 200)
        noms = [d['nom'] for d in resp.context['banques']]
        self.assertEqual(noms, ['Centre O-'])
        self.assertEqual(resp.context['groupe_selectionne'], 'O-')

    def test_groupe_invalide_ignore_le_filtre(self):
        self._banque('bq_inv', 'Centre X')
        resp = self.client.get(reverse('frontend:centresDeDon'), {'groupe': 'ZZZ'})
        self.assertEqual(resp.context['groupe_selectionne'], '')
        self.assertEqual(len(resp.context['banques']), 1)
