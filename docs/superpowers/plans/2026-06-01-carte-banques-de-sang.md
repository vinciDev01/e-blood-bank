# Carte des banques de sang — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Afficher les banques de sang géocodées sur une carte Google Maps dans le tableau de bord du service médical.

**Architecture:** On ajoute `latitude`/`longitude` à `BanqueDeSang`, remplis par géocodage de l'adresse au `save()` (Geocoding API via `urllib`, sans nouvelle dépendance). Une vue `carteBanques` réservée au rôle `medical` sérialise les banques géocodées en JSON et les affiche via la Maps JavaScript API. Une commande de management géocode les banques déjà en base.

**Tech Stack:** Django 4.2, MySQL, Google Maps (Geocoding API + Maps JavaScript API), `urllib` (stdlib), templates Django.

---

## File Structure

- `eBloodBank/info.py` — ajout de `GOOGLE_MAPS_API_KEY` (sensible).
- `_auth/geocoding.py` *(nouveau)* — `geocoder_adresse()`, appel Geocoding API.
- `_auth/models.py` — champs `latitude`/`longitude` + `save()` surchargé sur `BanqueDeSang`.
- `_auth/migrations/000X_banquedesang_latitude_longitude.py` *(généré)*.
- `_auth/management/commands/geocoder_banques.py` *(nouveau)* — backfill.
- `_auth/tests.py` — tests géocodage + save.
- `serviceMedicaux/views.py` — vue `carteBanques`.
- `serviceMedicaux/urls.py` — route `carteBanques`.
- `serviceMedicaux/tests.py` — test de la vue.
- `frontend/templates/frontend/serviceMedicaux/carte_banques_de_sang.html` *(nouveau)*.
- `frontend/templates/frontend/serviceMedicaux/base.html` — lien sidebar.

---

## Task 1: Configurer la clé API Google Maps

**Files:**
- Modify: `eBloodBank/info.py`

> Note : `eBloodBank/settings.py` fait déjà `from .info import *`, donc toute variable
> définie dans `info.py` devient un réglage Django. Aucune modification de `settings.py`.

- [ ] **Step 1: Ajouter la clé dans `info.py`**

Ajouter à la fin de `eBloodBank/info.py` :

```python

# Clé Google Maps (Geocoding API + Maps JavaScript API). Traiter comme sensible.
GOOGLE_MAPS_API_KEY = 'COLLER_LA_CLE_ICI'
```

> L'utilisateur collera sa vraie clé à la place de `COLLER_LA_CLE_ICI`.

- [ ] **Step 2: Vérifier que Django lit le réglage**

Run: `python manage.py shell -c "from django.conf import settings; print(bool(settings.GOOGLE_MAPS_API_KEY))"`
Expected: affiche `True`

- [ ] **Step 3: Commit**

```bash
git add eBloodBank/info.py
git commit -m "feat: ajout du réglage GOOGLE_MAPS_API_KEY"
```

---

## Task 2: Module de géocodage

**Files:**
- Create: `_auth/geocoding.py`
- Test: `_auth/tests.py`

- [ ] **Step 1: Écrire le test qui échoue**

Remplacer le contenu de `_auth/tests.py` par :

```python
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
```

- [ ] **Step 2: Lancer le test pour vérifier l'échec**

Run: `python manage.py test _auth.tests.GeocoderAdresseTest -v 2`
Expected: FAIL avec `ModuleNotFoundError` / `ImportError: cannot import name 'geocoder_adresse'`

- [ ] **Step 3: Implémenter `_auth/geocoding.py`**

