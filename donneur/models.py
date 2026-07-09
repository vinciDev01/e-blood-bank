from datetime import date

from django.db import models

from _auth.models import Donneur, BanqueDeSang


# Créneaux horaires proposés pour un rendez-vous de don.
CRENEAUX = [
    ('08:00-10:00', '08:00 - 10:00'),
    ('10:00-12:00', '10:00 - 12:00'),
    ('14:00-16:00', '14:00 - 16:00'),
    ('16:00-18:00', '16:00 - 18:00'),
]


class RendezVousDon(models.Model):
    """Rendez-vous de don planifié par un donneur dans une banque de sang."""

    STATUT_CHOICES = [
        ('Planifié', 'Planifié'),
        ('Annulé', 'Annulé'),
        ('Effectué', 'Effectué'),
    ]

    donneur = models.ForeignKey(Donneur, on_delete=models.CASCADE, related_name='rendez_vous')
    banque = models.ForeignKey(BanqueDeSang, on_delete=models.CASCADE)
    date = models.DateField()
    creneau = models.CharField(max_length=20, choices=CRENEAUX)
    statut = models.CharField(max_length=10, choices=STATUT_CHOICES, default='Planifié')
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['date', 'creneau']
        verbose_name = "Rendez-vous de don"
        verbose_name_plural = "Rendez-vous de don"

    def __str__(self):
        return f"{self.donneur} — {self.date} {self.creneau} @ {self.banque.nom_etablissement}"

    def est_a_venir(self):
        """Vrai si le rendez-vous est planifié et pas encore passé."""
        return self.statut == 'Planifié' and self.date >= date.today()
