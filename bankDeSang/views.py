from django.shortcuts import render
from .models import *
from decorateurs import check_role
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from serviceMedicaux.models import DemandeDeSang, Stock_de_sang
# from .models import PocheDeSang
from django.contrib import messages
from _auth.models import *
from django.http import HttpResponse, JsonResponse
# from django.db.models import Q, Count
import random

# Create your views here.

# @bankDeSang
@login_required(login_url='/_auth/authentification/')
@check_role('blood_bank')
def accueilBankDeSang(request):
    nbr_poche = StockDeSang.objects.aggregate(total_poches=models.Sum('nombre_de_poches'))['total_poches']
    nombre_demandes = DemandeDeSang.nbre_demande_en_attente_service_medicaux()

    # poche = PocheDeSang.objects.all()
    # # récupérer l'id de la banque de sang connectée
    # bank_de_sang = request.user.banque_de_sang
    # # récupérer les poches de sang et affecter à leur champ bank_de_sang l'id de la banque de sang connectée
    # poches = PocheDeSang.objects.all()
    # for poche in poches:
    #     poche.bank_de_sang = bank_de_sang
    #     poche.save()
    return render(request, 'frontend/bankDeSang/accueil_bankDeSang.html', {'nbr_poche': nbr_poche, 'nombre_demandes': nombre_demandes})

def notification(request):
    demandes_non_notifiees = DemandeDeSang.objects.filter(notification_envoyee=False, statut='En attente', serviceMedicaux__isnull=False)
    print(demandes_non_notifiees)
    return render(request, 'frontend/bankDeSang/base.html', {'demandes': demandes_non_notifiees})

@login_required(login_url='/_auth/authentification/')
@check_role('blood_bank')
def refuser_demande(request):
    demande_id = request.GET.get('demande_id')
    groupe_sang = request.GET.get('groupe_sang')
    print('groupe_sang')
    print(groupe_sang)
    if not demande_id or not groupe_sang:
        return JsonResponse({'status': 'error', 'message': 'Paramètres invalides.'}, status=400)

    try:
        demande = DemandeDeSang.objects.get(id=demande_id)
        etat_groupes = demande.etat_groupes
        etat_groupes[groupe_sang] = 'Rejetée'
        demande.etat_groupes = etat_groupes
        demande.save()
        return JsonResponse({'status': 'success', 'message': 'Demande rejetée avec succès.'})
    except DemandeDeSang.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Demande introuvable.'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)



@login_required(login_url='/_auth/authentification/')
@check_role('blood_bank')
def gestionStock(request):
    if request.method == 'POST':
        donneur_id = request.POST.get('donneur', None)
        matricule = request.POST.get('matricule', '')
        date_de_prelevement_str = request.POST.get('date_de_prelevement', '')
        type_produit = request.POST.get('type_produit', '')
        groupe_sanguin = request.POST.get('groupe_sanguin', '')

        date_de_prelevement = datetime.strptime(date_de_prelevement_str, '%Y-%m-%d').date()
        
        donneur = Donneur.objects.get(id=donneur_id) if donneur_id else None

        if PocheDeSang.objects.filter(matricule=matricule).exists():
            messages.error(request, 'Le matricule existe déjà.')
            return render(request, 'frontend/bankDeSang/gestion_stock.html', {'stocks': StockDeSang.objects.all()})

        poche_de_sang = PocheDeSang.objects.create(
            donneur=donneur,
            matricule=matricule,
            date_de_prelevement=date_de_prelevement,
            type_produit=type_produit,
            groupe_sanguin=groupe_sanguin,
            bank_de_sang=request.user.banque_de_sang
        )

        StockDeSang.enregistrer_stock(poche_de_sang, 1)

    stocks = StockDeSang.objects.all()
    return render(request, 'frontend/bankDeSang/gestion_stock.html', {'stocks': stocks})

@login_required(login_url='/_auth/authentification/')
@check_role('blood_bank')
def detailStock(request, stock_id):
    stock = StockDeSang.objects.get(id=stock_id)
    poches = PocheDeSang.objects.filter(groupe_sanguin=stock.groupe_sanguin, bank_de_sang=request.user.banque_de_sang, est_disponible=True)
    return render(request, 'frontend/bankDeSang/detail_stock.html', {'stock': stock, 'poches': poches})


@login_required(login_url='/_auth/authentification/')
@check_role('blood_bank')
def listeDonneurs(request):
    return render(request, 'frontend/bankDeSang/liste_donneurs.html')


@login_required(login_url='/_auth/authentification/')
@check_role('blood_bank')
def donneurMonetaire(request):
    return render(request, 'frontend/bankDeSang/donneur_monetaire.html')

