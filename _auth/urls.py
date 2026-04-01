from django.urls import path
from . import views

app_name = '_auth'

urlpatterns = [
    path('login/', views.logIn, name='login'),
    path('register/', views.register, name='register'),
    path('activate/<uidb64>/<token>', views.activate, name='activate'),

    path('logout/', views.logOut, name='logout'),
    #path('', views.accueilServiceMedicaux, name='accueilServiceMedicaux'),
    path('inscriptionServiceMedicaux/', views.inscriptionServiceMedicaux, name='inscriptionServiceMedicaux'),
    # path('authentification/', views.authentification, name='authentification'),
    path('deconnexion/', views.logoutServiceMedicaux, name='deconnexion'),

    # path('profile/', views.profile, name='profile'),
    # path('donateur/', views.donateur, name='donateur'),
    # path('donateur/<int:donateur_id>/', views.donateur_detail, name='donateur_detail'),
    # path('donateur/<int:donateur_id>/edit/', views.donateur_edit, name='donateur_edit'),
    # path('donateur/<int:donateur_id>/delete/', views.donateur_delete, name='donateur_delete'),
    # path('donateur/<int:donateur_id>/don/', views.donateur_don, name='donateur_don'),
    # path('donateur/<int:donateur_id>/don/<int:don_id>/', views.donateur_don_detail, name='donateur_don_detail'),
    # path('donateur/<int:donateur_id>/don/<int:don_id>/edit/', views.donateur_don_edit, name='donateur_don_edit'),
    # path('donateur/<int:donateur_id>/don/<int:don_id>/delete/', views.donateur_don_delete, name='donateur_don_delete'),
    # path('donateur/<int:donateur_id>/don/<int:don_id>/validate/', views.donateur_don_validate, name='donateur_don_validate'),
    # path('donateur/<int:donateur_id>/don/<int:don_id>/cancel/', views.donateur_don_cancel, name='donateur_don_cancel'),
    
]