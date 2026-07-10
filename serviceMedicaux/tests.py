from datetime import date
from unittest.mock import patch
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from _auth.models import BanqueDeSang, ServiceMedicaux
from serviceMedicaux.models import DemandeDeSang, Patient

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

    def test_carte_a_le_filtre_groupe(self):
        self.client.force_login(self.medical)
        resp = self.client.get(reverse('serviceMedicaux:carteBanques'))
        self.assertContains(resp, 'name="groupe"')
        self.assertContains(resp, 'Groupe sanguin recherché')

    def test_carte_filtre_par_groupe(self):
        from datetime import timedelta
        from bankDeSang.models import PocheDeSang
        banque = BanqueDeSang.objects.get(nom_etablissement='Banque Visible')
        PocheDeSang.objects.create(
            matricule='CB-O', type_produit='Sang total', groupe_sanguin='O-',
            date_expiration=date.today() + timedelta(days=42), est_disponible=True,
            bank_de_sang=banque,
        )
        self.client.force_login(self.medical)
        resp = self.client.get(reverse('serviceMedicaux:carteBanques'), {'groupe': 'O-'})
        noms = [b['nom'] for b in resp.context['banques']]
        self.assertEqual(noms, ['Banque Visible'])
        self.assertEqual(resp.context['groupe_selectionne'], 'O-')


class SuiviDemandesTest(TestCase):
    def _service_avec_demande(self):
        u = User.objects.create_user(username='svc_np', password='x', role='medical')
        service = ServiceMedicaux.objects.create(
            nom_etablissement='Hôpital Test', type_etablissement='Public', responsable='R',
            adresse='A', email='svc_np@example.com', ville='Lomé', code_postal='0', pays='Togo',
            telephone='0', numero_licence='L', numero_enregistrement='E', user=u,
        )
        # Patient SANS utilisateur lié (cas du formulaire médical et du seed)
        patient = Patient.objects.create(
            nom_complet='Patient Démo', date_de_naissance=date(2000, 1, 1), proche='',
            groupe_sanguin='A+', telephone_proche='',
        )
        demande = DemandeDeSang.objects.create(
            serviceMedicaux=service, patient=patient,
            groupe_sanguin={service.email: ['A+']}, type_produit='Sang total',
            nombre_poches={service.email: ['2']}, urgence='24 heures', motif='Chirurgie',
            etat='En attente', etat_groupes={'A+': 'En attente'},
        )
        return u, demande

    def test_nbr_poches_patient_ne_crashe_pas_sans_utilisateur(self):
        _, demande = self._service_avec_demande()
        self.assertEqual(demande.nbr_poches_patient(), '2')

    def test_page_suivi_demandes_rend_200(self):
        u, _ = self._service_avec_demande()
        self.client.force_login(u)
        resp = self.client.get(reverse('serviceMedicaux:listeDemandeDeSang'))
        self.assertEqual(resp.status_code, 200)


class DemandesBadgeContextTest(TestCase):
    def _service(self, username, email):
        u = User.objects.create_user(username=username, password='x', role='medical')
        s = ServiceMedicaux.objects.create(
            nom_etablissement='Hôpital', type_etablissement='Public', responsable='R',
            adresse='A', email=email, ville='Lomé', code_postal='0', pays='Togo',
            telephone='0', numero_licence='L', numero_enregistrement='E', user=u,
        )
        return u, s

    def _demande(self, service, etat='En attente'):
        return DemandeDeSang.objects.create(
            serviceMedicaux=service, type_produit='Sang total', urgence='Immédiate',
            motif='Accident', etat=etat, groupe_sanguin={service.email: ['A+']},
            nombre_poches={service.email: ['2']},
        )

    def test_badge_banque_compte_toutes_les_demandes_en_attente(self):
        u_med, service = self._service('med_b', 'medb@example.com')
        self._demande(service)
        self._demande(service)
        self._demande(service, etat='Approuvee')  # ne compte pas

        banque = User.objects.create_user(username='bank_b', password='x', role='blood_bank')
        self.client.force_login(banque)
        resp = self.client.get(reverse('bankDeSang:accueilBankDeSang'))
        self.assertEqual(resp.context['demandes_badge_count'], 2)
        self.assertEqual(resp.context['demandes_badge_url_name'], 'listeDemandesDeSang')

    def test_badge_service_compte_ses_propres_demandes(self):
        u_med, service = self._service('med_s', 'meds@example.com')
        self._demande(service)
        # Demande d'un autre service : ne doit pas compter
        _, autre = self._service('med_x', 'medx@example.com')
        self._demande(autre)

        self.client.force_login(u_med)
        resp = self.client.get(reverse('serviceMedicaux:mesDemandesDeSang'))
        self.assertEqual(resp.context['demandes_badge_count'], 1)
        self.assertEqual(resp.context['demandes_badge_url_name'], 'mesDemandesDeSang')


