from datetime import timedelta, datetime
from django.db import models
from _auth.models import Donneur, BanqueDeSang, ServiceMedicaux
from datetime import date
import qrcode
import os
from django.conf import settings

# Définition du modèle DonDeSang
def default_date_expiration():
    return date.today() + timedelta(days=42)

# une méthode qui génère un code qr avec les informations d'une poche de sang
def code_qr_poche_de_sang(instance, filename):
    relative_path = os.path.join('QR code', f"{instance.matricule}.png")
    full_path = os.path.join(settings.MEDIA_ROOT, relative_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    return relative_path

class PocheDeSang(models.Model):
    donneur = models.ForeignKey(Donneur, on_delete=models.CASCADE, null=True)
    matricule = models.CharField(max_length=20, unique=True)
    date_de_prelevement = models.DateField(default=date.today)
    type_produit_choices = [
        ('Sang total', 'Sang total'),
        ('Concentré de globules rouges', 'Concentré de globules rouges'),
        ('Plasma', 'Plasma'),
        ('Plaquettes', 'Plaquettes'),
    ]
    type_produit = models.CharField(max_length=30, choices=type_produit_choices)
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
    date_enregistrement = models.DateField(auto_now=True)
    date_expiration = models.DateField()
    code_qr = models.ImageField(upload_to=code_qr_poche_de_sang, null=True, blank=True)
    est_disponible = models.BooleanField(default=True)
    en_transition = models.BooleanField(default=False)
    bank_de_sang = models.ForeignKey(BanqueDeSang, on_delete=models.CASCADE, null=True, blank=True)
    service_medicaux = models.ForeignKey(ServiceMedicaux, on_delete=models.CASCADE, null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.date_expiration:
            self.date_expiration = self.date_de_prelevement + timedelta(days=42)
        super().save(*args, **kwargs)
        if not self.code_qr:
            self.generate_qr_code()

    def generate_qr_code(self):
        qr = qrcode.QRCode(
            version=3,
            error_correction=qrcode.ERROR_CORRECT_L,
            box_size=10,
            border=5,
        )
        qr.add_data(f"Poche {self.matricule}\n{self.type_produit} ({self.groupe_sanguin})\n{self.date_de_prelevement}\n{self.date_expiration}\n{self.donneur}")
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        img_path = code_qr_poche_de_sang(self, 'dummy.png')
        full_path = os.path.join(settings.MEDIA_ROOT, img_path)
        img.save(full_path)
        self.code_qr = img_path
        PocheDeSang.objects.filter(id=self.id).update(code_qr=img_path)

    def jour_restant(self):
        return f"{(self.date_expiration - date.today()).days}"

    class Meta:
        ordering = ['-id']

    def __str__(self):
        return f"Poche {self.matricule} - {self.type_produit} ({self.groupe_sanguin})"



class DonDeSang(models.Model):
    donneur = models.ForeignKey(Donneur, on_delete=models.CASCADE)
    poche_de_sang = models.ForeignKey(PocheDeSang, on_delete=models.CASCADE, null=True, blank=True)
    type_produit = models.CharField(max_length=30, choices=PocheDeSang.type_produit_choices)
    date_don = models.DateField(auto_now_add=True)
    date_expiration = models.DateField(default=default_date_expiration)

    class Meta:
        ordering = ['-id']

    def __str__(self):
        return f"Don de {self.donneur.nom} {self.donneur.prenom} ({self.type_produit} - {self.date_don})"



class StockDeSang(models.Model):
    # poche_de_sang = models.ForeignKey(PocheDeSang, on_delete=models.CASCADE, null=True, blank=True, related_name='stock_bankdesang')
    groupe_sanguin = models.CharField(max_length=3, choices=PocheDeSang.groupe_sanguin_choices, null=True, blank=True)
    nombre_de_poches = models.IntegerField(default=1)
    date_enregistrement = models.DateField(auto_now=True)

    class Meta:
        ordering = ['-id']

    def __str__(self):
        return f"Stock de {self.groupe_sanguin} - {self.nombre_de_poches} poches"

    @classmethod
    def enregistrer_stock(cls, poche, nombre_de_poches):
        try:
            stock = cls.objects.get(groupe_sanguin=poche.groupe_sanguin)
            stock.nombre_de_poches += nombre_de_poches
            stock.save()
        except cls.DoesNotExist:
            cls.objects.create(
                groupe_sanguin=poche.groupe_sanguin,
                nombre_de_poches=nombre_de_poches
            )

    def retirer_stock(self, nombre_de_poches):
        if self.nombre_de_poches >= nombre_de_poches:
            self.nombre_de_poches -= nombre_de_poches
            self.save()
        else:
            raise ValueError("Stock insuffisant")


class HistoriqueStock(models.Model):
    ACTION_CHOICES = [
        ('ajout', 'Ajout'),
        ('modification', 'Modification'),
        ('suppression', 'Suppression'),
    ]
    banque = models.ForeignKey(
        BanqueDeSang, on_delete=models.CASCADE, null=True, related_name='historique_stock'
    )
    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    groupe_sanguin = models.CharField(max_length=3, null=True, blank=True)
    description = models.TextField()
    date = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']
        verbose_name = "Historique de stock"
        verbose_name_plural = "Historiques de stock"

    def __str__(self):
        return f"{self.get_action_display()} - {self.groupe_sanguin or ''} ({self.date:%Y-%m-%d %H:%M})"

    @classmethod
    def enregistrer(cls, banque, utilisateur, action, groupe_sanguin, description):
        return cls.objects.create(
            banque=banque, utilisateur=utilisateur, action=action,
            groupe_sanguin=groupe_sanguin, description=description,
        )
