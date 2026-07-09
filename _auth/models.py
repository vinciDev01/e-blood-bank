from django.db import models
from django.core.exceptions import ObjectDoesNotExist
from datetime import date, timedelta
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.utils import timezone
from _auth.geocoding import geocoder_adresse
import os
import random
import string

# Create your models here.
def renomer_image(instance, filename):
    model_name = instance.__class__.__name__.lower()
    upload_to = f'images/{model_name}/'
    ext = filename.split('.')[-1]
    # Utiliser nom/prenom si disponibles, sinon le username du user lie
    if hasattr(instance, 'nom') and hasattr(instance, 'prenom'):
        nom_fichier = f'{instance.nom}_{instance.prenom}'
    elif hasattr(instance, 'nom_etablissement'):
        nom_fichier = instance.nom_etablissement
    elif hasattr(instance, 'user'):
        nom_fichier = instance.user.username
    else:
        nom_fichier = f'{model_name}_{instance.pk}'
    filename = f'photo_profile/{nom_fichier}.{ext}'
    return os.path.join(upload_to, filename)

def numero_de_donneur():
    count = Donneur.objects.count() + 1
    return f"{date.today().year}ebb{count:04d}"



class CustomUser(AbstractUser):

    ROLE_CHOICES = (
        ('generic', 'Generic User'),
        ('medical', 'Medical Service User'),
        ('clinic', 'Clinic User'),
        ('donor', 'Donor User'),
        ('blood_bank', 'Blood Bank User'),
        ('admin', 'Admin User'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='generic')
    

    groups = models.ManyToManyField(
        Group,
        related_name='customuser_set',
        blank=True,
        help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.',
        verbose_name='groups',
    )
    user_permissions = models.ManyToManyField(
        Permission,
        related_name='customuser_set',
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions',
    )

    def __str__(self):
        return self.username

    @property
    def nom_affichage(self):
        """Nom lisible de l'utilisateur connecté, selon son profil lié.

        Donneur / Utilisateur -> « Nom Prénom » ; Service médical / Banque de sang
        -> nom de l'établissement ; sinon nom complet ou, à défaut, le username.
        """
        try:
            return f"{self.donneur.nom} {self.donneur.prenom}".strip()
        except ObjectDoesNotExist:
            pass
        try:
            return f"{self.utilisateur.nom} {self.utilisateur.prenom}".strip()
        except ObjectDoesNotExist:
            pass
        try:
            return self.service_medical.nom_etablissement
        except ObjectDoesNotExist:
            pass
        try:
            return self.banque_de_sang.nom_etablissement
        except ObjectDoesNotExist:
            pass
        return self.get_full_name() or self.username

    # def set_profil(self, image):
    #     self.profil = image
    #     self.save()

class Utilisateur(models.Model):
    nom = models.CharField(max_length=200)
    prenom = models.CharField(max_length=200)
    email = models.EmailField(unique=True, null=True)
    profil = models.ImageField(upload_to=renomer_image, default='images/default.jpg')
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='utilisateur')

class ServiceMedicaux(models.Model):
    nom_etablissement = models.CharField(max_length=200)
    type_etablissement = models.CharField(max_length=200)
    responsable = models.CharField(max_length=200)
    adresse = models.CharField(max_length=200)
    email = models.EmailField(unique=True)
    ville = models.CharField(max_length=100)
    code_postal = models.CharField(max_length=10)
    pays = models.CharField(max_length=100)
    telephone = models.CharField(max_length=20)
    numero_licence = models.CharField(max_length=20)
    numero_enregistrement = models.CharField(max_length=20)
    certificat_enregistrement = models.FileField(upload_to='servicesMedicaux/certificats/')
    profil = models.ImageField(upload_to=renomer_image, default='images/default.jpg')

    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='service_medical')

    groups = models.ManyToManyField(Group, related_name="services_medicaux")
    user_permissions = models.ManyToManyField(Permission, related_name="services_medicaux_permissions")

    def __str__(self):
        return self.nom_etablissement
    
    class Meta:
        verbose_name = "Service Médical"
        verbose_name_plural = "Services Médicaux"
        ordering = ['-id']


