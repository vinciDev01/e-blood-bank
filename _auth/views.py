from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils.encoding import force_bytes, force_str
from django.template.loader import render_to_string
from django.contrib.sites.shortcuts import get_current_site
from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from .models import CustomUser, Utilisateur, ServiceMedicaux

from .token import generatorToken

# User registration
def register(request):
    if request.method == 'POST':
        firstname = request.POST['firstName']
        lastname = request.POST['lastName']
        email = request.POST['email']
        password = request.POST['password']
        confirmPassword = request.POST['confirmPassword']
        if password == confirmPassword:
            if CustomUser.objects.filter(email=email).exists():
                messages.error(request, 'Cet email est déjà associé à un compte')
                return redirect('_auth:register')
            else:
                user = CustomUser.objects.create_user(
                    username=email,
                    email=email,
                    password=password,
                    first_name=firstname,
                    last_name=lastname,
                    role='generic'  # ou un autre rôle selon vos besoins
                )
                
                utilisateur = Utilisateur(
                    user=user,
                    nom=firstname,
                    prenom=lastname,
                    email=email
                )
                user.is_active = False
                user.save()
                utilisateur.save()

                current_site = get_current_site(request)
                mail_subject = 'Activation de votre compte'
                message = render_to_string('auth/users/activationMail.html', {
                    'user': user,
                    'domain': current_site.domain,
                    'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                    'token': generatorToken.make_token(user)
                })
                try:
                    msg = MIMEMultipart()
                    msg['From'] = settings.EMAIL_HOST_USER
                    msg['To'] = email
                    msg['Subject'] = mail_subject
                    msg.attach(MIMEText(message, 'html'))
                    with smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT) as server:
                        server.starttls()
                        server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
                        server.sendmail(settings.EMAIL_HOST_USER, email, msg.as_string())
                        #print("Email Sent Successfully")
                except Exception as e:
                    print(f"Error: {e}")
                    
                messages.success(request, 'Un email de confirmation a été envoyé à votre adresse email')
                return redirect('_auth:login')
            
        else:
            messages.error(request, 'Les mots de passe ne correspondent pas')
            return redirect('_auth:register')
    else:
        return render(request, 'auth/users/register.html')

def logIn(request):
    if request.method == 'POST':
        username = request.POST.get('email')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is None or not user.is_active:
            messages.error(request, 'Nom d\'utilisateur ou mot de passe incorrect')
            return redirect('_auth:login')

        login(request, user)

        role_redirects = {
            'medical': 'serviceMedicaux:accueilServiceMedicaux',
            'generic': 'frontend:accueil',
            'donor': 'donneur:accueilDonneur',
            'blood_bank': 'bankDeSang:accueilBankDeSang',
            'admin': 'frontend:accueil',
        }
        redirect_url = role_redirects.get(user.role, 'frontend:accueil')
        return redirect(redirect_url)

    return render(request, 'auth/users/login.html')

def logOut(request):
    logout(request)
    messages.success(request, 'Vous avez bien été déconnecté')
    return redirect('_auth:login')

def activate(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = CustomUser.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
        user = None

    if user is not None and generatorToken.check_token(user, token):
        user.is_active = True
        user.save()
        messages.success(request, 'Félicitation, connectez-vous pour commencer à utiliser votre compte')
        return redirect('_auth:login')
    else:
        messages.error(request, 'Le lien d\'activation est invalide\n Activation echoué Veuillez vous inscrire à nouveau')
        return redirect('frontend:accueil')

def resetPassword(request):
    return render(request, 'auth/users/resetPassword.html')

def resetPasswordEmail(request):
    if request.method == 'POST':
        email = request.POST['email']
        if CustomUser.objects.filter(email=email).exists():
            user = CustomUser.objects.get(email=email)
            current_site = get_current_site(request)
            mail_subject = 'Réinitialisation de votre mot de passe'
            message = render_to_string('auth/users/resetPasswordMail.html', {
                'user': user,
                'domain': current_site.domain,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': generatorToken.make_token(user)
            })
            try:
                msg = MIMEMultipart()
                msg['From'] = settings.EMAIL_HOST_USER
                msg['To'] = email
                msg['Subject'] = mail_subject
                msg.attach(MIMEText(message, 'html'))
                with smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT) as server:
                    server.starttls()
                    server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
                    server.sendmail(settings.EMAIL_HOST_USER, email, msg.as_string())
            except Exception as e:
                print(f"Error: {e}")
            messages.success(request, 'Un email de réinitialisation de mot de passe a été envoyé à votre adresse email')
            return redirect('_auth:login')
        else:
            messages.error(request, 'Cet email n\'existe pas')
            return redirect('_auth:resetPassword')
    return render(request, 'auth/users/resetPassword.html')

