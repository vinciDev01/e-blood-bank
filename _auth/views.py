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


# ---------- Registration ----------

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


# ---------- Login with 2FA OTP ----------

def logIn(request):
    if request.method == 'POST':
        username = request.POST.get('email')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is None or not user.is_active:
            messages.error(request, 'Nom d\'utilisateur ou mot de passe incorrect')
            return redirect('_auth:login')

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

            if user.role == 'admin' or user.is_superuser:
                return redirect('_auth:administrationDashboard')

            role_redirects = {
                'medical': 'serviceMedicaux:accueilServiceMedicaux',
                'generic': 'frontend:accueil',
                'donor': 'donneur:accueilDonneur',
                'blood_bank': 'bankDeSang:accueilBankDeSang',
            }
            return redirect(role_redirects.get(user.role, 'frontend:accueil'))
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


# ---------- Logout ----------

def logOut(request):
    logout(request)
    messages.success(request, 'Vous avez bien ete deconnecte')
    return redirect('_auth:login')


# ---------- Email activation ----------

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


# ---------- Password reset ----------

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


# ---------- Administration (custom admin interface) ----------

@login_required(login_url='/_auth/login/')
@check_role('admin')
def administrationDashboard(request):
    banques = BanqueDeSang.objects.select_related('user').order_by('nom_etablissement')
    services = ServiceMedicaux.objects.select_related('user').order_by('nom_etablissement')
    return render(request, 'auth/administration/dashboard.html', {
        'banques': banques,
        'services': services,
        'nb_banques': banques.count(),
        'nb_services': services.count(),
        'nb_utilisateurs': CustomUser.objects.count(),
    })


@login_required(login_url='/_auth/login/')
@check_role('admin')
def creerBanqueDeSang(request):
    if request.method == 'POST':
        nom_etablissement = request.POST.get('nom_etablissement', '').strip()
        responsable = request.POST.get('responsable', '').strip()
        email = request.POST.get('email', '').strip().lower()
        adresse = request.POST.get('adresse', '').strip()
        ville = request.POST.get('ville', '').strip()
        code_postal = request.POST.get('code_postal', '').strip()
        pays = request.POST.get('pays', '').strip()
        telephone = request.POST.get('telephone', '').strip()

        if not all([nom_etablissement, responsable, email, adresse, ville, code_postal, pays, telephone]):
            messages.error(request, 'Tous les champs sont obligatoires.')
            return redirect('_auth:creerBanqueDeSang')

        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, 'Cet email est déjà associé à un compte.')
            return redirect('_auth:creerBanqueDeSang')

        password = generate_random_password()

        user = CustomUser.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=nom_etablissement,
            last_name=responsable,
            role='blood_bank',
        )
        user.is_active = True
        user.save()

        BanqueDeSang.objects.create(
            user=user,
            nom_etablissement=nom_etablissement,
            responsable=responsable,
            adresse=adresse,
            ville=ville,
            code_postal=code_postal,
            pays=pays,
            telephone=telephone,
        )

        current_site = get_current_site(request)
        html_message = render_to_string('auth/users/creationBanqueMail.html', {
            'nom_etablissement': nom_etablissement,
            'responsable': responsable,
            'email': email,
            'password': password,
            'domain': current_site.domain,
        })
        try:
            send_html_email(
                'Votre compte eBloodBank a été créé',
                html_message,
                email,
            )
            messages.success(request, f'Banque de sang « {nom_etablissement} » créée avec succès. Les identifiants ont été envoyés à {email}.')
        except Exception as e:
            print(f"Erreur envoi email creation banque: {e}")
            messages.warning(request, f'Compte créé, mais l\'email n\'a pas pu être envoyé. Mot de passe temporaire : {password}')

        return redirect('_auth:administrationDashboard')

    return render(request, 'auth/administration/creerBanque.html')


# ---------- ServiceMedicaux registration ----------

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
