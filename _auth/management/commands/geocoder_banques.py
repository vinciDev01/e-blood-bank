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
