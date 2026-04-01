from django.urls import path
from . import views

app_name = 'donneur'

urlpatterns = [
    path('', views.accueilDonneur, name='accueilDonneur'),
]