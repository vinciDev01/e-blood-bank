from django.shortcuts import render, redirect
from django.contrib import messages
from datetime import date
from _auth.models import *
from serviceMedicaux.models import *
from django.contrib.auth.decorators import login_required

# Create your views here.
def accueil(request):
    return render(request, 'frontend/accueil.html')

def listeHopitaux(request):
    hopitaux = ServiceMedicaux.objects.all()
    context = {
        'hopitaux': hopitaux
    }
    return render(request, 'frontend/liste_hopitaux.html', context)

def hopital(request, id):
    hopital = ServiceMedicaux.objects.get(id=id)
    context = {
        'hopital': hopital
    }
    return render(request, 'frontend/hopital.html', context)

@login_required
def listeDemandeDeSang(request):
    utilisateur = request.user
    id = utilisateur.id
    demandes = DemandeDeSang.objects.filter(patient__utilisateur=id)
    # demandes = DemandeDeSang.objects.filter(etat='En attente', patient__isnull=False)
    return render(request, 'frontend/demande_utilisateur.html', {'demandes': demandes})


# def patientDemandeDeSang(request):
#     if request.method == 'POST':
#         nom = request.POST['nom_patient']
#         prenom = request.POST['prenom_patient']
#         proche = request.POST['proche_patient']
#         relation = request.POST['relation_patient']
#         date_naissance = request.POST.get('date_naissance', '')
#         if date_naissance:
#             try:
#                 date_naissance = date.fromisoformat(date_naissance)
#             except ValueError:
#                 messages.error(request, 'Format de date invalide. Veuillez utiliser le format AAAA-MM-JJ.')
#                 return redirect('accueil')
#         groupe_sanguin = request.POST['groupe_sanguin']
#         type_produit = request.POST['type_produit']
#         telephone = request.POST['telephone']
#         quantite = request.POST['quantite']
#         urgence = request.POST['urgence']
#         motif = request.POST['motif']
#         commentaire = request.POST['commentaire']
#         num_identification = f"{nom[0].upper()}{prenom[0].upper()}{date_naissance.year}{date_naissance.month}{date_naissance.day}"
       
#         patient = Patient(nom=nom, prenom=prenom, proche=proche, relation_proche_patient=relation, date_de_naissance=date_naissance, groupe_sanguin=groupe_sanguin, telephone=telephone, numero_identification=num_identification)
#         patient.save()
#         hopitaux = ServiceMedicaux.objects.all()
#         for hopital in hopitaux:
#             demande = DemandeDeSang(patient=patient, hopital=hopital, type_produit=type_produit, quantite=quantite, urgence=urgence, motif=motif, commentaire=commentaire)
#             demande.save()
#             #envoyer une notification aux l'hopitaux
#             #envoyer une notification à l'utilisateur

#         messages.success(request, 'Votre demande a été enregistrée avec succès')
#         return redirect('accueil')
#     return render(request, 'frontend/accueil.html')



def centresDeDon(request):
    """Page publique : liste des centres de don (banques) + carte avec itinéraire.

    Filtre optionnel `?groupe=` : ne montre que les centres ayant au moins une
    poche disponible du groupe sanguin demandé.
    """
    contexte = BanqueDeSang.contexte_carte(request)
    contexte['centres'] = BanqueDeSang.objects.all()
    response = render(request, 'frontend/centres_de_don.html', contexte)
    # Les tuiles OpenStreetMap exigent un en-tête Referer (politique 'same-origin'
    # globale le supprimerait en cross-origin).
    response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    return response