class MesDemandesFluxTest(TestCase):
    def _service(self, username, email):
        u = User.objects.create_user(username=username, password='x', role='medical')
        s = ServiceMedicaux.objects.create(
            nom_etablissement='Hôpital', type_etablissement='Public', responsable='R',
            adresse='A', email=email, ville='Lomé', code_postal='0', pays='Togo',
            telephone='0', numero_licence='L', numero_enregistrement='E', user=u,
        )
        return u, s

    def test_flux_isole_les_demandes_du_service(self):
        u, service = self._service('med_f', 'medf@example.com')
        d1 = DemandeDeSang.objects.create(
            serviceMedicaux=service, type_produit='Sang total', urgence='Immédiate',
            motif='Accident', etat='En attente',
        )
        _, autre = self._service('med_g', 'medg@example.com')
        DemandeDeSang.objects.create(
            serviceMedicaux=autre, type_produit='Sang total', urgence='Immédiate',
            motif='Accident', etat='En attente',
        )
        self.client.force_login(u)
        resp = self.client.get(reverse('serviceMedicaux:mesDemandesFlux'))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['count'], 1)
        ids = [e[0] for e in data['etats']]
        self.assertEqual(ids, [d1.id])

    def test_flux_refuse_role_non_medical(self):
        autre = User.objects.create_user(username='don_f', password='x', role='donor')
        self.client.force_login(autre)
        resp = self.client.get(reverse('serviceMedicaux:mesDemandesFlux'))
        self.assertEqual(resp.status_code, 302)