```python
"""Géocodage d'adresses via la Google Geocoding API (sans dépendance externe)."""
import json
from urllib.parse import urlencode
from urllib.request import urlopen

from django.conf import settings

GEOCODE_URL = 'https://maps.googleapis.com/maps/api/geocode/json'


def geocoder_adresse(adresse, ville, code_postal, pays):
    """Retourne (lat, lng) pour l'adresse donnée, ou None si échec.

    Ne lève jamais d'exception : toute erreur (réseau, clé absente,
    statut non OK) renvoie None pour ne pas bloquer un enregistrement.
    """
    cle = getattr(settings, 'GOOGLE_MAPS_API_KEY', '')
    if not cle:
        return None

    adresse_complete = ', '.join(
        p for p in [adresse, ville, code_postal, pays] if p
    )
    if not adresse_complete:
        return None

    params = urlencode({'address': adresse_complete, 'key': cle})
    try:
        with urlopen(f'{GEOCODE_URL}?{params}', timeout=10) as reponse:
            donnees = json.loads(reponse.read().decode('utf-8'))
    except Exception:
        return None

    if donnees.get('status') != 'OK' or not donnees.get('results'):
        return None

    loc = donnees['results'][0]['geometry']['location']
    return (loc['lat'], loc['lng'])
```

- [ ] **Step 4: Lancer le test pour vérifier le succès**

Run: `python manage.py test _auth.tests.GeocoderAdresseTest -v 2`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add _auth/geocoding.py _auth/tests.py
git commit -m "feat: module de géocodage d'adresses Google"
```

---

## Task 3: Champs lat/long + save() géocodé sur BanqueDeSang

**Files:**
- Modify: `_auth/models.py` (classe `BanqueDeSang`, ~lignes 155-175)
- Test: `_auth/tests.py`

- [ ] **Step 1: Écrire le test qui échoue**

Ajouter à la fin de `_auth/tests.py` :

```python
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
```

- [ ] **Step 2: Lancer le test pour vérifier l'échec**

Run: `python manage.py test _auth.tests.BanqueDeSangSaveTest -v 2`
Expected: FAIL — `latitude` n'existe pas (`AttributeError` / `FieldError`)

- [ ] **Step 3: Ajouter l'import en haut de `_auth/models.py`**

Après la ligne `from django.utils import timezone` (ligne 4), ajouter :

```python
from _auth.geocoding import geocoder_adresse
```

- [ ] **Step 4: Ajouter les champs et surcharger `save()` dans `BanqueDeSang`**

Dans la classe `BanqueDeSang`, juste après le champ `profil` (ligne ~163) ajouter :

```python
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
```

Et juste avant `def __str__(self):` ajouter la méthode `save()` :

```python
    def _adresse_complete(self):
        return f'{self.adresse}|{self.ville}|{self.code_postal}|{self.pays}'

    def save(self, *args, **kwargs):
        adresse_changee = True
        if self.pk:
            ancienne = BanqueDeSang.objects.filter(pk=self.pk).first()
            if ancienne:
                adresse_changee = ancienne._adresse_complete() != self._adresse_complete()
        besoin_geocodage = adresse_changee or self.latitude is None or self.longitude is None
        if besoin_geocodage:
            coords = geocoder_adresse(self.adresse, self.ville, self.code_postal, self.pays)
            if coords:
                self.latitude, self.longitude = coords
        super().save(*args, **kwargs)
```

- [ ] **Step 5: Générer et appliquer la migration**

Run: `python manage.py makemigrations _auth`
Expected: crée `_auth/migrations/000X_banquedesang_latitude_longitude.py`

Run: `python manage.py migrate`
Expected: applique la migration sans erreur

- [ ] **Step 6: Lancer les tests pour vérifier le succès**

Run: `python manage.py test _auth.tests.BanqueDeSangSaveTest -v 2`
Expected: PASS (3 tests)

- [ ] **Step 7: Commit**

```bash
git add _auth/models.py _auth/migrations/ _auth/tests.py
git commit -m "feat: coordonnées géocodées au save sur BanqueDeSang"
```

---

## Task 4: Commande de backfill `geocoder_banques`

**Files:**
- Create: `_auth/management/__init__.py`
- Create: `_auth/management/commands/__init__.py`
- Create: `_auth/management/commands/geocoder_banques.py`
- Test: `_auth/tests.py`

- [ ] **Step 1: Écrire le test qui échoue**

Ajouter à la fin de `_auth/tests.py` :

```python
from io import StringIO
from django.core.management import call_command


