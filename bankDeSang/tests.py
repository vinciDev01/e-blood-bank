from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

from datetime import date

from _auth.models import BanqueDeSang
from bankDeSang.models import PocheDeSang, StockDeSang, HistoriqueStock

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

    def test_carte_a_le_filtre_et_filtre_par_groupe(self):
        from datetime import date, timedelta
        from _auth.models import BanqueDeSang
        from bankDeSang.models import PocheDeSang
        u = User.objects.create_user(username='bank_filtre', password='x', role='blood_bank')
        with patch('_auth.models.geocoder_adresse', return_value=(6.13, 1.22)):
            banque = BanqueDeSang.objects.create(
                nom_etablissement='Banque Filtre', responsable='R', adresse='Rue',
                ville='Lomé', code_postal='0', pays='Togo', telephone='90000000', user=u,
            )
        PocheDeSang.objects.create(
            matricule='BF-O', type_produit='Sang total', groupe_sanguin='O-',
            date_expiration=date.today() + timedelta(days=42), est_disponible=True,
            bank_de_sang=banque,
        )
        self.client.force_login(u)
        resp = self.client.get(reverse('bankDeSang:carteBanques'))
        self.assertContains(resp, 'name="groupe"')
        resp2 = self.client.get(reverse('bankDeSang:carteBanques'), {'groupe': 'O-'})
        noms = [b['nom'] for b in resp2.context['banques']]
        self.assertIn('Banque Filtre', noms)
        self.assertEqual(resp2.context['groupe_selectionne'], 'O-')


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

    def test_modifier_affiche_un_message_de_confirmation(self):
        stock = StockDeSang.objects.create(groupe_sanguin='B+', nombre_de_poches=2)
        self.client.force_login(self.user)
        resp = self.client.post(
            reverse('bankDeSang:modifierStock', args=[stock.id]),
            {'nombre_de_poches': '7'}, follow=True,
        )
        self.assertContains(resp, 'Stock mis à jour')

    def test_supprimer_affiche_un_message_de_confirmation(self):
        self.client.force_login(self.user)
        resp = self.client.post(
            reverse('bankDeSang:supprimerStock', args=[self.stock.id]), follow=True,
        )
        self.assertContains(resp, 'Stock supprimé')