class MessagesAffichesTest(TestCase):
    """Les messages Django (success/error) doivent s'afficher sur les pages qui
    étendent les gabarits de base (régression : la base ne les rendait pas)."""

    def test_message_erreur_saffiche_apres_action(self):
        u = User.objects.create_user(username='msg_med', password='x', role='medical')
        ServiceMedicaux.objects.create(
            nom_etablissement='Hôpital Msg', type_etablissement='Public', responsable='R',
            adresse='A', email='msgmed@example.com', ville='Lomé', code_postal='0', pays='Togo',
            telephone='0', numero_licence='L', numero_enregistrement='E', user=u,
        )
        self.client.force_login(u)
        # POST incomplet → messages.error puis redirection vers le formulaire
        resp = self.client.post(reverse('serviceMedicaux:faireDemandeDeSang'), {}, follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Veuillez remplir tous les champs obligatoires')


class DetailDemandeTest(TestCase):
    def _service(self, username, email):
        u = User.objects.create_user(username=username, password='x', role='medical')
        s = ServiceMedicaux.objects.create(
            nom_etablissement='Hôpital Détail', type_etablissement='Public', responsable='R',
            adresse='Rue 1', email=email, ville='Lomé', code_postal='0', pays='Togo',
            telephone='90000000', numero_licence='L', numero_enregistrement='E', user=u,
        )
        return u, s

    def _demande(self, service):
        return DemandeDeSang.objects.create(
            serviceMedicaux=service, type_produit='Sang total', urgence='Immédiate',
            motif='Accident', etat='En attente', groupe_sanguin={service.email: ['O+']},
            nombre_poches={service.email: ['2']}, etat_groupes={'O+': 'En attente'},
        )

    def test_details_groupes_mapping(self):
        _, service = self._service('det_a', 'deta@example.com')
        demande = self._demande(service)
        lignes = demande.details_groupes()
        self.assertEqual(lignes, [{'groupe': 'O+', 'quantite': '2', 'etat': 'En attente'}])

    def test_page_detail_proprietaire(self):
        u, service = self._service('det_b', 'detb@example.com')
        demande = self._demande(service)
        self.client.force_login(u)
        resp = self.client.get(reverse('serviceMedicaux:detailDemande', args=[demande.id]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Détail de la demande')
        self.assertContains(resp, 'Hôpital Détail')

    def test_detail_refuse_demande_d_un_autre_service(self):
        u1, _ = self._service('det_c', 'detc@example.com')
        _, s2 = self._service('det_d', 'detd@example.com')
        demande_autre = self._demande(s2)
        self.client.force_login(u1)
        resp = self.client.get(reverse('serviceMedicaux:detailDemande', args=[demande_autre.id]))
        self.assertEqual(resp.status_code, 404)

    def test_detail_refuse_role_non_medical(self):
        _, service = self._service('det_e', 'dete@example.com')
        demande = self._demande(service)
        donor = User.objects.create_user(username='don_det', password='x', role='donor')
        self.client.force_login(donor)
        resp = self.client.get(reverse('serviceMedicaux:detailDemande', args=[demande.id]))
        self.assertEqual(resp.status_code, 302)


class OrdonnancePdfTest(TestCase):
    def _service(self, username, email):
        u = User.objects.create_user(username=username, password='x', role='medical')
        s = ServiceMedicaux.objects.create(
            nom_etablissement='Hôpital Ordo', type_etablissement='Public', responsable='Dr X',
            adresse='Rue 1', email=email, ville='Lomé', code_postal='0', pays='Togo',
            telephone='90000000', numero_licence='L', numero_enregistrement='E', user=u,
        )
        return u, s

    def _demande(self, service):
        patient = Patient.objects.create(
            nom_complet='Jean Test', date_de_naissance=date(1990, 5, 1), proche='',
            groupe_sanguin='O+', telephone_proche='',
        )
        return DemandeDeSang.objects.create(
            serviceMedicaux=service, patient=patient, type_produit='Sang total',
            urgence='Immédiate', motif='Accident', etat='En attente',
            groupe_sanguin={service.email: ['O+']}, nombre_poches={service.email: ['2']},
        )

    def test_construire_pdf_renvoie_un_pdf(self):
        from serviceMedicaux.ordonnance import construire_pdf
        _, service = self._service('ordo_a', 'ordoa@example.com')
        demande = self._demande(service)
        pdf = construire_pdf(demande)
        self.assertTrue(pdf.startswith(b'%PDF'))
        self.assertGreater(len(pdf), 1000)

    def test_generer_ordonnance_remplit_le_champ(self):
        _, service = self._service('ordo_b', 'ordob@example.com')
        demande = self._demande(service)
        self.assertFalse(bool(demande.ordonnance_pdf))
        demande.generer_ordonnance()
        self.assertTrue(bool(demande.ordonnance_pdf))
        self.assertTrue(demande.ordonnance_pdf.name.endswith('.pdf'))

    def test_reference_format(self):
        _, service = self._service('ordo_r', 'ordor@example.com')
        demande = self._demande(service)
        self.assertEqual(demande.reference(), f"DEM-{demande.id}-{demande.date_demande.year}")

    def test_telechargement_service_proprietaire(self):
        u, service = self._service('ordo_c', 'ordoc@example.com')
        demande = self._demande(service)  # sans ordonnance_pdf → génération paresseuse
        self.client.force_login(u)
        resp = self.client.get(reverse('serviceMedicaux:telechargerOrdonnance', args=[demande.id]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'application/pdf')
        self.assertIn('attachment', resp['Content-Disposition'])

    def test_service_ne_telecharge_pas_la_demande_d_un_autre(self):
        u1, s1 = self._service('ordo_d', 'ordod@example.com')
        _, s2 = self._service('ordo_e', 'ordoe@example.com')
        demande_autre = self._demande(s2)
        self.client.force_login(u1)
        resp = self.client.get(reverse('serviceMedicaux:telechargerOrdonnance', args=[demande_autre.id]))
        self.assertEqual(resp.status_code, 404)

    def test_telechargement_refuse_role_non_medical(self):
        _, service = self._service('ordo_f', 'ordof@example.com')
        demande = self._demande(service)
        donor = User.objects.create_user(username='don_ordo', password='x', role='donor')
        self.client.force_login(donor)
        resp = self.client.get(reverse('serviceMedicaux:telechargerOrdonnance', args=[demande.id]))
        self.assertEqual(resp.status_code, 302)
