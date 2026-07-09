from django.http import JsonResponse, FileResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from datetime import datetime

from .models import DemandeDeSang, Patient, Stock_de_sang
from bankDeSang.models import PocheDeSang, StockDeSang
from _auth.models import ServiceMedicaux, BanqueDeSang
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
def mes_demandes_flux(request):
    """Flux JSON du compteur de demandes pour le service médical (polling).

    count : demandes du service courant encore « En attente » (de réponse).
    etats : snapshot [id, etat] des dernières demandes, pour que le client
            détecte un changement d'état (réponse de la banque).
    """
    try:
        service = request.user.service_medical
    except ServiceMedicaux.DoesNotExist:
        return JsonResponse({'count': 0, 'etats': []})

    qs = DemandeDeSang.objects.filter(serviceMedicaux=service)
    count = qs.filter(etat='En attente').count()
    etats = list(qs.order_by('-id').values_list('id', 'etat')[:50])
    return JsonResponse({'count': count, 'etats': etats})


def _generer_ordonnance_silencieux(demande):
    """Génère l'ordonnance PDF sans faire échouer la création si la génération plante."""
    try:
        demande.generer_ordonnance()
    except Exception:
        pass


def servir_ordonnance(demande):
    """Renvoie une FileResponse (attachment) du PDF de `demande`.

    Génère le PDF à la volée s'il n'existe pas encore (demandes antérieures).
    Partagé par les vues de téléchargement service et banque.
    """
    if not demande.ordonnance_pdf:
        demande.generer_ordonnance()
    demande.ordonnance_pdf.open('rb')
    return FileResponse(
        demande.ordonnance_pdf, as_attachment=True,
        filename=f"Ordonnance_{demande.reference()}.pdf",
        content_type='application/pdf',
    )


@login_required
@check_role('medical')
def telechargerOrdonnance(request, demande_id):
    """Téléchargement de l'ordonnance par le service médical propriétaire."""
    try:
        service = request.user.service_medical
    except ServiceMedicaux.DoesNotExist:
        return redirect('serviceMedicaux:mesDemandesDeSang')
    demande = get_object_or_404(DemandeDeSang, id=demande_id, serviceMedicaux=service)
    return servir_ordonnance(demande)


@login_required
@check_role('medical')
def listeDemandeDeSang(request):
    demandes = DemandeDeSang.objects.filter(etat='En attente', patient__isnull=False)
    return render(request, 'frontend/serviceMedicaux/liste_demande_de_sang.html', {'demandes': demandes})


@login_required
def faireDemandeDeSang(request):
    if request.method == 'POST':
        type_produit = request.POST.get('type_produit', '').strip()
        urgence = request.POST.get('urgence', '').strip()
        motif = request.POST.get('motif', '').strip() or 'Autre'
        groupe_sanguin = request.POST.get('groupe_sanguin', '').strip()
        quantite = request.POST.get('quantite', '').strip()

        if request.user.role == 'medical':
            if not (groupe_sanguin and quantite and type_produit and urgence):
                messages.error(request, "Veuillez remplir tous les champs obligatoires.")
                return redirect('serviceMedicaux:faireDemandeDeSang')

            try:
                service_medical = request.user.service_medical
            except ServiceMedicaux.DoesNotExist:
                messages.error(request, "Profil de service médical introuvable pour cet utilisateur.")
                return redirect('serviceMedicaux:faireDemandeDeSang')

            # Onglet "Demande patient" si nom_patient est fourni
            patient = None
            nom_patient = request.POST.get('nom_patient', '').strip()
            if nom_patient:
                prenom_patient = request.POST.get('prenom_patient', '').strip()
                date_naissance = request.POST.get('date_naissance', '').strip()
                if not date_naissance:
                    messages.error(request, "La date de naissance du patient est obligatoire.")
                    return redirect('serviceMedicaux:faireDemandeDeSang')
                try:
                    patient = Patient.objects.create(
                        nom_complet=f"{prenom_patient} {nom_patient}".strip(),
                        date_de_naissance=date_naissance,
                        proche='',
                        groupe_sanguin=groupe_sanguin,
                        relation_proche_patient='',
                        telephone_proche='',
                    )
                except Exception as e:
                    messages.error(request, f"Erreur lors de la création du patient : {e}")
                    return redirect('serviceMedicaux:faireDemandeDeSang')

            try:
                demande = DemandeDeSang.objects.create(
                    serviceMedicaux=service_medical,
                    patient=patient,
                    groupe_sanguin={service_medical.email: [groupe_sanguin]},
                    type_produit=type_produit,
                    nombre_poches={service_medical.email: [quantite]},
                    urgence=urgence,
                    motif=motif,
                    etat_groupes={groupe_sanguin: 'En attente'},
                    notification_envoyee=False,
                )
            except Exception as e:
                messages.error(request, f"Erreur lors de l'enregistrement de la demande : {e}")
                return redirect('serviceMedicaux:faireDemandeDeSang')

            _generer_ordonnance_silencieux(demande)

            messages.success(request, 'Votre demande a été enregistrée avec succès.')
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
            _generer_ordonnance_silencieux(demande)
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
            _generer_ordonnance_silencieux(demande)
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


@login_required
@check_role('medical')
def carteBanques(request):
    response = render(request, 'frontend/serviceMedicaux/carte_banques_de_sang.html', {
        'banques': BanqueDeSang.donnees_carte(),
    })
    # Les serveurs de tuiles OpenStreetMap exigent un en-tête Referer. La politique
    # globale 'same-origin' le supprime en cross-origin ; on transmet l'origine
    # (sans le chemin) uniquement pour cette page.
    response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    return response