class HistoriqueStockTest(TestCase):
    def setUp(self):
        self.user = _creer_banque('bank_hist')
        self.bank = self.user.banque_de_sang
        self.stock = StockDeSang.objects.create(groupe_sanguin='A+', nombre_de_poches=5)
        self.client.force_login(self.user)

    @patch('bankDeSang.models.PocheDeSang.generate_qr_code')
    def test_ajout_de_poche_est_journalise(self, _qr):
        self.client.post(reverse('bankDeSang:gestionStock'), {
            'matricule': 'PS-HIST-1', 'donneur': '',
            'date_de_prelevement': '2026-06-01', 'groupe_sanguin': 'A+',
            'type_produit': 'Sang total',
        })
        self.assertTrue(HistoriqueStock.objects.filter(action='ajout', banque=self.bank).exists())

    def test_modification_est_journalisee(self):
        self.client.post(reverse('bankDeSang:modifierStock', args=[self.stock.id]),
                         {'nombre_de_poches': '9'})
        h = HistoriqueStock.objects.filter(action='modification', banque=self.bank).first()
        self.assertIsNotNone(h)
        self.assertIn('5', h.description)
        self.assertIn('9', h.description)

    def test_suppression_est_journalisee(self):
        self.client.post(reverse('bankDeSang:supprimerStock', args=[self.stock.id]))
        self.assertTrue(HistoriqueStock.objects.filter(action='suppression', banque=self.bank).exists())

    def test_page_historique_liste_les_entrees(self):
        HistoriqueStock.objects.create(
            banque=self.bank, utilisateur=self.user, action='modification',
            groupe_sanguin='A+', description='Entrée de test historique',
        )
        resp = self.client.get(reverse('bankDeSang:historiqueStock'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Entrée de test historique')

    def test_page_historique_refuse_role_non_banque(self):
        autre = User.objects.create_user(username='med_h', password='x', role='medical')
        self.client.force_login(autre)
        resp = self.client.get(reverse('bankDeSang:historiqueStock'))
        self.assertEqual(resp.status_code, 302)


class DemandesFluxBanqueTest(TestCase):
    def _service(self, username, email):
        from _auth.models import ServiceMedicaux
        u = User.objects.create_user(username=username, password='x', role='medical')
        return ServiceMedicaux.objects.create(
            nom_etablissement='Hôpital Flux', type_etablissement='Public', responsable='R',
            adresse='A', email=email, ville='Lomé', code_postal='0', pays='Togo',
            telephone='0', numero_licence='L', numero_enregistrement='E', user=u,
        )

    def test_flux_renvoie_compte_et_max_id(self):
        from serviceMedicaux.models import DemandeDeSang
        service = self._service('med_flx', 'medflx@example.com')
        DemandeDeSang.objects.create(
            serviceMedicaux=service, type_produit='Sang total', urgence='Immédiate',
            motif='Accident', etat='En attente', groupe_sanguin={service.email: ['A+']},
        )
        DemandeDeSang.objects.create(
            serviceMedicaux=service, type_produit='Sang total', urgence='24 heures',
            motif='Chirurgie', etat='En attente', groupe_sanguin={service.email: ['O-']},
        )
        derniere = DemandeDeSang.objects.create(
            serviceMedicaux=service, type_produit='Sang total', urgence='Non urgent',
            motif='Maladie', etat='Approuvee',  # ne compte pas dans count, mais max_id oui
        )
        banque = _creer_banque('bank_flux')
        self.client.force_login(banque)
        resp = self.client.get(reverse('bankDeSang:demandesFlux'))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['count'], 2)
        self.assertEqual(data['max_id'], derniere.id)  # plus grand id, tous états confondus
        self.assertTrue(len(data['recentes']) >= 1)

    def test_flux_refuse_role_non_banque(self):
        autre = User.objects.create_user(username='med_flx2', password='x', role='medical')
        self.client.force_login(autre)
        resp = self.client.get(reverse('bankDeSang:demandesFlux'))
        self.assertEqual(resp.status_code, 302)


class OrdonnanceBanqueTest(TestCase):
    def _demande(self):
        from _auth.models import ServiceMedicaux
        from serviceMedicaux.models import DemandeDeSang
        u = User.objects.create_user(username='med_ordo_b', password='x', role='medical')
        service = ServiceMedicaux.objects.create(
            nom_etablissement='Hôpital Ordo B', type_etablissement='Public', responsable='R',
            adresse='A', email='medordob@example.com', ville='Lomé', code_postal='0', pays='Togo',
            telephone='0', numero_licence='L', numero_enregistrement='E', user=u,
        )
        return DemandeDeSang.objects.create(
            serviceMedicaux=service, type_produit='Sang total', urgence='Immédiate',
            motif='Accident', etat='En attente', groupe_sanguin={service.email: ['A+']},
            nombre_poches={service.email: ['1']},
        )

    def test_banque_telecharge_l_ordonnance(self):
        demande = self._demande()
        banque = _creer_banque('bank_ordo')
        self.client.force_login(banque)
        resp = self.client.get(reverse('bankDeSang:telechargerOrdonnance', args=[demande.id]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'application/pdf')
        self.assertIn('attachment', resp['Content-Disposition'])

    def test_telechargement_refuse_role_non_banque(self):
        demande = self._demande()
        autre = User.objects.create_user(username='med_ordo_x', password='x', role='medical')
        self.client.force_login(autre)
        resp = self.client.get(reverse('bankDeSang:telechargerOrdonnance', args=[demande.id]))
        self.assertEqual(resp.status_code, 302)