class GeocoderBanquesCommandTest(TestCase):
    @patch('_auth.models.geocoder_adresse', return_value=None)
    def test_commande_geocode_banques_sans_coords(self, mock_save_geo):
        # Créée sans coords (géocodage save renvoie None)
        banque = BanqueDeSang.objects.create(
            nom_etablissement='Banque D', responsable='R', adresse='Rue 4',
            ville='Lomé', code_postal='00000', pays='Togo', telephone='90000003',
            user=User.objects.create_user(username='b4', password='x', role='blood_bank'),
        )
        self.assertIsNone(banque.latitude)

        with patch('_auth.management.commands.geocoder_banques.geocoder_adresse',
                   return_value=(6.13, 1.22)):
            out = StringIO()
            call_command('geocoder_banques', stdout=out)

        banque.refresh_from_db()
        self.assertEqual(banque.latitude, 6.13)
        self.assertEqual(banque.longitude, 1.22)
```

- [ ] **Step 2: Lancer le test pour vérifier l'échec**

Run: `python manage.py test _auth.tests.GeocoderBanquesCommandTest -v 2`
Expected: FAIL — `CommandError: Unknown command: 'geocoder_banques'`

- [ ] **Step 3: Créer les packages de management**

Créer `_auth/management/__init__.py` (vide) et `_auth/management/commands/__init__.py` (vide).

- [ ] **Step 4: Implémenter la commande**

Créer `_auth/management/commands/geocoder_banques.py` :

```python
from django.core.management.base import BaseCommand

from _auth.models import BanqueDeSang
from _auth.geocoding import geocoder_adresse


class Command(BaseCommand):
    help = "Géocode les banques de sang sans coordonnées."

    def handle(self, *args, **options):
        a_traiter = BanqueDeSang.objects.filter(latitude__isnull=True) | \
            BanqueDeSang.objects.filter(longitude__isnull=True)
        a_traiter = a_traiter.distinct()

        geocodees, echecs = 0, 0
        for banque in a_traiter:
            coords = geocoder_adresse(
                banque.adresse, banque.ville, banque.code_postal, banque.pays
            )
            if coords:
                banque.latitude, banque.longitude = coords
                # update_fields évite de redéclencher le géocodage du save()
                banque.save(update_fields=['latitude', 'longitude'])
                geocodees += 1
                self.stdout.write(self.style.SUCCESS(
                    f'OK  {banque.nom_etablissement} -> {coords}'
                ))
            else:
                echecs += 1
                self.stdout.write(self.style.WARNING(
                    f'ÉCHEC  {banque.nom_etablissement}'
                ))
        self.stdout.write(f'Terminé : {geocodees} géocodées, {echecs} échecs.')
```

> Note : `save(update_fields=[...])` saute la branche de géocodage du `save()` car
> on passe des coordonnées déjà calculées ; et même si elle s'exécutait, `latitude`
> serait non-nul donc `besoin_geocodage` resterait vrai uniquement si l'adresse a
> changé — ici elle n'a pas changé. Comportement cohérent.

- [ ] **Step 5: Lancer le test pour vérifier le succès**

Run: `python manage.py test _auth.tests.GeocoderBanquesCommandTest -v 2`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add _auth/management/
git commit -m "feat: commande geocoder_banques pour backfill des coordonnées"
```

---

## Task 5: Vue et URL `carteBanques`

**Files:**
- Modify: `serviceMedicaux/views.py`
- Modify: `serviceMedicaux/urls.py`
- Test: `serviceMedicaux/tests.py`

- [ ] **Step 1: Écrire le test qui échoue**

Remplacer le contenu de `serviceMedicaux/tests.py` par :

```python
import json
from unittest.mock import patch
from django.test import TestCase, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model
from _auth.models import BanqueDeSang

User = get_user_model()


@override_settings(GOOGLE_MAPS_API_KEY='TEST_KEY')
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
        self.assertEqual(resp.context['google_maps_api_key'], 'TEST_KEY')

    def test_seules_les_banques_geocodees_sont_envoyees(self):
        self.client.force_login(self.medical)
        resp = self.client.get(reverse('serviceMedicaux:carteBanques'))
        banques = json.loads(resp.context['banques_json'])
        noms = [b['nom'] for b in banques]
        self.assertIn('Banque Visible', noms)
        self.assertNotIn('Banque Cachee', noms)

    def test_role_non_medical_est_redirige(self):
        autre = User.objects.create_user(username='autre', password='x', role='donor')
        self.client.force_login(autre)
        resp = self.client.get(reverse('serviceMedicaux:carteBanques'))
        self.assertEqual(resp.status_code, 302)
```

