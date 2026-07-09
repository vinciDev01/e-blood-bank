from django.urls import path
from . import views

app_name = 'donneur'

urlpatterns = [
    path('', views.accueilDonneur, name='accueilDonneur'),
    path('planifier/', views.planifierDon, name='planifierDon'),
    path('rendezvous/<int:rdv_id>/annuler/', views.annulerRendezVous, name='annulerRendezVous'),
]