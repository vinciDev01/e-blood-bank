from django.db import models
from _auth.models import ServiceMedicaux, Donneur, Utilisateur
from bankDeSang.models import PocheDeSang


class Patient(models.Model):
    # Champs pour les informations personnelles du patient
    nom_complet = models.CharField(max_length=200)
    date_de_naissance = models.DateField()
    proche = models.CharField(max_length=200)
    groupe_sanguin = models.CharField(max_length=3, blank=True)
    relation_proche_patient = models.CharField(max_length=200, blank=True)
    telephone_proche = models.CharField(max_length=20)
    utilisateur = models.ForeignKey(Utilisateur, on_delete=models.CASCADE, null=True, blank=True)

    # Méthode pour retourner une représentation en chaîne de caractères de l'objet
    def __str__(self):
        return f"{self.nom_complet} ({self.date_de_naissance})"
    
    # Générer automatiquement le numéro d'identification du patient
    # def save(self, *args, **kwargs):
    #     if not self.numero_identification:
    #         self.numero_identification = f"{self.nom[:3].upper()}-{self.prenom[:3].upper()}-{self.proche[:3].upper()}-{date.today().year}"
    #     super(Patient, self).save(*args, **kwargs)

class DemandeDeSang(models.Model):
    serviceMedicaux = models.ForeignKey(ServiceMedicaux, on_delete=models.CASCADE, null=True, blank=True)
    patient = models.ForeignKey('Patient', on_delete=models.CASCADE, null=True, blank=True)
    donneur = models.ForeignKey(Donneur, on_delete=models.CASCADE, null=True, blank=True)
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
    groupe_sanguin = models.JSONField(default=dict)
    type_produit_choices = [
        ('Sang total', 'Sang total'),
        ('Concentré de globules rouges', 'Concentré de globules rouges'),
        ('Plasma', 'Plasma'),
        ('Plaquettes', 'Plaquettes'),
    ]
    type_produit = models.CharField(max_length=30, choices=type_produit_choices)
    nombre_poches = models.JSONField(default=dict)
    nombre_poches_allouees = models.JSONField(default=dict)
    poches_recues = models.JSONField(default=dict)
    urgence_choices = [
        ('Immédiate', 'Immédiate'),
        ('24 heures', '24 heures'),
        ('Non urgent', 'Non urgent'),
    ]
    urgence = models.CharField(max_length=20, choices=urgence_choices)
    motif_choices = [
        ('Chirurgie', 'Chirurgie'),
        ('Accident', 'Accident'),
        ('Maladie', 'Maladie'),
        ('Autre', 'Autre'),
    ]
    motif = models.CharField(max_length=20, choices=motif_choices)
    etat_choices = [
        ('En attente', 'En attente'),
        ('1/2 Approuvee', '1/2 Approuvee'),
        ('Approuvee', 'Approuvee'),
        ('Rejetee', 'Rejetee'),
        ('Completee', 'Completee'),
    ]
    etat = models.CharField(max_length=20, choices=etat_choices, default='En attente')
    etat_groupes = models.JSONField(default=dict)  # Nouveau champ pour suivre l'état de chaque groupe sanguin
    date_demande = models.DateField(auto_now_add=True)
    notification_envoyee = models.BooleanField(default=False)

    def __str__(self):
        return f"Demande de {self.serviceMedicaux.nom_etablissement if self.serviceMedicaux else 'N/A'} pour {self.patient.nom_complet if self.patient else 'N/A'}"

    def nom_etablissement(self):
        return self.serviceMedicaux.nom_etablissement

    def _valeur_pour_service(self, donnees):
        """Valeur d'un dict JSON indexé par l'email du service.

        Repli : si l'email courant du service est absent des clés (ex. email du
        service modifié après la création de la demande), on renvoie l'unique
        valeur présente — une demande n'étant rattachée qu'à un seul service —
        plutôt que de lever un KeyError.
        """
        if not isinstance(donnees, dict) or not donnees:
            return []
        email = self.serviceMedicaux.email if self.serviceMedicaux else None
        if email in donnees:
            return donnees[email]
        valeurs = list(donnees.values())
        return valeurs[0] if len(valeurs) == 1 else []

    def groupeSanguin(self):
        return self._valeur_pour_service(self.groupe_sanguin)

    def nombrePoches(self):
        return self._valeur_pour_service(self.nombre_poches)

    def nom_patient(self):
        return self.patient.nom_complet

    def grp_sanguin_patient(self):
        return self.patient.groupe_sanguin

    def nbr_poches_patient(self):
        # Robuste : le patient peut ne pas avoir d'utilisateur lié, et nombre_poches
        # est indexé par l'email du service (pas du patient). On réutilise la même
        # logique de repli que nombrePoches() et on renvoie un affichage simple.
        valeurs = self._valeur_pour_service(self.nombre_poches)
        if isinstance(valeurs, list):
            return ', '.join(str(v) for v in valeurs)
        return valeurs

    @classmethod
    def nbre_demande_en_attente_service_medicaux(cls):
        return cls.objects.filter(etat='En attente', serviceMedicaux__isnull=False).count()

    def get_etat_groupe(self, groupe_sang):
        return self.etat_groupes.get(groupe_sang, 'En attente')
    
    # def get_matricules(self):
    #     service_email = self.serviceMedicaux.email
    #     groupe_sanguin = self.groupe_sanguin.get(service_email)
    #     if groupe_sanguin:
    #         return self.nombre_poches_allouees.get(groupe_sanguin, [])
    #     return []
    
    def get_matricules(self):
        service_email = self.serviceMedicaux.email
        groupe_sanguin = self.groupe_sanguin.get(service_email, [])
        return self.nombre_poches_allouees.get(groupe_sanguin, [])

    
    class Meta:
        verbose_name = "Demande de Sang"
        verbose_name_plural = "Demandes de Sang"




class Stock_de_sang(models.Model):
    service_medical= models.ForeignKey(ServiceMedicaux, on_delete=models.CASCADE)
    groupe_sanguin = models.CharField(max_length=3, choices=PocheDeSang.groupe_sanguin_choices)
    nombre_de_poches = models.IntegerField(default=1)
    date_enregistrement = models.DateField(auto_now=True)

    def __str__(self):
        return f"Stock de {self.service_medical.nom_etablissement} ({self.groupe_sanguin}) - {self.nombre_de_poches} poches"
    
    @classmethod
    def enregistrer_stock(cls, poche_de_sang, nombre_de_poches):
        stock, created = cls.objects.get_or_create(service_medical=poche_de_sang.service_medicaux, groupe_sanguin=poche_de_sang.groupe_sanguin)
        if not created:
            stock.nombre_de_poches += nombre_de_poches
        else:
            stock.nombre_de_poches = nombre_de_poches
        stock.save()