- [ ] **Step 2: Lancer le test pour vérifier l'échec**

Run: `python manage.py test serviceMedicaux.tests.CarteBanquesViewTest -v 2`
Expected: FAIL — `NoReverseMatch: 'carteBanques' not found`

- [ ] **Step 3: Ajouter la vue dans `serviceMedicaux/views.py`**

S'assurer que ces imports sont présents en haut du fichier (ajouter ceux qui manquent) :

```python
import json
from django.conf import settings
from _auth.models import BanqueDeSang
```

> `from _auth.models import ServiceMedicaux` existe déjà ; on étend l'import OU on
> ajoute une ligne séparée `from _auth.models import BanqueDeSang`.

Ajouter la vue à la fin du fichier :

```python
@login_required
@check_role('medical')
def carteBanques(request):
    banques = BanqueDeSang.objects.filter(
        latitude__isnull=False, longitude__isnull=False
    )
    donnees = [
        {
            'nom': b.nom_etablissement,
            'adresse': b.adresse,
            'ville': b.ville,
            'telephone': b.telephone,
            'lat': b.latitude,
            'lng': b.longitude,
        }
        for b in banques
    ]
    context = {
        'banques_json': json.dumps(donnees),
        'google_maps_api_key': settings.GOOGLE_MAPS_API_KEY,
    }
    return render(request, 'frontend/serviceMedicaux/carte_banques_de_sang.html', context)
```

- [ ] **Step 4: Ajouter la route dans `serviceMedicaux/urls.py`**

Dans `urlpatterns`, après la ligne `recevoir_poches`, ajouter :

```python
    path('carteBanques/', views.carteBanques, name='carteBanques'),
```

- [ ] **Step 5: Lancer les tests**

> Le template n'existe pas encore : `test_role_medical_voit_la_carte` et
> `test_seules_les_banques_geocodees_sont_envoyees` échoueront sur
> `TemplateDoesNotExist`. C'est attendu — ils passeront après la Task 6.
> `test_role_non_medical_est_redirige` doit déjà PASSER (redirection avant rendu).

Run: `python manage.py test serviceMedicaux.tests.CarteBanquesViewTest.test_role_non_medical_est_redirige -v 2`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add serviceMedicaux/views.py serviceMedicaux/urls.py serviceMedicaux/tests.py
git commit -m "feat: vue et URL carteBanques (rôle medical)"
```

---

## Task 6: Template de la carte

**Files:**
- Create: `frontend/templates/frontend/serviceMedicaux/carte_banques_de_sang.html`

- [ ] **Step 1: Créer le template**

```html
{% extends 'frontend/serviceMedicaux/base.html' %}
{% block content %}
<div style="padding:16px;">
    <h1 style="font-size:20px;font-weight:600;margin-bottom:12px;">Carte des banques de sang</h1>
    <div id="carte-banques" style="width:100%;height:70vh;border-radius:12px;"></div>
    <p id="carte-message" style="display:none;color:#6b7280;margin-top:12px;">
        Aucune banque de sang localisée pour le moment.
    </p>
</div>

{{ banques_json|json_script:"banques-data" }}

<script>
    function initCarteBanques() {
        const banques = JSON.parse(document.getElementById('banques-data').textContent);
        const conteneur = document.getElementById('carte-banques');

        if (!banques.length) {
            conteneur.style.display = 'none';
            document.getElementById('carte-message').style.display = 'block';
            return;
        }

        const carte = new google.maps.Map(conteneur, { zoom: 6 });
        const bounds = new google.maps.LatLngBounds();
        const infoWindow = new google.maps.InfoWindow();

        banques.forEach(function (b) {
            const position = { lat: b.lat, lng: b.lng };
            const marqueur = new google.maps.Marker({ position: position, map: carte, title: b.nom });
            bounds.extend(position);

            marqueur.addListener('click', function () {
                infoWindow.setContent(
                    '<div style="font-size:13px;max-width:220px;">' +
                    '<strong>' + b.nom + '</strong><br>' +
                    b.adresse + ', ' + b.ville + '<br>' +
                    '<a href="tel:' + b.telephone + '">' + b.telephone + '</a>' +
                    '</div>'
                );
                infoWindow.open(carte, marqueur);
            });
        });

        carte.fitBounds(bounds);
    }
    window.initCarteBanques = initCarteBanques;
