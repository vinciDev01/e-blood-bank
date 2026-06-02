from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

from datetime import date

from _auth.models import BanqueDeSang
from bankDeSang.models import PocheDeSang, StockDeSang

User = get_user_model()


def _creer_banque(username):
    user = User.objects.create_user(username=username, password='x', role='blood_bank')
    with patch('_auth.models.geocoder_adresse', return_value=None):
        BanqueDeSang.objects.create(
            nom_etablissement='Banque Test Topbar', responsable='Resp', adresse='Rue',
            ville='Lomé', code_postal='00000', pays='Togo', telephone='90000000', user=user,
        )
    return user


class TopbarBankDeSangTest(TestCase):
    def test_topbar_affiche_le_nom_de_letablissement(self):
        user = _creer_banque('bank_topbar')
        self.client.force_login(user)
        resp = self.client.get(reverse('bankDeSang:accueilBankDeSang'))
        self.assertEqual(resp.status_code, 200)
        # Le nom de l'établissement s'affiche...
        self.assertContains(resp, 'Banque Test Topbar')
        # ...et la balise n'apparaît plus en texte brut (bug de balise coupée).
        self.assertNotContains(resp, '{{ user.last_name')


class GestionStockDonneurTest(TestCase):
    def test_numero_donneur_invalide_ne_provoque_pas_d_erreur(self):
        user = _creer_banque('bank_stock')
        self.client.force_login(user)
        resp = self.client.post(reverse('bankDeSang:gestionStock'), {
            'matricule': 'PS-TEST-0001',
            'donneur': 'ZEREE',  # numéro de donneur inexistant / non numérique
            'date_de_prelevement': '2026-06-01',
            'groupe_sanguin': 'A-',
            'type_produit': 'Sang total',
        })
        # Plus de ValueError (500) : on redirige proprement...
        self.assertEqual(resp.status_code, 302)
        # ...et aucune poche n'est créée pour un numéro de donneur invalide.
        self.assertFalse(PocheDeSang.objects.filter(matricule='PS-TEST-0001').exists())


class CarteBanquesBankDeSangTest(TestCase):
    def test_banque_connectee_voit_la_carte(self):
        user = _creer_banque('bank_carte')
        self.client.force_login(user)
        resp = self.client.get(reverse('bankDeSang:carteBanques'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'id="banques-data"')
        # En-tête Referer requis par les tuiles OSM.
        self.assertEqual(resp.headers['Referrer-Policy'], 'strict-origin-when-cross-origin')

    def test_role_non_banque_est_redirige(self):
        user = User.objects.create_user(username='med_x', password='x', role='medical')
        self.client.force_login(user)
        resp = self.client.get(reverse('bankDeSang:carteBanques'))
        self.assertEqual(resp.status_code, 302)


class ModifierSupprimerStockTest(TestCase):
    def setUp(self):
        self.user = _creer_banque('bank_stockmod')
        self.bank = self.user.banque_de_sang
        self.stock = StockDeSang.objects.create(groupe_sanguin='A+', nombre_de_poches=5)
        PocheDeSang.objects.bulk_create([
            PocheDeSang(matricule='P-A-1', groupe_sanguin='A+', type_produit='Sang total',
                        date_de_prelevement=date(2026, 6, 1), date_expiration=date(2026, 7, 13),
                        est_disponible=True, bank_de_sang=self.bank),
            PocheDeSang(matricule='P-A-2', groupe_sanguin='A+', type_produit='Sang total',
                        date_de_prelevement=date(2026, 6, 1), date_expiration=date(2026, 7, 13),
                        est_disponible=True, bank_de_sang=self.bank),
        ])

    def test_modifier_met_a_jour_le_nombre_de_poches(self):
        self.client.force_login(self.user)
        resp = self.client.post(
            reverse('bankDeSang:modifierStock', args=[self.stock.id]),
            {'nombre_de_poches': '12'},
        )
        self.assertEqual(resp.status_code, 302)
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.nombre_de_poches, 12)

    def test_modifier_refuse_en_get(self):
        self.client.force_login(self.user)
        resp = self.client.get(reverse('bankDeSang:modifierStock', args=[self.stock.id]))
        self.assertEqual(resp.status_code, 302)
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.nombre_de_poches, 5)  # inchangé

    def test_supprimer_retire_les_poches_et_supprime_le_stock(self):
        self.client.force_login(self.user)
        resp = self.client.post(reverse('bankDeSang:supprimerStock', args=[self.stock.id]))
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(StockDeSang.objects.filter(id=self.stock.id).exists())
        # Les poches existent toujours mais sont retirées (traçabilité conservée).
        poches = PocheDeSang.objects.filter(groupe_sanguin='A+', bank_de_sang=self.bank)
        self.assertEqual(poches.count(), 2)
        self.assertEqual(poches.filter(est_disponible=True).count(), 0)

    def test_supprimer_refuse_role_non_banque(self):
        autre = User.objects.create_user(username='med_z', password='x', role='medical')
        self.client.force_login(autre)
        resp = self.client.post(reverse('bankDeSang:supprimerStock', args=[self.stock.id]))
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(StockDeSang.objects.filter(id=self.stock.id).exists())
