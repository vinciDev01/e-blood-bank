from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from datetime import datetime

from .models import DemandeDeSang, Patient, Stock_de_sang
from bankDeSang.models import PocheDeSang, StockDeSang
from _auth.models import ServiceMedicaux
from decorateurs import check_role


@login_required
@check_role('medical')
def accueilServiceMedicaux(request):
    service = request.user.service_medical
    hopital = service.nom_etablissement

    demandes = DemandeDeSang.objects.filter(serviceMedicaux=service)
    nombre_demandes = demandes.count()
    demandes_en_attente = demandes.filter(etat='En attente').count()
    demandes_approuvees = demandes.filter(etat__in=['Approuvee', '1/2 Approuvee']).count()
    demandes_completees = demandes.filter(etat='Completee').count()
    demandes_rejetees = demandes.filter(etat='Rejetee').count()

    stocks = Stock_de_sang.objects.filter(service_medical=service)
    nbr_poche = sum(s.nombre_de_poches for s in stocks)

    stock_par_groupe = {g: 0 for g, _ in DemandeDeSang.groupe_sanguin_choices}
    for s in stocks:
        stock_par_groupe[s.groupe_sanguin] = stock_par_groupe.get(s.groupe_sanguin, 0) + s.nombre_de_poches
    total_stock = sum(stock_par_groupe.values()) or 1
    repartition = [
        {'groupe': g, 'nombre': n, 'pourcentage': round(n * 100 / total_stock, 1)}
        for g, n in stock_par_groupe.items()
    ]

    dernieres_demandes = demandes.order_by('-date_demande')[:5]

    context = {
        'hopital': hopital,
        'service': service,
        'nombre_demandes': nombre_demandes,
        'demandes_en_attente': demandes_en_attente,
        'demandes_approuvees': demandes_approuvees,
        'demandes_completees': demandes_completees,
        'demandes_rejetees': demandes_rejetees,
        'nbr_poche': nbr_poche,
        'repartition': repartition,
        'dernieres_demandes': dernieres_demandes,
    }
    return render(request, 'frontend/serviceMedicaux/accueil_service_medicaux.html', context)


@login_required
@check_role('medical')
def mesDemandesDeSang(request):
    demandes = DemandeDeSang.objects.filter(serviceMedicaux=request.user.service_medical)
    service_medical = request.user.service_medical
    grp_sanguins = []
    nbr_poches = []
    poches_allouees = []

    for demande in demandes:
        grp_sanguins.extend(demande.groupe_sanguin.get(service_medical.email, []))
        nbr_poches.extend(demande.nombre_poches.get(service_medical.email, []))
        if service_medical.email in demande.nombre_poches_allouees:
            poches_allouees.extend(demande.nombre_poches_allouees[service_medical.email])

    mes_demandes = True
    id_demande = DemandeDeSang.objects.filter(
        serviceMedicaux=request.user.service_medical,
        etat="Approuvee",
    ).values_list('id', flat=True).first()

    context = {
        'demandes': demandes,
        'grp_sanguins': grp_sanguins,
        'nbr_poches': nbr_poches,
        'poches_allouees': poches_allouees,
        'mes_demandes': mes_demandes,
        'id_demande': id_demande,
    }
    return render(request, 'frontend/serviceMedicaux/liste_demande_de_sang.html', context)


@login_required
@check_role('medical')
def listeDemandeDeSang(request):
    demandes = DemandeDeSang.objects.filter(etat='En attente', patient__isnull=False)
    return render(request, 'frontend/serviceMedicaux/liste_demande_de_sang.html', {'demandes': demandes})


@login_required
def faireDemandeDeSang(request):
    if request.method == 'POST':
        type_produit = request.POST.get('typeProduit', '')
        urgence = request.POST.get('urgence', '')
        motif = request.POST.get('motif', '')

        if request.user.role == 'medical':
            groupes_sanguins = request.POST.getlist('groupesSanguins[]')
            nombres_poches = request.POST.getlist('nombresPoches[]')
            service_medical = request.user.service_medical

            # Initialiser etat_groupes pour chaque groupe demande
            etat_groupes = {grp: 'En attente' for grp in groupes_sanguins}

            demande = DemandeDeSang(
                serviceMedicaux=service_medical,
                groupe_sanguin={service_medical.email: groupes_sanguins},
                type_produit=type_produit,
                nombre_poches={service_medical.email: nombres_poches},
                urgence=urgence,
                motif=motif,
                etat_groupes=etat_groupes,
                notification_envoyee=False,
            )
            demande.save()
            messages.success(request, 'Votre demande a ete enregistree avec succes')
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
                etat_groupes={groupe_sanguin: 'En attente'},
                notification_envoyee=False,
            )
            demande.save()
            messages.success(request, 'Votre demande a ete enregistree avec succes')
            return redirect('frontend:accueil')

        elif request.user.role == 'generic':
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
                utilisateur=user,
            )
            demande = DemandeDeSang(
                patient=patient,
                groupe_sanguin={user.email: groupe_sanguin},
                type_produit=type_produit,
                nombre_poches={user.email: nombre_poche},
                urgence=urgence,
                motif=motif,
                etat_groupes={groupe_sanguin: 'En attente'},
                notification_envoyee=False,
            )
            demande.save()
            messages.success(request, 'Votre demande a ete enregistree avec succes')
            return redirect('frontend:accueil')

    return render(request, 'frontend/serviceMedicaux/faire_demande_de_sang.html')


@login_required
@check_role('medical')
def getToutesDemande(request):
    demandes = DemandeDeSang.objects.filter(etat='En attente')
    data = list(demandes.values(
        'id', 'etat', 'type_produit', 'urgence', 'motif', 'date_demande',
    ))
    return JsonResponse({'demandes': data})


@login_required
@check_role('medical')
def recevoir_poches(request):
    if request.method == 'POST':
        demande_id = request.POST.get('demande_id')
        matricules_recues = request.POST.getlist('poches[]')

        demande = get_object_or_404(DemandeDeSang, id=demande_id)
        service = demande.serviceMedicaux

        # Stocker les poches recues
        demande.poches_recues = {service.email: matricules_recues}

        # Traiter chaque poche recue
        for matricule in matricules_recues:
            poche = get_object_or_404(PocheDeSang, matricule=matricule)

            # Transferer la poche de la banque vers le service medical
            poche.bank_de_sang = None
            poche.service_medicaux = service
            poche.en_transition = False
            poche.est_disponible = True
            poche.save()

            # Diminuer le stock de la banque de sang
            StockDeSang.enregistrer_stock(poche, -1)
            # Augmenter le stock du service medical
            Stock_de_sang.enregistrer_stock(poche, 1)

        # Mettre a jour l'etat des groupes : marquer comme complet
        groupes_sanguins = demande.groupe_sanguin.get(service.email, [])
        for groupe in groupes_sanguins:
            # Un groupe est "recu" si au moins une poche de ce groupe est dans les matricules recues
            demande.etat_groupes[groupe] = 'Completee'

        demande.etat = 'Completee'
        demande.save()
        messages.success(request, 'Les poches ont ete recues avec succes')

    return redirect('serviceMedicaux:mesDemandesDeSang')