def resetPasswordConfirm(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = CustomUser.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
        user = None

    if user is not None and generatorToken.check_token(user, token):
        if request.method == 'POST':
            password = request.POST['password']
            confirmPassword = request.POST['confirmPassword']
            if password == confirmPassword:
                user.set_password(password)
                user.save()
                messages.success(request, 'Votre mot de passe a été réinitialisé avec succès')
                return redirect('_auth:login')
            else:
                messages.error(request, 'Les mots de passe ne correspondent pas')
                return redirect('_auth:resetPasswordConfirm', uidb64=uidb64, token=token)
        return render(request, 'auth/users/resetPasswordConfirm.html')
    else:
        messages.error(request, 'Le lien de réinitialisation de mot de passe est invalide\n Réinitialisation echoué')
        return redirect('frontend:accueil')
    
def forgotPassword(request):
    return render(request, 'auth/users/forgotPassword.html')




# ServiceMedicaux registration

def inscriptionServiceMedicaux(request):
    if request.method == 'POST':
        # Récupération des données du formulaire
        nom_etablissement = request.POST['nom_etablissement']
        type_etablissement = request.POST.get('type_etablissement', None)
        responsable = request.POST['responsable']
        adresse = request.POST['adresse']
        ville = request.POST['ville']
        code_postal = request.POST['code_postal']
        pays = request.POST['pays']
        telephone = request.POST['telephone']
        email = request.POST['email']
        numero_licence = request.POST['numero_licence']
        numero_enregistrement = request.POST['numero_enregistrement']
        certificat_enregistrement = request.FILES.get('certificat_enregistrement', None)
        password = request.POST['password']

        # Vérification si l'email est déjà utilisé
        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, 'Cet email est déjà associé à un compte')
            return redirect('_auth:inscriptionServiceMedicaux')
        else:
            # Création de l'utilisateur CustomUser
            user = CustomUser.objects.create_user(
                username=email,
                first_name=nom_etablissement,
                last_name=responsable,
                email=email,
                password=password,
                role='medical'
            )
            user.save()

            # Création de l'instance ServiceMedicaux et sauvegarde dans la base de données
            serviceMedicaux = ServiceMedicaux(
                user=user,
                nom_etablissement=nom_etablissement,
                type_etablissement=type_etablissement,
                responsable=responsable,
                adresse=adresse,
                ville=ville,
                code_postal=code_postal,
                pays=pays,
                telephone=telephone,
                email=email,
                numero_licence=numero_licence,
                numero_enregistrement=numero_enregistrement,
                certificat_enregistrement=certificat_enregistrement
            )
            serviceMedicaux.save()

            return redirect('_auth:login')
    return render(request, 'auth/serviceMedicaux/inscriptionServiceMedicaux.html')

# def authentification(request):
#     if request.method == 'POST':
#         email = request.POST['email']
#         password = request.POST['password']
#         try:
#             user = CustomUser.objects.get(email=email)
#             user = authenticate(request, username=user.username, password=password)
#             if user is not None:
#                 login(request, user)
#                 return redirect('serviceMedicaux:accueilServiceMedicaux')
#             else:
#                 messages.error(request, 'Problème d\'authentification')
#         except CustomUser.DoesNotExist:
#             messages.error(request, 'Email incorrect')
#     return render(request, 'auth/serviceMedicaux/authentification.html')
    
    
    
def logoutServiceMedicaux(request):
    logout(request)
    messages.success(request, 'Vous avez bien été déconnecté')
    return redirect('_auth:login')
