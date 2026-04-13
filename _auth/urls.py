from django.urls import path
from . import views

app_name = '_auth'

urlpatterns = [
    path('login/', views.logIn, name='login'),
    path('register/', views.register, name='register'),
    path('activate/<uidb64>/<token>', views.activate, name='activate'),
    path('logout/', views.logOut, name='logout'),

    # Verification OTP (2FA)
    path('verifyOTP/', views.verifyOTP, name='verifyOTP'),
    path('resendOTP/', views.resendOTP, name='resendOTP'),

    # Reinitialisation de mot de passe
    path('resetPassword/', views.resetPassword, name='resetPassword'),
    path('resetPasswordEmail/', views.resetPasswordEmail, name='resetPasswordEmail'),
    path('resetPasswordConfirm/<uidb64>/<token>/', views.resetPasswordConfirm, name='resetPasswordConfirm'),

    # Services Medicaux
    path('inscriptionServiceMedicaux/', views.inscriptionServiceMedicaux, name='inscriptionServiceMedicaux'),
    path('deconnexion/', views.logoutServiceMedicaux, name='deconnexion'),

    # Administration (custom admin interface)
    path('administration/', views.administrationDashboard, name='administrationDashboard'),
    path('administration/utilisateurs/creer/', views.creerUtilisateur, name='creerUtilisateur'),
]