</script>
<script async
    src="https://maps.googleapis.com/maps/api/js?key={{ google_maps_api_key }}&callback=initCarteBanques">
</script>
{% endblock %}
```

> Vérifier que `serviceMedicaux/base.html` définit bien un `{% block content %}`.
> Si le bloc porte un autre nom, adapter `{% block content %}` en conséquence.

- [ ] **Step 2: Vérifier le nom du bloc dans base.html**

Run: `grep -n "block content\|block " frontend/templates/frontend/serviceMedicaux/base.html`
Expected: confirme l'existence d'un bloc englobant le contenu (ex. `{% block content %}`). Adapter le template si le nom diffère.

- [ ] **Step 3: Lancer les tests de la vue (template présent)**

Run: `python manage.py test serviceMedicaux.tests.CarteBanquesViewTest -v 2`
Expected: PASS (3 tests)

- [ ] **Step 4: Commit**

```bash
git add frontend/templates/frontend/serviceMedicaux/carte_banques_de_sang.html
git commit -m "feat: template carte des banques de sang"
```

---

## Task 7: Lien dans la sidebar

**Files:**
- Modify: `frontend/templates/frontend/serviceMedicaux/base.html` (groupe « Général », ~ligne 350)

- [ ] **Step 1: Ajouter le lien**

Dans le groupe `Général` (`<div class="ebb-nav-group">` contenant le label « Général »),
juste après le `</a>` du lien « Tableau de bord » (ligne ~350) et avant la fermeture
`</div>` du groupe, ajouter :

```html
                    <a href="{% url 'serviceMedicaux:carteBanques' %}"
                        class="ebb-nav-item {% if url_name == 'carteBanques' %}active{% endif %}">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round"
                            stroke-linejoin="round">
                            <path d="M9 20l-5.447-2.724A1 1 0 0 1 3 16.382V5.618a1 1 0 0 1 1.447-.894L9 7m0 13l6-3m-6 3V7m6 10l5.447 2.724A1 1 0 0 0 21 18.382V7.618a1 1 0 0 0-1.447-.894L15 4m0 13V4m0 0L9 7" />
                        </svg>
                        <span>Carte des banques</span>
                    </a>
```

> `url_name` est déjà disponible via `{% with url_name=request.resolver_match.url_name %}`
> ouvert au début de `<nav class="ebb-nav">`.

- [ ] **Step 2: Vérification manuelle**

Run: `python manage.py runserver` puis se connecter en tant que service médical et
ouvrir `/serviceMedicaux/carteBanques/`.
Expected: le lien « Carte des banques » apparaît dans la sidebar (état actif), la carte
s'affiche avec un marqueur par banque géocodée ; un clic montre nom/adresse/téléphone.

> Prérequis : avoir collé une vraie clé API (Task 1) et exécuté
> `python manage.py geocoder_banques` pour les banques existantes.

- [ ] **Step 3: Commit**

```bash
git add frontend/templates/frontend/serviceMedicaux/base.html
git commit -m "feat: lien Carte des banques dans la sidebar service médical"
```

---

## Validation finale

- [ ] `python manage.py test _auth serviceMedicaux` → tous les tests passent.
- [ ] La création d'une banque avec adresse renseigne ses coordonnées.
- [ ] `python manage.py geocoder_banques` géocode les banques existantes.
- [ ] La carte affiche les banques géocodées ; les non géocodées sont absentes sans erreur.
- [ ] Une banque sans coordonnées n'apparaît pas et ne provoque aucune erreur.
