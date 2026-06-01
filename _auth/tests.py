import json
from unittest.mock import patch, MagicMock
from django.test import TestCase
from _auth.geocoding import geocoder_adresse


class GeocoderAdresseTest(TestCase):
    def _fake_response(self, payload):
        fake = MagicMock()
        fake.read.return_value = json.dumps(payload).encode('utf-8')
        fake.__enter__.return_value = fake
        fake.__exit__.return_value = False
        return fake

    @patch('_auth.geocoding.urlopen')
    def test_retourne_coordonnees_quand_ok(self, mock_urlopen):
        mock_urlopen.return_value = self._fake_response({
            'status': 'OK',
            'results': [{'geometry': {'location': {'lat': 6.13, 'lng': 1.22}}}],
        })
        coords = geocoder_adresse('Rue 1', 'Lomé', '00000', 'Togo')
        self.assertEqual(coords, (6.13, 1.22))

    @patch('_auth.geocoding.urlopen')
    def test_retourne_none_quand_zero_result(self, mock_urlopen):
        mock_urlopen.return_value = self._fake_response({
            'status': 'ZERO_RESULTS', 'results': [],
        })
        self.assertIsNone(geocoder_adresse('xxx', '', '', ''))

    @patch('_auth.geocoding.urlopen', side_effect=Exception('réseau coupé'))
    def test_retourne_none_si_exception(self, mock_urlopen):
        self.assertIsNone(geocoder_adresse('Rue 1', 'Lomé', '00000', 'Togo'))


from unittest.mock import patch
from django.contrib.auth import get_user_model
from _auth.models import BanqueDeSang

User = get_user_model()


class BanqueDeSangSaveTest(TestCase):
    def _user(self, username):
        return User.objects.create_user(
            username=username, password='x', role='blood_bank'
        )

    @patch('_auth.models.geocoder_adresse', return_value=(6.13, 1.22))
    def test_save_remplit_coordonnees(self, mock_geo):
        banque = BanqueDeSang.objects.create(
            nom_etablissement='Banque A', responsable='R', adresse='Rue 1',
            ville='Lomé', code_postal='00000', pays='Togo', telephone='90000000',
            user=self._user('b1'),
        )
        self.assertEqual(banque.latitude, 6.13)
        self.assertEqual(banque.longitude, 1.22)
        mock_geo.assert_called_once()

    @patch('_auth.models.geocoder_adresse', return_value=None)
    def test_save_sans_geocodage_reste_none(self, mock_geo):
        banque = BanqueDeSang.objects.create(
            nom_etablissement='Banque B', responsable='R', adresse='Rue 2',
            ville='Lomé', code_postal='00000', pays='Togo', telephone='90000001',
            user=self._user('b2'),
        )
        self.assertIsNone(banque.latitude)
        self.assertIsNone(banque.longitude)

    @patch('_auth.models.geocoder_adresse', return_value=(6.13, 1.22))
    def test_save_ne_regeocode_pas_si_coords_presentes(self, mock_geo):
        banque = BanqueDeSang.objects.create(
            nom_etablissement='Banque C', responsable='R', adresse='Rue 3',
            ville='Lomé', code_postal='00000', pays='Togo', telephone='90000002',
            user=self._user('b3'),
        )
        mock_geo.reset_mock()
        banque.telephone = '90000099'  # adresse inchangée
        banque.save()
        mock_geo.assert_not_called()
