from django.urls import path
from . import views

app_name = 'bankDeSang'

urlpatterns = [
    path('', views.accueilBankDeSang, name='accueilBankDeSang'),
    path('listeDemandesDeSang/', views.listeDemandesDeSang, name='listeDemandesDeSang'),
    path('historiqueDemandes/', views.historiqueDemandesDeSang, name='historiqueDemandes'),
    path('accepterDemande', views.accepter_demande, name='accepterDemande'),
    # path('traiterDemande/<int:demande_id>/', views.traiter_demande, name='traiterDemande'),
    # path('refuserDemande/<int:demande_id>/<str:groupe_sang>/', views.refuser_demande, name='refuserDemande'),
    path('refuserDemande/', views.refuser_demande, name='refuserDemande'),
    path('listeDonneurs/', views.listeDonneurs, name='listeDonneurs'),
    path('donneurMonetaire/', views.donneurMonetaire, name='donneurMonetaire'),
    path('gestionStock/', views.gestionStock, name='gestionStock'),
    path('detailStock/<int:stock_id>/', views.detailStock, name='detailStock'),
    path('statistiques/', views.statistiques, name='statistiques'),
    path('poches_disponibles/', views.poches_disponibles, name='poches_disponibles'),
]