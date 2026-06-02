from datetime import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db import models
import random
import json

from .models import PocheDeSang, StockDeSang
from _auth.models import Donneur, BanqueDeSang
from serviceMedicaux.models import DemandeDeSang, Stock_de_sang
from decorateurs import check_role


@login_required
@check_role('blood_bank')
def accueilBankDeSang(request):
    from datetime import date, timedelta

    nbr_poche = StockDeSang.objects.aggregate(total_poches=models.Sum('nombre_de_poches'))['total_poches'] or 0
    nombre_demandes = DemandeDeSang.nbre_demande_en_attente_service_medicaux()
    nombre_donneurs = Donneur.objects.count()

    poches_disponibles = PocheDeSang.objects.filter(est_disponible=True).count()
    poches_expirees = PocheDeSang.objects.filter(date_expiration__lt=date.today()).count()
    poches_bientot_expirees = PocheDeSang.objects.filter(
        date_expiration__gte=date.today(),
        date_expiration__lte=date.today() + timedelta(days=7),
        est_disponible=True,
    ).count()

    stocks = StockDeSang.objects.all()
    stock_par_groupe = {g: 0 for g, _ in PocheDeSang.groupe_sanguin_choices}
    for s in stocks:
        if s.groupe_sanguin:
            stock_par_groupe[s.groupe_sanguin] = stock_par_groupe.get(s.groupe_sanguin, 0) + s.nombre_de_poches
    total_stock = sum(stock_par_groupe.values()) or 1
    repartition = [
        {'groupe': g, 'nombre': n, 'pourcentage': round(n * 100 / total_stock, 1)}
        for g, n in stock_par_groupe.items()
    ]

    demandes_recentes = DemandeDeSang.objects.filter(
        serviceMedicaux__isnull=False,
    ).order_by('-date_demande')[:5]

    return render(request, 'frontend/bankDeSang/accueil_bankDeSang.html', {
        'nbr_poche': nbr_poche,
        'nombre_demandes': nombre_demandes,
        'nombre_donneurs': nombre_donneurs,
        'poches_disponibles': poches_disponibles,
        'poches_expirees': poches_expirees,
        'poches_bientot_expirees': poches_bientot_expirees,
        'repartition': repartition,
        'demandes_recentes': demandes_recentes,
    })


@login_required
@check_role('blood_bank')
def notification(request):
    demandes_non_notifiees = DemandeDeSang.objects.filter(
        notification_envoyee=False,
        etat='En attente',
        serviceMedicaux__isnull=False,
    )
    return render(request, 'frontend/bankDeSang/base.html', {'demandes': demandes_non_notifiees})


@login_required
@check_role('blood_bank')
def refuser_demande(request):
    demande_id = request.GET.get('demande_id')
    groupe_sang = request.GET.get('groupe_sang')
    if not demande_id or not groupe_sang:
        return JsonResponse({'status': 'error', 'message': 'Parametres invalides.'}, status=400)

    try:
        demande = DemandeDeSang.objects.get(id=demande_id)
        demande.etat_groupes[groupe_sang] = 'Rejetee'
        demande.save()
        return JsonResponse({'status': 'success', 'message': 'Demande rejetee avec succes.'})
    except DemandeDeSang.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Demande introuvable.'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
