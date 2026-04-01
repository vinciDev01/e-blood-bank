from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from datetime import datetime
from .models import *
from bankDeSang.models import *
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
# from django.conf import settings
from .models import *
from decorateurs import check_role
from django.shortcuts import get_object_or_404




# Create your views here.

# @serviceMedicaux
@login_required(login_url='/_auth/authentification/')
def accueilServiceMedicaux(request):
    # `request.user` contient l'utilisateur authentifié
    hopital = request.user.service_medical.nom_etablissement
    return render(request, 'frontend/serviceMedicaux/accueil_service_medicaux.html', {'hopital': hopital})

def mesDemandesDeSang(request):
    demandes = DemandeDeSang.objects.filter(serviceMedicaux=request.user.service_medical)
    service_medical = request.user.service_medical
    grp_sanguins = []
    nbr_poches = []
    poches_allouees = []
    for demande in demandes:
        grp_sanguins.extend(demande.groupe_sanguin[service_medical.email])
        nbr_poches.extend(demande.nombre_poches[service_medical.email])
        if service_medical.email in demande.nombre_poches_allouees:
            poches_allouees.extend(demande.nombre_poches_allouees[service_medical.email])
        # print(nbr_poches)

    mes_demandes = True
    id_demande = DemandeDeSang.objects.filter(serviceMedicaux=request.user.service_medical, etat="Approuvée").values_list('id', flat=True).first()
    print("id_demande")
    print(id_demande)
    context = {
        'demandes': demandes,
        'grp_sanguins': grp_sanguins,
        'nbr_poches': nbr_poches,
        'poches_allouees': poches_allouees,
        'mes_demandes': mes_demandes,
        'id_demande': id_demande
    }
    return render(request, 'frontend/serviceMedicaux/liste_demande_de_sang.html', context)

#demande des utilisateurs
def listeDemandeDeSang(request):
    demandes = DemandeDeSang.objects.filter(etat='En attente', patient__isnull=False)
    return render(request, 'frontend/serviceMedicaux/liste_demande_de_sang.html', {'demandes': demandes})


@login_required(login_url='/_auth/authentification/')
def faireDemandeDeSang(request):
    if request.method == 'POST':
        type_produit = request.POST.get('typeProduit', '')
        urgence = request.POST.get('urgence', '')
        motif = request.POST.get('motif', '')

        if request.user.role == 'medical':
            groupes_sanguins = request.POST.getlist('groupesSanguins[]')
            nombres_poches = request.POST.getlist('nombresPoches[]')
            service_medical = request.user.service_medical
            demande = DemandeDeSang(
                serviceMedicaux=service_medical,
                groupe_sanguin={service_medical.email: groupes_sanguins},
                type_produit=type_produit,
                nombre_poches={service_medical.email: nombres_poches},
                urgence=urgence,
                motif=motif,
                notification_envoyee=False
            )
            demande.save()
            return redirect('serviceMedicaux:accueilServiceMedicaux')
        elif request.user.role == 'donor':
            groupe_sanguin = request.POST.get('groupeSanguin', '')
            nombre_poche = request.POST.get('nombrePoche', '')
            donneur = request.user.donneur
            demande = DemandeDeSang(
                donneur=donneur,
                groupe_sanguin={"groupe_sanguin": groupe_sanguin},
                type_produit=type_produit,
                nombre_poches={"nombre_poche": nombre_poche},
                urgence=urgence,
                motif=motif,
                notification_envoyee=False
            )
            demande.save()
            # return redirect('serviceMedicaux:accueilServiceMedicaux')
        elif request.user.role == 'generic':
            # Gérer les utilisateurs lambda
            groupe_sanguin = request.POST.get('groupeSanguin', '')
            nombre_poche = request.POST.get('nombrePoche', '')
            user = request.user

            patient = Patient.objects.create(
                nom_complet=request.POST['nomComplet'],
                date_de_naissance=request.POST['dateDeNaissance'],
                proche=request.POST['proche'],
                groupe_sanguin=groupe_sanguin,
                relation_proche_patient=request.POST['relationProchePatient'],
                telephone_proche=request.POST['telephone'],
                utilisateur = user
            )
            demande = DemandeDeSang(
                patient=patient,
                groupe_sanguin={user.email: groupe_sanguin},
                type_produit=type_produit,
                nombre_poches={user.email: nombre_poche},
                urgence=urgence,
                motif=motif,
                notification_envoyee=False
            )
            # for service_medical in ServiceMedicaux.objects.all():
            #     demande.serviceMedicaux = service_medical
            demande.save()

            return redirect('frontend:accueil')

        # demande.save()
        messages.success(request, 'Votre demande a été enregistrée avec succès')
        # return redirect('serviceMedicaux:accueilServiceMedicaux')

    return render(request, 'frontend/serviceMedicaux/faire_demande_de_sang.html')




# def faireDemandeDeSang2(request):
#     if request.method == 'POST':
#         type_produit = request.POST.get('typeProduit', '')
#         urgence = request.POST.get('urgence', '')
#         motif = request.POST.get('motif', '')

