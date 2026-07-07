from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils.encoding import force_bytes, force_str
from django.template.loader import render_to_string
from django.contrib.sites.shortcuts import get_current_site
from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.core.mail import send_mail
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from datetime import timedelta
import secrets
import string

from .models import CustomUser, Utilisateur, ServiceMedicaux, BanqueDeSang, OTPCode
from .token import generatorToken
from decorateurs import check_role


def generate_random_password(length=12):
    alphabet = string.ascii_letters + string.digits + '!@#$%&*'
    while True:
        pwd = ''.join(secrets.choice(alphabet) for _ in range(length))
        if (any(c.islower() for c in pwd) and any(c.isupper() for c in pwd)
                and any(c.isdigit() for c in pwd)):
            return pwd


def send_html_email(subject, html_message, recipient_email):
    send_mail(
        subject=subject,
        message='',
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=[recipient_email],
        html_message=html_message,
        fail_silently=False,
    )


#  Registration 
def register(request):
    if request.method == 'POST':
        firstname = request.POST['firstName']
        lastname = request.POST['lastName']
        email = request.POST['email']
        password = request.POST['password']
        confirmPassword = request.POST['confirmPassword']
        if password == confirmPassword:
            if CustomUser.objects.filter(email=email).exists():
                messages.error(request, 'Cet email est deja associe a un compte')
                return redirect('_auth:register')
            else:
                user = CustomUser.objects.create_user(
                    username=email,
                    email=email,
                    password=password,
                    first_name=firstname,
                    last_name=lastname,
                    role='generic',
                )

                utilisateur = Utilisateur(
                    user=user,
                    nom=firstname,
                    prenom=lastname,
                    email=email,
                )
                user.is_active = False
                user.save()
                utilisateur.save()

                current_site = get_current_site(request)
                mail_subject = 'Activation de votre compte - eBloodBank'
                message = render_to_string('auth/users/activationMail.html', {
                    'user': user,
                    'domain': current_site.domain,
                    'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                    'token': generatorToken.make_token(user),
                })
                try:
                    send_html_email(mail_subject, message, email)
                except Exception as e:
                    print(f"Erreur envoi email activation: {e}")

                messages.success(request, 'Un email de confirmation a ete envoye a votre adresse email')
                return redirect('_auth:login')
        else:
            messages.error(request, 'Les mots de passe ne correspondent pas')
            return redirect('_auth:register')
    else:
        return render(request, 'auth/users/register.html')


#  Login with 2FA OTP 
def _rediriger_apres_login(user):
    """Redirection vers le tableau de bord correspondant au rôle de l'utilisateur."""
    if user.role == 'admin' or user.is_superuser:
        return redirect('_auth:administrationDashboard')

    role_redirects = {
        'medical': 'serviceMedicaux:accueilServiceMedicaux',
        'generic': 'frontend:accueil',
        'donor': 'donneur:accueilDonneur',
        'blood_bank': 'bankDeSang:accueilBankDeSang',
    }
    return redirect(role_redirects.get(user.role, 'frontend:accueil'))


def logIn(request):
    if request.method == 'POST':
        username = request.POST.get('email')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is None or not user.is_active:
            messages.error(request, 'Nom d\'utilisateur ou mot de passe incorrect')
            return redirect('_auth:login')

        # OTP désactivé (test/dev) : connexion directe, sans code ni email.
        if not getattr(settings, 'OTP_ENABLED', True):
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            return _rediriger_apres_login(user)

        # Invalidate previous unused OTP codes
        OTPCode.objects.filter(user=user, is_used=False).update(is_used=True)

        # Generate new OTP
        code = OTPCode.generate_code()
        OTPCode.objects.create(
            user=user,
            code=code,
            expires_at=timezone.now() + timedelta(minutes=5),
        )

        # Send OTP email
        html_message = render_to_string('auth/users/otpMail.html', {
            'user': user,
            'otp_code': code,
        })
        try:
            send_html_email('Votre code de verification - eBloodBank', html_message, user.email)
        except Exception as e:
            print(f"Erreur envoi OTP: {e}")

        # Store user ID in session (NOT logged in yet)
        request.session['otp_user_id'] = user.pk

        messages.success(request, 'Un code de verification a ete envoye a votre adresse email')
        return redirect('_auth:verifyOTP')

    return render(request, 'auth/users/login.html')


def verifyOTP(request):
    user_id = request.session.get('otp_user_id')
    if not user_id:
        messages.error(request, 'Session expiree. Veuillez vous reconnecter.')
        return redirect('_auth:login')

    if request.method == 'POST':
        otp_code = request.POST.get('otp_code', '').strip()

        try:
            user = CustomUser.objects.get(pk=user_id)
        except CustomUser.DoesNotExist:
            messages.error(request, 'Utilisateur introuvable.')
            return redirect('_auth:login')

        otp = OTPCode.objects.filter(
            user=user,
            code=otp_code,
            is_used=False,
            expires_at__gt=timezone.now(),
        ).order_by('-created_at').first()

        if otp:
            otp.is_used = True
            otp.save()

            del request.session['otp_user_id']

            login(request, user, backend='django.contrib.auth.backends.ModelBackend')

            return _rediriger_apres_login(user)
        else:
            messages.error(request, 'Code invalide ou expire. Veuillez reessayer.')
            return redirect('_auth:verifyOTP')

    return render(request, 'auth/users/verifyOTP.html')


