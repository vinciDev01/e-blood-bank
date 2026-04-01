from django.shortcuts import render
from _auth.models import Donneur
from django.contrib.auth.decorators import login_required
from decorateurs import check_role

# Create your views here.

@login_required
@check_role('donor')
def accueilDonneur(request):
    return render(request, 'frontend/donneur/accueil_donneur.html')

@login_required
@check_role('donor')
def listeDonneur(request):
    donneurs = Donneur.objects.all()
    return render(request, 'frontend/donneur/liste_donneur.html', {'donneurs': donneurs})