#         if request.user.role == 'medical':
#             groupes_sanguins = request.POST.getlist('groupesSanguins[]')
#             nombres_poches = request.POST.getlist('nombresPoches[]')
#             service_medical = request.user.service_medical
#             demandes = []
#             for groupe_sanguin, nombre_poche in zip(groupes_sanguins, nombres_poches):
#                 demande = DemandeDeSang(
#                     serviceMedicaux=service_medical,
#                     groupe_sanguin={service_medical.email: groupe_sanguin},
#                     type_produit=type_produit,
#                     nombre_poches={service_medical.email: nombre_poche},
#                     urgence=urgence,
#                     motif=motif,
#                     notification_envoyee=False
#                 )
#                 demandes.append(demande)
#         elif request.user.role == 'donor':
#             groupe_sanguin = request.POST.get('groupeSanguin', '')
#             nombre_poche = request.POST.get('nombrePoche', '')
#             donneur = request.user.donneur
#             demande = DemandeDeSang(
#                 donneur=donneur,
#                 groupe_sanguin={"groupe_sanguin": groupe_sanguin},
#                 type_produit=type_produit,
#                 nombre_poches={"nombre_poche": nombre_poche},
#                 urgence=urgence,
#                 motif=motif,
#                 notification_envoyee=False
#             )
#             demandes = [demande]
#         else:
#             # Gérer les utilisateurs lambda
#             groupe_sanguin = request.POST.get('groupeSanguin', '')
#             nombre_poche = request.POST.get('nombrePoche', '')
#             patient = Patient.objects.create(
#                 nom_complet=request.POST['nomComplet'],
#                 date_de_naissance=request.POST['dateDeNaissance'],
#                 proche=request.POST['proche'],
#                 relation_proche_patient=request.POST['relationProchePatient'],
#                 telephone_proche=request.POST['telephone'],
#             )
#             demande = DemandeDeSang(
#                 patient=patient,
#                 groupe_sanguin={"groupe_sanguin": groupe_sanguin},
#                 type_produit=type_produit,
#                 nombre_poches={"nombre_poche": nombre_poche},
#                 urgence=urgence,
#                 motif=motif,
#                 notification_envoyee=False
#             )
#             demandes = [demande]
#             for service_medical in ServiceMedicaux.objects.all():
#                 demande.serviceMedicaux = service_medical
#                 demande.save()

#         for demande in demandes:
#             demande.save()
#         messages.success(request, 'Votre demande a été enregistrée avec succès')
#         return redirect('serviceMedicaux:accueilServiceMedicaux')

#     return render(request, 'frontend/serviceMedicaux/faire_demande_de_sang.html')



def getToutesDemande(request):
    demandes = DemandeDeSang.objects.get(etat='En attente')
    return JsonResponse({'demandes': list(demandes.values())})



def recevoir_poches(request):
    if request.method == 'POST':
        demande_id = request.POST.get('demande_id')
        poches = request.POST.getlist('poches[]')
        demande = DemandeDeSang.objects.get(id=demande_id)
        groupes_sanguins = demande.groupe_sanguin[demande.serviceMedicaux.email]

        for groupe in groupes_sanguins:
            if groupe in poches:
                demande.etat_groupes[groupe] = 'Approuvée'
            else:
                demande.etat_groupes[groupe] = 'Rejetée'

        demande.poches_recues = {demande.serviceMedicaux.email: poches}

        for matricul in poches:
            poche = PocheDeSang.objects.get(matricule=matricul)
            poche.bank_de_sang = None
            poche.service_medicaux = demande.serviceMedicaux
            poche.en_transition = False
            poche.est_disponible = True
            StockDeSang.enregistrer_stock(poche, -1)
            Stock_de_sang.enregistrer_stock(poche, 1)
            poche.save()

        demande.save()
        messages.success(request, 'Les poches ont été reçues avec succès')
    return redirect('serviceMedicaux:mesDemandesDeSang')

# @login_required(login_url='/_auth/authentification/')
# @check_role('blood_bank')
# def gestionStock(request):
#     if request.method == 'POST':
#         donneur_id = request.POST.get('donneur', None)
#         matricule = request.POST.get('matricule', '')
#         date_de_prelevement_str = request.POST.get('date_de_prelevement', '')
#         type_produit = request.POST.get('type_produit', '')
#         groupe_sanguin = request.POST.get('groupe_sanguin', '')

#         date_de_prelevement = datetime.strptime(date_de_prelevement_str, '%Y-%m-%d').date()
        
#         donneur = Donneur.objects.get(id=donneur_id) if donneur_id else None

#         if PocheDeSang.objects.filter(matricule=matricule).exists():
#             messages.error(request, 'Le matricule existe déjà.')
#             return render(request, 'frontend/bankDeSang/gestion_stock.html', {'stocks': StockDeSang.objects.all()})

#         poche_de_sang = PocheDeSang.objects.create(
#             donneur=donneur,
#             matricule=matricule,
#             date_de_prelevement=date_de_prelevement,
#             type_produit=type_produit,
#             groupe_sanguin=groupe_sanguin
#         )

#         StockDeSang.enregistrer_stock(poche_de_sang, 1)

#     stocks = StockDeSang.objects.all()
#     return render(request, 'frontend/bankDeSang/gestion_stock.html', {'stocks': stocks})