def resendOTP(request):
    user_id = request.session.get('otp_user_id')
    if not user_id:
        return redirect('_auth:login')

    try:
        user = CustomUser.objects.get(pk=user_id)
    except CustomUser.DoesNotExist:
        return redirect('_auth:login')

    OTPCode.objects.filter(user=user, is_used=False).update(is_used=True)

    code = OTPCode.generate_code()
    OTPCode.objects.create(
        user=user,
        code=code,
        expires_at=timezone.now() + timedelta(minutes=5),
    )

    html_message = render_to_string('auth/users/otpMail.html', {
        'user': user,
        'otp_code': code,
    })
    try:
        send_html_email('Votre code de verification - eBloodBank', html_message, user.email)
    except Exception as e:
        print(f"Erreur renvoi OTP: {e}")

    messages.success(request, 'Un nouveau code a ete envoye.')
    return redirect('_auth:verifyOTP')


#  Logout 
def logOut(request):
    logout(request)
    messages.success(request, 'Vous avez bien ete deconnecte')
    return redirect('_auth:login')


#  Email activation 
def activate(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = CustomUser.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
        user = None

    if user is not None and generatorToken.check_token(user, token):
        user.is_active = True
        user.save()
        messages.success(request, 'Felicitations, connectez-vous pour commencer a utiliser votre compte')
        return redirect('_auth:login')
    else:
        messages.error(request, 'Le lien d\'activation est invalide. Veuillez vous inscrire a nouveau.')
        return redirect('frontend:accueil')


#  Password reset 
def resetPassword(request):
    return render(request, 'auth/users/resetPassword.html')


def resetPasswordEmail(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        user = CustomUser.objects.filter(email=email).first()
        if user is not None:
            current_site = get_current_site(request)
            mail_subject = 'Reinitialisation de votre mot de passe - eBloodBank'
            message = render_to_string('auth/users/resetPasswordMail.html', {
                'user': user,
                'domain': current_site.domain,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': generatorToken.make_token(user),
            })
            try:
                send_html_email(mail_subject, message, email)
            except Exception as e:
                print(f"Erreur envoi email reset: {e}")
        messages.success(request, 'Si cette adresse est associee a un compte, un email de reinitialisation a ete envoye.')
        return redirect('_auth:login')
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
                messages.success(request, 'Votre mot de passe a ete reinitialise avec succes')
                return redirect('_auth:login')
            else:
                messages.error(request, 'Les mots de passe ne correspondent pas')
                return redirect('_auth:resetPasswordConfirm', uidb64=uidb64, token=token)
        return render(request, 'auth/users/resetPasswordConfirm.html')
    else:
        messages.error(request, 'Le lien de reinitialisation est invalide.')
        return redirect('frontend:accueil')


#  Administration (custom admin interface) 
ROLE_LABELS = {
    'blood_bank': 'Banque de sang',
    'medical': 'Service médical',
    'donor': 'Donneur',
    'admin': 'Administrateur',
    'generic': 'Utilisateur générique',
}


@login_required(login_url='/_auth/login/')
@check_role('admin')
def administrationDashboard(request):
    from .models import Donneur

    banques = BanqueDeSang.objects.select_related('user').order_by('nom_etablissement')
    services = ServiceMedicaux.objects.select_related('user').order_by('nom_etablissement')
    donneurs = Donneur.objects.select_related('user').order_by('nom', 'prenom')[:50]
    admins = CustomUser.objects.filter(role='admin').order_by('email')
    generics = CustomUser.objects.filter(role='generic').exclude(banque_de_sang__isnull=False).exclude(service_medical__isnull=False).exclude(donneur__isnull=False).order_by('email')

    return render(request, 'auth/administration/dashboard.html', {
        'banques': banques,
        'services': services,
        'donneurs': donneurs,
        'admins': admins,
        'generics': generics,
        'nb_banques': banques.count(),
        'nb_services': services.count(),
        'nb_donneurs': Donneur.objects.count(),
        'nb_admins': admins.count(),
        'nb_generics': generics.count(),
        'nb_utilisateurs': CustomUser.objects.count(),
    })


@login_required(login_url='/_auth/login/')
@check_role('admin')
def creerUtilisateur(request):
    from .models import Donneur
    from datetime import datetime

    role = request.GET.get('role') or request.POST.get('role', 'blood_bank')
    if role not in ROLE_LABELS:
        role = 'blood_bank'

    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()

        if not email:
            messages.error(request, 'L\'adresse email est obligatoire.')
            return redirect(f"{request.path}?role={role}")

        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, 'Cet email est déjà associé à un compte.')
            return redirect(f"{request.path}?role={role}")

        try:
            if role == 'blood_bank':
                required = ['nom_etablissement', 'responsable', 'adresse', 'ville', 'code_postal', 'pays', 'telephone']
                data = {f: request.POST.get(f, '').strip() for f in required}
                if not all(data.values()):
                    raise ValueError('Tous les champs sont obligatoires.')
                password = generate_random_password()
                user = CustomUser.objects.create_user(
                    username=email, email=email, password=password,
                    first_name=data['nom_etablissement'], last_name=data['responsable'],
                    role='blood_bank',
                )
                user.is_active = True
                user.save()
                BanqueDeSang.objects.create(user=user, **data)
                display_name = data['nom_etablissement']

            elif role == 'medical':
                required = ['nom_etablissement', 'type_etablissement', 'responsable', 'adresse', 'ville', 'code_postal', 'pays', 'telephone', 'numero_licence', 'numero_enregistrement']
                data = {f: request.POST.get(f, '').strip() for f in required}
                if not all(data.values()):
                    raise ValueError('Tous les champs sont obligatoires.')
                password = generate_random_password()
                user = CustomUser.objects.create_user(
                    username=email, email=email, password=password,
                    first_name=data['nom_etablissement'], last_name=data['responsable'],
                    role='medical',
                )
                user.is_active = True
                user.save()
                ServiceMedicaux.objects.create(user=user, email=email, **data)
                display_name = data['nom_etablissement']

            elif role == 'donor':
                required = ['nom', 'prenom', 'date_naissance', 'sexe', 'groupe_sanguin', 'adresse', 'ville', 'code_postal', 'pays', 'telephone']
                data = {f: request.POST.get(f, '').strip() for f in required}
                if not all(data.values()):
                    raise ValueError('Tous les champs sont obligatoires.')
                data['date_naissance'] = datetime.strptime(data['date_naissance'], '%Y-%m-%d').date()
                password = generate_random_password()
                user = CustomUser.objects.create_user(
                    username=email, email=email, password=password,
                    first_name=data['prenom'], last_name=data['nom'],
                    role='donor',
                )
                user.is_active = True
                user.save()
                Donneur.objects.create(user=user, **data)
                display_name = f"{data['prenom']} {data['nom']}"

            elif role in ('admin', 'generic'):
                first_name = request.POST.get('first_name', '').strip()
                last_name = request.POST.get('last_name', '').strip()
                if not first_name or not last_name:
                    raise ValueError('Prénom et nom sont obligatoires.')
                password = generate_random_password()
                user = CustomUser.objects.create_user(
                    username=email, email=email, password=password,
                    first_name=first_name, last_name=last_name,
                    role=role,
                )
                user.is_active = True
                if role == 'admin':
                    user.is_staff = True
                    user.is_superuser = True
                user.save()
                Utilisateur.objects.create(
                    user=user, nom=first_name, prenom=last_name, email=email,
                )
                display_name = f"{first_name} {last_name}"

        except ValueError as ve:
            messages.error(request, str(ve))
            return redirect(f"{request.path}?role={role}")
        except Exception as e:
            print(f"Erreur creation utilisateur ({role}): {e}")
            messages.error(request, f"Erreur lors de la création : {e}")
            return redirect(f"{request.path}?role={role}")

        current_site = get_current_site(request)
        html_message = render_to_string('auth/users/creationUtilisateurMail.html', {
            'display_name': display_name,
            'role_label': ROLE_LABELS[role],
            'email': email,
            'password': password,
            'domain': current_site.domain,
        })
        try:
            send_html_email('Votre compte eBloodBank a été créé', html_message, email)
            messages.success(request, f'{ROLE_LABELS[role]} « {display_name} » créé avec succès. Les identifiants ont été envoyés à {email}.')
        except Exception as e:
            print(f"Erreur envoi email: {e}")
            messages.warning(request, f'Compte créé, mais l\'email n\'a pas pu être envoyé. Mot de passe temporaire : {password}')

        return redirect('_auth:administrationDashboard')

    from .models import Donneur as DM
    return render(request, 'auth/administration/creerUtilisateur.html', {
        'role': role,
        'role_label': ROLE_LABELS.get(role, 'Utilisateur'),
        'groupes_sanguins': DM.groupe_sanguin_choices,
    })


#  ServiceMedicaux registration 
def inscriptionServiceMedicaux(request):
    if request.method == 'POST':
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

        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, 'Cet email est deja associe a un compte')
            return redirect('_auth:inscriptionServiceMedicaux')
        else:
            user = CustomUser.objects.create_user(
                username=email,
                first_name=nom_etablissement,
                last_name=responsable,
                email=email,
                password=password,
                role='medical',
            )
            user.save()

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
                certificat_enregistrement=certificat_enregistrement,
            )
            serviceMedicaux.save()

            return redirect('_auth:login')
    return render(request, 'auth/serviceMedicaux/inscriptionServiceMedicaux.html')


def logoutServiceMedicaux(request):
    logout(request)
    messages.success(request, 'Vous avez bien ete deconnecte')
    return redirect('_auth:login')