@check_role('blood_bank')
def gestionStock(request):
    from datetime import date, timedelta

    if request.method == 'POST':
        donneur_id = request.POST.get('donneur', None)
        matricule = request.POST.get('matricule', '')
        date_de_prelevement_str = request.POST.get('date_de_prelevement', '')
        type_produit = request.POST.get('type_produit', '')
        groupe_sanguin = request.POST.get('groupe_sanguin', '')

        date_de_prelevement = datetime.strptime(date_de_prelevement_str, '%Y-%m-%d').date()

        # Le formulaire fournit le NUMÉRO de donneur (numero_de_donneur), pas la
        # clé primaire. Recherche par ce numéro ; champ facultatif.
        donneur = None
        numero_donneur = (donneur_id or '').strip()
        if numero_donneur:
            donneur = Donneur.objects.filter(numero_de_donneur=numero_donneur).first()
            if donneur is None:
                messages.error(request, "Aucun donneur trouvé avec ce numéro.")
                return redirect('bankDeSang:gestionStock')

        if PocheDeSang.objects.filter(matricule=matricule).exists():
            messages.error(request, 'Ce matricule existe déjà.')
            return redirect('bankDeSang:gestionStock')

        poche_de_sang = PocheDeSang.objects.create(
            donneur=donneur,
            matricule=matricule,
            date_de_prelevement=date_de_prelevement,
            type_produit=type_produit,
            groupe_sanguin=groupe_sanguin,
            bank_de_sang=request.user.banque_de_sang,
        )
        StockDeSang.enregistrer_stock(poche_de_sang, 1)
        messages.success(request, 'Poche de sang enregistrée avec succès.')
        return redirect('bankDeSang:gestionStock')

    stocks_dict = {g: 0 for g, _ in PocheDeSang.groupe_sanguin_choices}
    for s in StockDeSang.objects.all():
        if s.groupe_sanguin:
            stocks_dict[s.groupe_sanguin] = stocks_dict.get(s.groupe_sanguin, 0) + s.nombre_de_poches
    total_poches = sum(stocks_dict.values())
    max_poches = max(stocks_dict.values()) if stocks_dict.values() else 0

    stocks = []
    for grp, _ in PocheDeSang.groupe_sanguin_choices:
        n = stocks_dict.get(grp, 0)
        pct = round(n * 100 / max_poches, 1) if max_poches else 0
        # essayer de retrouver un stock existant pour pouvoir lier au detail
        stock_obj = StockDeSang.objects.filter(groupe_sanguin=grp).first()
        if n < 5:
            level = 'critique'
        elif n < 15:
            level = 'faible'
        else:
            level = 'ok'
        stocks.append({
            'id': stock_obj.id if stock_obj else None,
            'groupe': grp,
            'nombre': n,
            'pct': pct,
            'niveau': level,
        })

    poches_bientot_expirees = PocheDeSang.objects.filter(
        bank_de_sang=request.user.banque_de_sang,
        est_disponible=True,
        date_expiration__gte=date.today(),
        date_expiration__lte=date.today() + timedelta(days=7),
    ).count()
    poches_expirees = PocheDeSang.objects.filter(
        bank_de_sang=request.user.banque_de_sang,
        date_expiration__lt=date.today(),
    ).count()

    return render(request, 'frontend/bankDeSang/gestion_stock.html', {
        'stocks': stocks,
        'total_poches': total_poches,
        'nombre_groupes': sum(1 for v in stocks_dict.values() if v > 0),
        'poches_bientot_expirees': poches_bientot_expirees,
        'poches_expirees': poches_expirees,
        'types_produit': PocheDeSang.type_produit_choices,
        'groupes_sanguins': PocheDeSang.groupe_sanguin_choices,
        'today_iso': date.today().isoformat(),
    })


@login_required
@check_role('blood_bank')
def detailStock(request, stock_id):
    stock = get_object_or_404(StockDeSang, id=stock_id)
    poches = PocheDeSang.objects.filter(
        groupe_sanguin=stock.groupe_sanguin,
        bank_de_sang=request.user.banque_de_sang,
        est_disponible=True,
    )
    return render(request, 'frontend/bankDeSang/detail_stock.html', {'stock': stock, 'poches': poches})


@login_required
@check_role('blood_bank')
def listeDonneurs(request):
    search = request.GET.get('q', '').strip()
    groupe = request.GET.get('groupe', '').strip()

    donneurs_qs = Donneur.objects.select_related('user').annotate(
        nb_dons=models.Count('pochedesang')
    )

    if search:
        from django.db.models import Q
        donneurs_qs = donneurs_qs.filter(
            Q(nom__icontains=search) | Q(prenom__icontains=search)
            | Q(numero_de_donneur__icontains=search) | Q(user__email__icontains=search)
        )

    if groupe:
        donneurs_qs = donneurs_qs.filter(groupe_sanguin=groupe)

    donneurs = donneurs_qs.order_by('-nb_dons', 'nom')

    total_donneurs = Donneur.objects.count()
    donneurs_actifs = Donneur.objects.filter(pochedesang__isnull=False).distinct().count()
    total_dons = PocheDeSang.objects.count()

    from _auth.models import Donneur as DM
    groupes_disponibles = [g for g, _ in DM.groupe_sanguin_choices]

    return render(request, 'frontend/bankDeSang/liste_donneurs.html', {
        'donneurs': donneurs,
        'total_donneurs': total_donneurs,
        'donneurs_actifs': donneurs_actifs,
        'total_dons': total_dons,
        'search': search,
        'groupe_filtre': groupe,
        'groupes_disponibles': groupes_disponibles,
    })


@login_required
@check_role('blood_bank')
def donneurMonetaire(request):
    return render(request, 'frontend/bankDeSang/donneur_monetaire.html')


