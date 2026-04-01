# from django.db import models
# from datetime import date
# import os

# def renomer_image(instance, filename):
#     upload_to = 'images/'
#     ext = filename.split('.')[-1]
#     filename = 'photo_profile/{}_{}.{}'.format(instance.nom, instance.prenom, ext)
#     return os.path.join(upload_to, filename)

# class Donneur(models.Model):
#     nom = models.CharField(max_length=200)
#     prenom = models.CharField(max_length=200)
#     date_de_naissance = models.DateField()
#     groupe_sanguin_choices = [
#         ('A+', 'A+'),
#         ('A-', 'A-'),
#         ('B+', 'B+'),
#         ('B-', 'B-'),
#         ('AB+', 'AB+'),
#         ('AB-', 'AB-'),
#         ('O+', 'O+'),
#         ('O-', 'O-'),
#     ]
#     groupe_sanguin = models.CharField(max_length=3, choices=groupe_sanguin_choices)
#     telephone = models.CharField(max_length=20)
#     email = models.EmailField()
#     adresse = models.CharField(max_length=255)
#     ville = models.CharField(max_length=100)
#     code_postal = models.CharField(max_length=10)
#     pays = models.CharField(max_length=100)
#     numero_identification = models.CharField(max_length=20, unique=True)
#     date_dernier_don = models.DateField(blank=True, null=True)
#     photo_profile = models.ImageField(upload_to=renomer_image, blank=True, null=True)

#     def __str__(self):
#         return f"{self.nom} {self.prenom} ({self.groupe_sanguin})"

#     @property # @property pour définir une méthode comme une propriété
#     def age(self): # Calcul de l'âge du donneur en fonction de sa date de naissance
#         return date.today().year - self.date_de_naissance.year - (
#             (date.today().month, date.today().day) < (self.date_de_naissance.month, self.date_de_naissance.day)
#         )

#     @property 
#     def peut_donner(self): # Vérification si le donneur peut donner du sang
#         if not self.date_dernier_don:
#             return True
#         temps_depuis_dernier_don = date.today() - self.date_dernier_don
#         return temps_depuis_dernier_don.days >= 90

#     def save(self, *args, **kwargs): # Surcharge de la méthode save pour vérifier l'âge du donneur
#         if self.age < 18 or self.age > 65:
#             raise ValueError("Le donneur doit avoir entre 18 et 65 ans.")
#         super().save(*args, **kwargs)

#     class Meta: # Classe Meta pour la configuration du modèle Donneur
#         verbose_name = "Donneur" # Nom au singulier
#         verbose_name_plural = "Donneurs" # Nom au pluriel
