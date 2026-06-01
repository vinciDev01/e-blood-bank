from django.urls import path
from . import views

app_name = 'serviceMedicaux'

urlpatterns = [
    path('accueil/', views.accueilServiceMedicaux, name='accueilServiceMedicaux'),
    path('mesDemandesDeSang/', views.mesDemandesDeSang, name='mesDemandesDeSang'),
    path('listeDemandeDeSang/', views.listeDemandeDeSang, name='listeDemandeDeSang'),
    #path('inscriptionServiceMedicaux/', views.inscriptionServiceMedicaux, name='inscriptionServiceMedicaux'),
    path('faireDemandeDeSang/', views.faireDemandeDeSang, name='faireDemandeDeSang'),
    path('recevoir_poches/', views.recevoir_poches, name='recevoir_poches'),
    path('carteBanques/', views.carteBanques, name='carteBanques'),
    # path('getToutesDemande/', views.getToutesDemande, name='getToutesDemande'),
    #path('authentification/', views.authentification, name='authentification'),
]