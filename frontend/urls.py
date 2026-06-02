from .views import *
from django.urls import path#, include

app_name = 'frontend'

urlpatterns = [
    path('', accueil, name='accueil'),
    path('centres/', centresDeDon, name='centresDeDon'),
    path('listeHopitaux', listeHopitaux, name='listeHopitaux'),
    path('hopital/<int:id>', hopital, name='hopital'),
    path('listeDemandeDeSang', listeDemandeDeSang, name='listeDemandeDeSang'),
    # path('register', register, name='register'),
    # path('login', logIn, name='login'),
    # path('logout', logOut, name='logout'),
    # path('activate/<uidb64>/<token>', activate, name='activate'),

    # path('patientDemandeDeSang', patientDemandeDeSang, name='patientDemandeDeSang'),
    #path('serviceMedicaux/', include('serviceMedicaux.urls')),

]


