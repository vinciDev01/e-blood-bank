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
