from django.urls import path
from . import views

app_name = 'serviceMedicaux'

urlpatterns = [
    path('accueil/', views.accueilServiceMedicaux, name='accueilServiceMedicaux'),
    path('mesDemandesDeSang/', views.mesDemandesDeSang, name='mesDemandesDeSang'),
    path('api/demandes/flux/', views.mes_demandes_flux, name='mesDemandesFlux'),
    path('ordonnance/<int:demande_id>/', views.telechargerOrdonnance, name='telechargerOrdonnance'),
    path('listeDemandeDeSang/', views.listeDemandeDeSang, name='listeDemandeDeSang'),
    #path('inscriptionServiceMedicaux/', views.inscriptionServiceMedicaux, name='inscriptionServiceMedicaux'),
    path('faireDemandeDeSang/', views.faireDemandeDeSang, name='faireDemandeDeSang'),
    path('recevoir_poches/', views.recevoir_poches, name='recevoir_poches'),
    path('carteBanques/', views.carteBanques, name='carteBanques'),
    # path('getToutesDemande/', views.getToutesDemande, name='getToutesDemande'),
    #path('authentification/', views.authentification, name='authentification'),
]