@login_required(login_url='/_auth/authentification/')
@check_role('blood_bank')
def listeDemandesDeSang(request):
    demandes = DemandeDeSang.objects.filter(etat__in=['En attente', '1/2 Approuvée'], serviceMedicaux__isnull=False)
    demandes_data = []

    for demande in demandes:
        service_medical = demande.serviceMedicaux.email
        groupe_sanguin = demande.groupeSanguin()
        nombre_poches = demande.nombrePoches()
        demande_zip = list(zip(groupe_sanguin, nombre_poches))
        groupe_etat_approuvee = []
        groupe_etat_refusee = []

        #récupérer les poches de sang disponibles pour cette demande
        poches_disponibles = PocheDeSang.objects.filter(groupe_sanguin=demande.groupe_sanguin, est_disponible=True)
        poches_data = [{'id': poche.id, 'matricule': poche.matricule} for poche in poches_disponibles]

        # vérifier dans la demande si le groupe sanguin est approuvé
        for groupe, etat in demande.etat_groupes.items():
            if etat == 'Approuvée':
                groupe_etat_approuvee.append(groupe)
            elif etat == 'Rejetée':
                groupe_etat_refusee.append(groupe)
        
        poches_allouees = demande.nombre_poches_allouees
            
        print("demande_etat")
        print(groupe_etat_approuvee)


        print("demande_zip")
        print(demande_zip)
        
        
        
        demandes_data.append({
            'demande': demande,
            'demande_zip': demande_zip,
            'service_medical': service_medical,
            'groupe_sanguin': groupe_sanguin,
            'nombre_poches': nombre_poches,
            'poches_disponibles': poches_data,
            'groupe_etat_approuvee': groupe_etat_approuvee,
            'groupe_etat_refusee': groupe_etat_refusee,
            'poches_allouees': poches_allouees,
        })

    context = {
        'demandes_data': demandes_data,
    }
    return render(request, 'frontend/bankDeSang/liste_demandes_de_sang.html', context)

@login_required(login_url='/_auth/authentification/')
@check_role('blood_bank')
def historiqueDemandesDeSang(request):
    demandes = DemandeDeSang.objects.filter(serviceMedicaux__isnull=False, etat__in=['Approuvée', 'Rejetée'])
    demandes_data = []

    for demande in demandes:
        service_medical = demande.serviceMedicaux.email
        groupe_sanguin = demande.groupeSanguin()
        nombre_poches = demande.nombrePoches()
        demande_zip = list(zip(groupe_sanguin, nombre_poches))
        groupe_etat_approuvee = []
        groupe_etat_refusee = []

        # vérifier dans la demande si le groupe sanguin est approuvé
        for groupe, etat in demande.etat_groupes.items():
            if etat == 'Approuvée':
                groupe_etat_approuvee.append(groupe)
            elif etat == 'Rejetée':
                groupe_etat_refusee.append(groupe)

        demandes_data.append({
            'demande': demande,
            'demande_zip': demande_zip,
            'service_medical': service_medical,
            'groupe_sanguin': groupe_sanguin,
            'nombre_poches': nombre_poches,
            'groupe_etat_approuvee': groupe_etat_approuvee,
            'groupe_etat_refusee': groupe_etat_refusee,
        })

    context = {
        'demandes_data': demandes_data,
    }
    return render(request, 'frontend/bankDeSang/historique_demandes_de_sang.html', context)


@login_required(login_url='/_auth/authentification/')
@check_role('blood_bank')
def statistiques(request):
    return render(request, 'frontend/bankDeSang/statistiques.html')


@login_required(login_url='/_auth/authentification/')
@check_role('blood_bank')
def poches_disponibles(request):
    demande_id = request.GET.get('demande_id')
    groupe_sang = request.GET.get('groupe_sang')

    try:
        demande = DemandeDeSang.objects.get(id=demande_id)
        poches = list(PocheDeSang.objects.filter(groupe_sanguin=groupe_sang, est_disponible=True))
        random.shuffle(poches)
        poches = poches[:12]  # Prendre seulement 12 poches aléatoires
        poches_data = [{'groupe_sanguin': poche.groupe_sanguin, 'matricule': poche.matricule, 'exp': poche.jour_restant()} for poche in poches]
        return JsonResponse({'poches': poches_data})
    except DemandeDeSang.DoesNotExist:
        return JsonResponse({'error': 'Demande non trouvée'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)




@login_required(login_url='/_auth/authentification/')
@check_role('blood_bank')
def accepter_demande(request):
    if request.method == 'POST':
        demande_id = request.POST.get('demande_id')
        groupe_sang = request.POST.get('groupe_sang')
        poches_selectionnees = request.POST.getlist('poches[]')

        try:
            demande = DemandeDeSang.objects.get(id=demande_id)
            for poche_matricule in poches_selectionnees:
                poche = PocheDeSang.objects.get(matricule=poche_matricule)
                poche.est_disponible = False
                poche.en_transition = True
                poche.save()

                if groupe_sang in demande.nombre_poches_allouees:
                    demande.nombre_poches_allouees[groupe_sang].append(poche_matricule)
                else:
                    demande.nombre_poches_allouees[groupe_sang] = [poche_matricule]

                demande.etat_groupes[groupe_sang] = 'Approuvée'

            # Vérifier si tous les groupes sanguins ont une appréciation
            if all([v in ['Approuvée', 'Rejetée'] for v in demande.etat_groupes.values()]):
                demande.etat = 'Approuvée'
                demande.save()

            demande.save()
            messages.success(request, 'Demande acceptée avec succès.')
        except DemandeDeSang.DoesNotExist:
            messages.error(request, 'Demande non trouvée.')
        except PocheDeSang.DoesNotExist:
            messages.error(request, 'Poche de sang non trouvée.')
        except Exception as e:
            messages.error(request, f'Erreur: {str(e)}')

    return redirect('bankDeSang:listeDemandesDeSang')
