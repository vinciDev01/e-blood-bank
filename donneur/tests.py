from datetime import date, timedelta
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

from _auth.models import Donneur, BanqueDeSang
from donneur.models import RendezVousDon

User = get_user_model()


def _donneur(username='don_rdv'):
    u = User.objects.create_user(username=username, password='x', role='donor')
    d = Donneur.objects.create(
        nom='Test', prenom='Donneur', date_naissance=date(1990, 1, 1), sexe='M',
        groupe_sanguin='O+', adresse='A', ville='Lomé', code_postal='0', pays='Togo',
        telephone='90000000', user=u,
    )
    return u, d


def _banque(username='bank_rdv'):
    u = User.objects.create_user(username=username, password='x', role='blood_bank')
    with patch('_auth.models.geocoder_adresse', return_value=None):
        return BanqueDeSang.objects.create(
            nom_etablissement='Banque RDV', responsable='R', adresse='Rue',
            ville='Lomé', code_postal='0', pays='Togo', telephone='90000000', user=u,
        )


class RendezVousModelTest(TestCase):
    def test_creation_et_est_a_venir(self):
        _, d = _donneur()
        b = _banque()
        futur = RendezVousDon.objects.create(
            donneur=d, banque=b, date=date.today() + timedelta(days=3), creneau='08:00-10:00')
        passe = RendezVousDon.objects.create(
            donneur=d, banque=b, date=date.today() - timedelta(days=3), creneau='08:00-10:00')
        self.assertTrue(futur.est_a_venir())
        self.assertFalse(passe.est_a_venir())


class PlanifierDonViewTest(TestCase):
    def test_get_affiche_calendrier(self):
        u, _ = _donneur()
        _banque()
        self.client.force_login(u)
        resp = self.client.get(reverse('donneur:planifierDon'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Planifier un don')
        self.assertContains(resp, 'Banque RDV')
        self.assertContains(resp, '08:00 - 10:00')

    def test_refuse_role_non_donor(self):
        autre = User.objects.create_user(username='med_rdv', password='x', role='medical')
        self.client.force_login(autre)
        resp = self.client.get(reverse('donneur:planifierDon'))
        self.assertEqual(resp.status_code, 302)

    def test_post_cree_un_rendez_vous(self):
        u, d = _donneur()
        b = _banque()
        self.client.force_login(u)
        futur = (date.today() + timedelta(days=5)).isoformat()
        resp = self.client.post(reverse('donneur:planifierDon'), {
            'banque_id': b.id, 'date': futur, 'creneau': '10:00-12:00',
        })
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(RendezVousDon.objects.filter(donneur=d).count(), 1)
        rdv = RendezVousDon.objects.get(donneur=d)
        self.assertEqual(rdv.statut, 'Planifié')
        self.assertEqual(rdv.creneau, '10:00-12:00')

    def test_post_refuse_date_passee(self):
        u, d = _donneur()
        b = _banque()
        self.client.force_login(u)
        passe = (date.today() - timedelta(days=1)).isoformat()
        self.client.post(reverse('donneur:planifierDon'), {
            'banque_id': b.id, 'date': passe, 'creneau': '10:00-12:00',
        })
        self.assertEqual(RendezVousDon.objects.filter(donneur=d).count(), 0)

    def test_post_refuse_banque_invalide(self):
        u, d = _donneur()
        _banque()
        self.client.force_login(u)
        futur = (date.today() + timedelta(days=5)).isoformat()
        self.client.post(reverse('donneur:planifierDon'), {
            'banque_id': 99999, 'date': futur, 'creneau': '10:00-12:00',
        })
        self.assertEqual(RendezVousDon.objects.filter(donneur=d).count(), 0)


class DashboardEtAnnulationTest(TestCase):
    def test_dashboard_liste_les_rdv_du_donneur(self):
        u, d = _donneur('don_a')
        b = _banque()
        RendezVousDon.objects.create(
            donneur=d, banque=b, date=date.today() + timedelta(days=2), creneau='14:00-16:00')
        # rdv d'un autre donneur : ne doit pas apparaître
        _, autre = _donneur('don_b')
        RendezVousDon.objects.create(
            donneur=autre, banque=b, date=date.today() + timedelta(days=2), creneau='16:00-18:00')

        self.client.force_login(u)
        resp = self.client.get(reverse('donneur:accueilDonneur'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context['rdv_a_venir']), 1)
        self.assertContains(resp, '14:00-16:00')
        self.assertNotContains(resp, '16:00-18:00')

    def test_annulation_passe_statut_a_annule(self):
        u, d = _donneur('don_c')
        b = _banque()
        rdv = RendezVousDon.objects.create(
            donneur=d, banque=b, date=date.today() + timedelta(days=2), creneau='08:00-10:00')
        self.client.force_login(u)
        resp = self.client.post(reverse('donneur:annulerRendezVous', args=[rdv.id]))
        self.assertEqual(resp.status_code, 302)
        rdv.refresh_from_db()
        self.assertEqual(rdv.statut, 'Annulé')

    def test_ne_peut_pas_annuler_le_rdv_d_un_autre(self):
        u, _ = _donneur('don_d')
        _, autre = _donneur('don_e')
        b = _banque()
        rdv_autre = RendezVousDon.objects.create(
            donneur=autre, banque=b, date=date.today() + timedelta(days=2), creneau='08:00-10:00')
        self.client.force_login(u)
        resp = self.client.post(reverse('donneur:annulerRendezVous', args=[rdv_autre.id]))
        self.assertEqual(resp.status_code, 404)
        rdv_autre.refresh_from_db()
        self.assertEqual(rdv_autre.statut, 'Planifié')