@login_required
@check_role('blood_bank')
def listeDemandesDeSang(request):
    # Inclure les demandes en attente et partiellement approuvees
    demandes = DemandeDeSang.objects.filter(
        etat__in=['En attente', '1/2 Approuvee'],
        serviceMedicaux__isnull=False,
    )
    demandes_data = []

    bank = request.user.banque_de_sang

    for demande in demandes:
        service_medical = demande.serviceMedicaux.email
        groupe_sanguin = demande.groupeSanguin()
        nombre_poches = demande.nombrePoches()
        demande_zip = list(zip(groupe_sanguin, nombre_poches))
        groupe_etat_approuvee = []
        groupe_etat_refusee = []

        # Recuperer les poches disponibles pour CHAQUE groupe sanguin de la demande
        # (et filtrees par la banque connectee)
        poches_disponibles = []
        for grp in groupe_sanguin:
            poches_grp = PocheDeSang.objects.filter(
                groupe_sanguin=grp,
                est_disponible=True,
                bank_de_sang=bank,
            )
            poches_disponibles.extend(
                [{'id': p.id, 'matricule': p.matricule} for p in poches_grp]
            )

        for groupe, etat in demande.etat_groupes.items():
            if etat == 'Approuvee':
                groupe_etat_approuvee.append(groupe)
            elif etat == 'Rejetee':
                groupe_etat_refusee.append(groupe)

        demandes_data.append({
            'demande': demande,
            'demande_zip': demande_zip,
            'service_medical': service_medical,
            'groupe_sanguin': groupe_sanguin,
            'nombre_poches': nombre_poches,
            'poches_disponibles': poches_disponibles,
            'groupe_etat_approuvee': groupe_etat_approuvee,
            'groupe_etat_refusee': groupe_etat_refusee,
            'poches_allouees': demande.nombre_poches_allouees,
        })

    return render(request, 'frontend/bankDeSang/liste_demandes_de_sang.html', {
        'demandes_data': demandes_data,
    })


@login_required
@check_role('blood_bank')
def historiqueDemandesDeSang(request):
    demandes = DemandeDeSang.objects.filter(
        serviceMedicaux__isnull=False,
        etat__in=['Approuvee', 'Rejetee'],
    )
    demandes_data = []

    for demande in demandes:
        service_medical = demande.serviceMedicaux.email
        groupe_sanguin = demande.groupeSanguin()
        nombre_poches = demande.nombrePoches()
        demande_zip = list(zip(groupe_sanguin, nombre_poches))
        groupe_etat_approuvee = []
        groupe_etat_refusee = []

        for groupe, etat in demande.etat_groupes.items():
            if etat == 'Approuvee':
                groupe_etat_approuvee.append(groupe)
            elif etat == 'Rejetee':
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

    return render(request, 'frontend/bankDeSang/historique_demandes_de_sang.html', {
        'demandes_data': demandes_data,
    })


