from unittest.mock import patch
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from _auth.models import BanqueDeSang, ServiceMedicaux
from serviceMedicaux.models import DemandeDeSang

User = get_user_model()


class DemandeGroupeSanguinTest(TestCase):
    """`groupeSanguin()` / `nombrePoches()` indexent un dict JSON par l'email du
    service. Si cet email change après la création de la demande, la clé ne
    correspond plus : la méthode doit se rabattre sur la donnée plutôt que lever
    un KeyError."""

    def _service(self, email):
        user = User.objects.create_user(username='svc_' + email[:4], password='x', role='medical')
        return ServiceMedicaux.objects.create(
            nom_etablissement='Hôpital', type_etablissement='Public', responsable='R',
            adresse='Rue', email=email, ville='Lomé', code_postal='00000', pays='Togo',
            telephone='90000000', numero_licence='L1', numero_enregistrement='E1', user=user,
        )

    def test_repli_quand_email_du_service_a_change(self):
        service = self._service('nouveau@example.com')
        demande = DemandeDeSang.objects.create(
            serviceMedicaux=service, type_produit='Sang total',
            urgence='Immédiate', motif='Accident',
            groupe_sanguin={'ancien@example.com': ['A+']},
            nombre_poches={'ancien@example.com': [2]},
        )
        # La clé du dict ('ancien@...') ne correspond plus à l'email du service.
        self.assertEqual(demande.groupeSanguin(), ['A+'])
        self.assertEqual(demande.nombrePoches(), [2])

    def test_acces_normal_quand_email_correspond(self):
        service = self._service('match@example.com')
        demande = DemandeDeSang.objects.create(
            serviceMedicaux=service, type_produit='Sang total',
            urgence='Immédiate', motif='Accident',
            groupe_sanguin={'match@example.com': ['O-']},
            nombre_poches={'match@example.com': [3]},
        )
        self.assertEqual(demande.groupeSanguin(), ['O-'])
        self.assertEqual(demande.nombrePoches(), [3])

    def test_dict_vide_renvoie_liste_vide(self):
        service = self._service('vide@example.com')
        demande = DemandeDeSang.objects.create(
            serviceMedicaux=service, type_produit='Sang total',
            urgence='Immédiate', motif='Accident',
        )
        self.assertEqual(demande.groupeSanguin(), [])
        self.assertEqual(demande.nombrePoches(), [])


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

    def test_carte_est_bornee_au_togo(self):
        # La carte est verrouillée sur la boîte englobante du Togo.
        self.client.force_login(self.medical)
        resp = self.client.get(reverse('serviceMedicaux:carteBanques'))
        self.assertContains(resp, 'maxBounds')
        self.assertContains(resp, 'bornesTogo')

    def test_carte_propose_itineraire(self):
        # Le bouton d'itinéraire et l'appel au routage OSRM sont présents.
        self.client.force_login(self.medical)
        resp = self.client.get(reverse('serviceMedicaux:carteBanques'))
        self.assertContains(resp, 'Itinéraire')
        self.assertContains(resp, 'router.project-osrm.org')