class Donneur(models.Model):
    nom = models.CharField(max_length=200)
    prenom = models.CharField(max_length=200)
    date_naissance = models.DateField()
    sexe = models.CharField(max_length=10)
    groupe_sanguin_choices = [
        ('A+', 'A+'),
        ('A-', 'A-'),
        ('B+', 'B+'),
        ('B-', 'B-'),
        ('AB+', 'AB+'),
        ('AB-', 'AB-'),
        ('O+', 'O+'),
        ('O-', 'O-'),
    ]
    groupe_sanguin = models.CharField(max_length=3, choices=groupe_sanguin_choices)
    #rh = models.CharField(max_length=10)
    adresse = models.CharField(max_length=200)
    ville = models.CharField(max_length=100)
    code_postal = models.CharField(max_length=10)
    pays = models.CharField(max_length=100)
    telephone = models.CharField(max_length=20)
    profil = models.ImageField(upload_to=renomer_image, default='images/default.jpg')
    numero_de_donneur = models.CharField(max_length=20, default=numero_de_donneur)

    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='donneur')

    groups = models.ManyToManyField(Group, related_name="donneurs")
    user_permissions = models.ManyToManyField(Permission, related_name="donneurs_permissions")

    def __str__(self):
        return self.nom + ' ' + self.prenom
    
    @property
    def age(self):
        return date.today().year - self.date_naissance.year - (
            (date.today().month, date.today().day) < (self.date_naissance.month, self.date_naissance.day)
        )

    # @property
    # def peut_donner(self):
    #     if not self.date_dernier_don:
    #         return True
    #     temps_depuis_dernier_don = date.today() - self.date_dernier_don
    #     return temps_depuis_dernier_don.days >= 90



    class Meta:
        verbose_name = "Donneur"
        verbose_name_plural = "Donneurs"
        ordering = ['-id']


class BanqueDeSang(models.Model):
    nom_etablissement = models.CharField(max_length=200)
    responsable = models.CharField(max_length=200)
    adresse = models.CharField(max_length=200)
    ville = models.CharField(max_length=100)
    code_postal = models.CharField(max_length=10)
    pays = models.CharField(max_length=100)
    telephone = models.CharField(max_length=20)
    profil = models.ImageField(upload_to=renomer_image, default='images/default.jpg')
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='banque_de_sang')

    groups = models.ManyToManyField(Group, related_name="banques_de_sang")
    user_permissions = models.ManyToManyField(Permission, related_name="banques_de_sang_permissions")

    @classmethod
    def donnees_carte(cls, groupe=None):
        """Banques géocodées, sérialisées pour la carte (liste de dicts).

        Chaque banque porte `dispo` = nombre de poches disponibles (est_disponible).
        Si `groupe` (un groupe sanguin valide) est fourni, on ne renvoie que les
        banques ayant au moins une poche disponible de ce groupe, et chaque dict
        porte alors `dispo_groupe` = nombre de poches disponibles de ce groupe.
        """
        from django.db.models import Count, Q

        qs = cls.objects.filter(latitude__isnull=False, longitude__isnull=False).annotate(
            dispo=Count('pochedesang', filter=Q(pochedesang__est_disponible=True)),
        )
        if groupe:
            qs = qs.annotate(
                dispo_groupe=Count('pochedesang', filter=Q(
                    pochedesang__est_disponible=True, pochedesang__groupe_sanguin=groupe,
                )),
            ).filter(dispo_groupe__gt=0)

        données = []
        for b in qs:
            d = {
                'nom': b.nom_etablissement,
                'adresse': b.adresse,
                'ville': b.ville,
                'telephone': b.telephone,
                'lat': b.latitude,
                'lng': b.longitude,
                'dispo': b.dispo,
            }
            if groupe:
                d['dispo_groupe'] = b.dispo_groupe
            données.append(d)
        return données

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

    def __str__(self):
        return self.nom_etablissement

    class Meta:
        verbose_name = "Banque de Sang"
        verbose_name_plural = "Banques de Sang"
        ordering = ['-id']


class OTPCode(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='otp_codes')
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(minutes=5)
        super().save(*args, **kwargs)

    def is_valid(self):
        return not self.is_used and timezone.now() < self.expires_at

    @staticmethod
    def generate_code():
        return ''.join(random.choices(string.digits, k=6))

    class Meta:
        verbose_name = "Code OTP"
        verbose_name_plural = "Codes OTP"
        ordering = ['-created_at']