@login_required
@check_role('blood_bank')
def statistiques(request):
    from datetime import date, timedelta
    from collections import OrderedDict

    today = date.today()

    # KPIs
    total_poches_collectees = PocheDeSang.objects.count()
    poches_disponibles = PocheDeSang.objects.filter(est_disponible=True).count()
    poches_distribuees = PocheDeSang.objects.filter(service_medicaux__isnull=False).count()
    poches_expirees = PocheDeSang.objects.filter(date_expiration__lt=today).count()
    total_donneurs = Donneur.objects.count()
    total_demandes = DemandeDeSang.objects.filter(serviceMedicaux__isnull=False).count()
    demandes_completees = DemandeDeSang.objects.filter(
        serviceMedicaux__isnull=False, etat='Completee'
    ).count()
    taux_approbation = round(demandes_completees * 100 / total_demandes, 1) if total_demandes else 0

    # Collectes par mois (12 derniers mois)
    mois_noms = ['Janv.', 'Févr.', 'Mars', 'Avr.', 'Mai', 'Juin',
                 'Juil.', 'Août', 'Sept.', 'Oct.', 'Nov.', 'Déc.']
    collectes_par_mois = []
    labels_mois = []
    for i in range(11, -1, -1):
        year = today.year
        month = today.month - i
        while month <= 0:
            month += 12
            year -= 1
        count = PocheDeSang.objects.filter(
            date_de_prelevement__year=year,
            date_de_prelevement__month=month,
        ).count()
        collectes_par_mois.append(count)
        labels_mois.append(f"{mois_noms[month - 1]} {str(year)[-2:]}")

    # Stock par groupe sanguin
    stock_par_groupe = OrderedDict((g, 0) for g, _ in PocheDeSang.groupe_sanguin_choices)
    for s in StockDeSang.objects.all():
        if s.groupe_sanguin:
            stock_par_groupe[s.groupe_sanguin] = stock_par_groupe.get(s.groupe_sanguin, 0) + s.nombre_de_poches
    groupes_labels = list(stock_par_groupe.keys())
    groupes_values = list(stock_par_groupe.values())

    # Demandes par état
    demandes_qs = DemandeDeSang.objects.filter(serviceMedicaux__isnull=False)
    etats_labels = ['En attente', 'Approuvée', 'Complétée', 'Rejetée']
    etats_values = [
        demandes_qs.filter(etat='En attente').count(),
        demandes_qs.filter(etat__in=['Approuvee', '1/2 Approuvee']).count(),
        demandes_qs.filter(etat='Completee').count(),
        demandes_qs.filter(etat='Rejetee').count(),
    ]

    # Top donneurs (par nombre de dons)
    top_donneurs = (
        PocheDeSang.objects
        .values('donneur__id', 'donneur__nom', 'donneur__prenom', 'donneur__groupe_sanguin')
        .annotate(nb_dons=models.Count('id'))
        .filter(donneur__isnull=False)
        .order_by('-nb_dons')[:5]
    )

    return render(request, 'frontend/bankDeSang/statistiques.html', {
        'total_poches_collectees': total_poches_collectees,
        'poches_disponibles': poches_disponibles,
        'poches_distribuees': poches_distribuees,
        'poches_expirees': poches_expirees,
        'total_donneurs': total_donneurs,
        'total_demandes': total_demandes,
        'demandes_completees': demandes_completees,
        'taux_approbation': taux_approbation,
        'labels_mois_json': json.dumps(labels_mois),
        'collectes_par_mois_json': json.dumps(collectes_par_mois),
        'groupes_labels_json': json.dumps(groupes_labels),
        'groupes_values_json': json.dumps(groupes_values),
        'etats_labels_json': json.dumps(etats_labels),
        'etats_values_json': json.dumps(etats_values),
        'top_donneurs': top_donneurs,
    })


@login_required
@check_role('blood_bank')
def poches_disponibles(request):
    demande_id = request.GET.get('demande_id')
    groupe_sang = request.GET.get('groupe_sang')

    try:
        demande = DemandeDeSang.objects.get(id=demande_id)
        # Filtrer par banque connectee
        poches = list(PocheDeSang.objects.filter(
            groupe_sanguin=groupe_sang,
            est_disponible=True,
            bank_de_sang=request.user.banque_de_sang,
        ))
        random.shuffle(poches)
        poches = poches[:12]
        poches_data = [{
            'groupe_sanguin': p.groupe_sanguin,
            'matricule': p.matricule,
            'exp': p.jour_restant(),
        } for p in poches]
        return JsonResponse({'poches': poches_data})
    except DemandeDeSang.DoesNotExist:
        return JsonResponse({'error': 'Demande non trouvee'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
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

                demande.etat_groupes[groupe_sang] = 'Approuvee'

            # Verifier si tous les groupes sanguins ont ete traites
            groupes_demandes = demande.groupeSanguin()
            tous_traites = all(
                demande.etat_groupes.get(g) in ['Approuvee', 'Rejetee']
                for g in groupes_demandes
            )
            if tous_traites and groupes_demandes:
                demande.etat = 'Approuvee'
            elif any(demande.etat_groupes.get(g) in ['Approuvee', 'Rejetee'] for g in groupes_demandes):
                demande.etat = '1/2 Approuvee'

            demande.save()
            messages.success(request, 'Demande acceptee avec succes.')
        except DemandeDeSang.DoesNotExist:
            messages.error(request, 'Demande non trouvee.')
        except PocheDeSang.DoesNotExist:
            messages.error(request, 'Poche de sang non trouvee.')
        except Exception as e:
            messages.error(request, f'Erreur: {str(e)}')

    return redirect('bankDeSang:listeDemandesDeSang')


@login_required
@check_role('blood_bank')
def carteBanques(request):
    response = render(request, 'frontend/bankDeSang/carte_banques_de_sang.html', {
        'banques': BanqueDeSang.donnees_carte(),
    })
    # Les serveurs de tuiles OpenStreetMap exigent un en-tête Referer ; la politique
    # globale 'same-origin' le supprime en cross-origin -> on transmet l'origine ici.
    response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    return response
