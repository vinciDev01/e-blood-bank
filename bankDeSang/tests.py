from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

from _auth.models import BanqueDeSang
from bankDeSang.models import PocheDeSang

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
