import calendar
from datetime import date

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from _auth.models import Donneur, BanqueDeSang
from decorateurs import check_role
from donneur.models import RendezVousDon, CRENEAUX


@login_required
@check_role('donor')
def accueilDonneur(request):
    donneur = request.user.donneur
    rdv = RendezVousDon.objects.filter(donneur=donneur).select_related('banque')
    aujourd_hui = date.today()
    rdv_a_venir = [r for r in rdv if r.statut == 'Planifié' and r.date >= aujourd_hui]
    rdv_passes = [r for r in rdv if r.statut == 'Effectué' or r.date < aujourd_hui]
    return render(request, 'frontend/donneur/accueil_donneur.html', {
        'rdv_a_venir': rdv_a_venir,
        'rdv_passes': rdv_passes,
    })


@login_required
@check_role('donor')
def listeDonneur(request):
    donneurs = Donneur.objects.all()
    return render(request, 'frontend/donneur/liste_donneur.html', {'donneurs': donneurs})


@login_required
@check_role('donor')
def planifierDon(request):
    """Calendrier mensuel + sélection banque/créneau pour planifier un don."""
    creneaux_valides = [c for c, _ in CRENEAUX]

    if request.method == 'POST':
        banque_id = request.POST.get('banque_id', '')
        date_str = request.POST.get('date', '').strip()
        creneau = request.POST.get('creneau', '').strip()

        banque = BanqueDeSang.objects.filter(id=banque_id).first()
        try:
            date_rdv = date.fromisoformat(date_str)
        except ValueError:
            date_rdv = None

        if banque is None:
            messages.error(request, "Veuillez choisir une banque de sang valide.")
        elif date_rdv is None:
            messages.error(request, "Veuillez choisir une date valide sur le calendrier.")
        elif date_rdv < date.today():
            messages.error(request, "La date choisie est déjà passée.")
        elif creneau not in creneaux_valides:
            messages.error(request, "Veuillez choisir un créneau horaire.")
        else:
            RendezVousDon.objects.create(
                donneur=request.user.donneur, banque=banque,
                date=date_rdv, creneau=creneau,
            )
            messages.success(request, "Votre rendez-vous de don a été planifié avec succès.")
            return redirect('donneur:accueilDonneur')
        return redirect('donneur:planifierDon')

    # GET : construction de la grille du mois
    aujourd_hui = date.today()
    try:
        annee = int(request.GET.get('annee', aujourd_hui.year))
        mois = int(request.GET.get('mois', aujourd_hui.month))
    except (TypeError, ValueError):
        annee, mois = aujourd_hui.year, aujourd_hui.month
    if not 1 <= mois <= 12:
        annee, mois = aujourd_hui.year, aujourd_hui.month

    cal = calendar.Calendar(firstweekday=0)  # 0 = lundi
    semaines = cal.monthdatescalendar(annee, mois)

    mois_precedent = (annee - 1, 12) if mois == 1 else (annee, mois - 1)
    mois_suivant = (annee + 1, 1) if mois == 12 else (annee, mois + 1)

    noms_mois = ['', 'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
                 'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre']

    return render(request, 'frontend/donneur/planifier_don.html', {
        'semaines': semaines,
        'annee': annee,
        'mois': mois,
        'nom_mois': noms_mois[mois],
        'mois_courant': mois,
        'aujourd_hui': aujourd_hui,
        'mois_precedent': mois_precedent,
        'mois_suivant': mois_suivant,
        'banques': BanqueDeSang.objects.all(),
        'creneaux': CRENEAUX,
    })


@login_required
@check_role('donor')
def annulerRendezVous(request, rdv_id):
    """Annule un rendez-vous appartenant au donneur connecté."""
    if request.method != 'POST':
        return redirect('donneur:accueilDonneur')
    rdv = get_object_or_404(RendezVousDon, id=rdv_id, donneur=request.user.donneur)
    rdv.statut = 'Annulé'
    rdv.save()
    messages.success(request, "Votre rendez-vous a été annulé.")
    return redirect('donneur:accueilDonneur')
