from django.shortcuts import render
from _auth.models import Donneur

# Create your views here.

# @donneurLogin
def accueilDonneur(request):
    return render(request, 'frontend/donneur/accueil_donneur.html')

def listeDonneur(request):
    donneurs = Donneur.objects.all()
    return render(request, 'frontend/donneur/liste_donneur.html', {'donneurs': donneurs})