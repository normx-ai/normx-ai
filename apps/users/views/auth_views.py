# -*- coding: utf-8 -*-
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import PermissionDenied
from django.conf import settings

from ..models import User, UserType
from ..forms import (
    LoginForm, VerificationCodeForm, MFAVerificationForm,
    PasswordResetRequestForm, PasswordResetConfirmForm,
    UserTypeSelectForm, CompanyRegistrationForm, AccountantRegistrationForm
)
from ..services import (
    AuthenticationService, RegistrationService, VerificationService,
    TokenService, VerificationCodeService, PasswordResetService
)

logger = logging.getLogger(__name__)

def login_view(request):
    """Vue de connexion utilisateur"""
    # Si l'utilisateur est déjà connecté, le rediriger vers sa destination
    if request.user.is_authenticated:
        messages.info(request, _("Vous êtes déjà connecté."))

        # Si next est spécifié dans l'URL, rediriger vers cette page
        next_url = request.GET.get('next')
        if next_url:
            return redirect(next_url)

        # Sinon, rediriger vers le tableau de bord
        return redirect('dashboard')

    # Debug - Afficher des informations sur la session et les cookies
    if settings.DEBUG:
        print("=" * 60)
        print("LOGIN VIEW DEBUG")
        print(f"SESSION ID: {request.session.session_key}")
        print(f"SESSION MODIFIED: {request.session.modified}")
        print(f"SESSION IS EMPTY: {request.session.is_empty()}")
        if request.method == 'POST':
            print(f"CSRF Debug: token received: {request.POST.get('csrfmiddlewaretoken')}")
            print(f"CSRF Debug: cookie value: {request.COOKIES.get('csrftoken')}")
        print("=" * 60)

    # Traitement du formulaire de connexion
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            remember = form.cleaned_data.get('remember_me', False)

            # Tentative de connexion
            user, error = AuthenticationService.login(request, email, password, remember)

            if user:
                # Gérer l'authentification à deux facteurs si activée
                if user.mfa_enabled:
                    # Stocker les informations nécessaires en session
                    request.session['mfa_user_id'] = str(user.id)
                    request.session['mfa_remember'] = remember

                    # Conserver l'URL de redirection après MFA
                    next_url = request.POST.get('next') or request.GET.get('next')
                    if next_url:
                        request.session['mfa_next'] = next_url

                    return redirect('mfa_verification')

                # Connexion standard si MFA non activée
                login(request, user)

                # Vérifier si c'est un premier accès et rediriger vers l'onboarding
                if user.user_type == UserType.COMPANY:
                    if hasattr(user, 'company_profile') and not user.company_profile.onboarding_completed:
                        return redirect('company_onboarding')
                elif user.user_type == UserType.ACCOUNTANT:
                    if hasattr(user, 'accountant_profile') and not user.accountant_profile.onboarding_completed:
                        return redirect('accountant_onboarding')

                # Redirection vers next s'il existe, sinon vers le tableau de bord
                next_url = request.POST.get('next') or request.GET.get('next')
                if next_url:
                    return redirect(next_url)
                return redirect('dashboard')
            else:
                # Afficher l'erreur d'authentification
                messages.error(request, error)
    else:
        # Création d'un nouveau formulaire
        form = LoginForm()

    # Contexte pour le template
    context = {
        'form': form,
        'next': request.GET.get('next', '')
    }

    return render(request, 'users/auth/login.html', context)

def mfa_verification_view(request):
    """Vue de vérification pour l'authentification à deux facteurs"""
    # Vérifier que l'utilisateur est en cours d'authentification MFA
    if 'mfa_user_id' not in request.session:
        return redirect('login')

    user_id = request.session.get('mfa_user_id')
    user = get_object_or_404(User, id=user_id)

    # Générer et stocker un code MFA pour le mode développement
    debug_mfa_code = None
    if settings.DEBUG:
        # Générer un code MFA fixe pour le développement
        debug_mfa_code = '123456'
        # Si l'utilisateur n'a pas de session, stocker le code
        if 'debug_mfa_code' not in request.session:
            request.session['debug_mfa_code'] = debug_mfa_code

    if request.method == 'POST':
        form = MFAVerificationForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data.get('code')

            # En mode développement, utiliser le code de debug
            if settings.DEBUG:
                is_valid = (code == request.session.get('debug_mfa_code', '123456'))
            else:
                # TODO: Implémenter la vérification réelle du code MFA
                # Pour l'instant, on simule une vérification réussie avec n'importe quel code
                is_valid = True  # À remplacer par une vérification réelle

            if is_valid:
                # Récupérer l'option "se souvenir de moi"
                remember = request.session.get('mfa_remember', False)

                # Connecter l'utilisateur
                login(request, user)

                # Récupérer l'URL de redirection, si présente
                next_url = request.session.get('mfa_next')

                # Nettoyer les données de session
                keys_to_clean = ['mfa_user_id', 'mfa_remember', 'mfa_next', 'debug_mfa_code']
                for key in keys_to_clean:
                    if key in request.session:
                        del request.session[key]

                # Gérer l'expiration de session selon l'option "se souvenir de moi"
                if remember:
                    # Session de 2 semaines
                    request.session.set_expiry(1209600)
                else:
                    # Session qui expire à la fermeture du navigateur
                    request.session.set_expiry(0)

                # Vérifier si c'est un premier accès
                if user.user_type == UserType.COMPANY:
                    if hasattr(user, 'company_profile') and not user.company_profile.onboarding_completed:
                        return redirect('company_onboarding')
                elif user.user_type == UserType.ACCOUNTANT:
                    if hasattr(user, 'accountant_profile') and not user.accountant_profile.onboarding_completed:
                        return redirect('accountant_onboarding')

                # Redirection vers next s'il existe, sinon vers le tableau de bord
                if next_url:
                    return redirect(next_url)
                return redirect('dashboard')
            else:
                messages.error(request, _("Code d'authentification invalide. Veuillez réessayer."))
    else:
        form = MFAVerificationForm()

    context = {
        'form': form
    }

    # En mode développement, afficher le code MFA dans le template
    if settings.DEBUG:
        context['debug_mfa_code'] = request.session.get('debug_mfa_code', debug_mfa_code)
        context['is_debug'] = True

    return render(request, 'users/auth/mfa_verification.html', context)

@login_required
def logout_view(request):
    """Vue de déconnexion"""
    user = request.user

    # Déconnecter l'utilisateur et nettoyer la session
    AuthenticationService.logout(request, user)
    logout(request)

    # Ajouter un message de succès
    messages.success(request, _("Vous avez été déconnecté avec succès."))

    # Nettoyer complètement la session (y compris registration_user_type)
    request.session.flush()

    # Rediriger vers la page de connexion
    return redirect('login')

def register_select_type_view(request):
    """Vue de sélection du type d'utilisateur lors de l'inscription"""
    # Debug - Affichons des informations de débogage
    print("============ REGISTER SELECT TYPE VIEW ============")
    print(f"REQUEST METHOD: {request.method}")
    print(f"USER AUTHENTICATED: {request.user.is_authenticated}")
    print(f"SESSION DATA: {request.session.items()}")

    # Si l'utilisateur est déjà connecté, l'avertir et le rediriger
    if request.user.is_authenticated:
        print("User is authenticated, redirecting to dashboard")
        # Ajouter un message d'information
        messages.info(request, _("Vous êtes déjà connecté. Déconnectez-vous pour créer un nouveau compte."))
        # Rediriger vers le tableau de bord
        return redirect('dashboard')

    # Nettoyer les anciennes données d'inscription en session
    # (au cas où l'utilisateur aurait abandonné une inscription précédente)
    if 'registration_user_type' in request.session:
        del request.session['registration_user_type']

    if request.method == 'POST':
        print(f"POST DATA: {request.POST}")
        form = UserTypeSelectForm(request.POST)
        if form.is_valid():
            user_type = form.cleaned_data.get('user_type')
            request.session['registration_user_type'] = user_type
            print(f"Form is valid, user_type selected: {user_type}")

            if user_type == UserType.COMPANY:
                print("Redirecting to register_company")
                return redirect('register_company')
            else:
                print("Redirecting to register_accountant")
                return redirect('register_accountant')
        else:
            print(f"Form is invalid, errors: {form.errors}")
    else:
        print("Creating an empty form")
        form = UserTypeSelectForm()

    print(f"Rendering register_select_type template with form: {form}")
    return render(request, 'users/auth/register_select_type.html', {'form': form})

def register_company_view(request):
    """Vue d'inscription pour les entreprises"""
    # Si l'utilisateur est déjà connecté, l'avertir et le rediriger
    if request.user.is_authenticated:
        messages.info(request, _("Vous êtes déjà connecté. Déconnectez-vous pour créer un nouveau compte."))
        return redirect('dashboard')

    # Debug - Afficher le token CSRF reçu
    if settings.DEBUG and request.method == 'POST':
        print(f"CSRF Debug: token received: {request.POST.get('csrfmiddlewaretoken')}")
        print(f"CSRF Debug: cookie value: {request.COOKIES.get('csrftoken')}")

    # Vérifier que le type d'utilisateur a été sélectionné correctement
    if 'registration_user_type' not in request.session or request.session['registration_user_type'] != UserType.COMPANY:
        # Rediriger vers la page de sélection
        return redirect('register_select_type')

    if request.method == 'POST':
        form = CompanyRegistrationForm(request.POST)
        if form.is_valid():
            # Récupérer les données du formulaire
            registration_data = form.cleaned_data

            # Appeler le service d'inscription
            user, error = RegistrationService.register_company(registration_data)

            if user:
                # Générer et envoyer le code de vérification
                verification_code = VerificationService.generate_verification_code()

                # Stocker le code en session pour la vérification ultérieure
                request.session['verification_user_id'] = str(user.id)
                request.session['verification_code'] = verification_code
                request.session['verification_timestamp'] = timezone.now().isoformat()

                # Envoyer le code par email
                success = VerificationCodeService.send_verification_code(user, verification_code)

                # En mode développement, afficher le code dans un message
                if settings.DEBUG:
                    messages.info(request, _(f"Code de vérification généré: {verification_code}"))

                # Rediriger vers la page de vérification
                return redirect('verify_email')
            else:
                messages.error(request, error)
    else:
        form = CompanyRegistrationForm()

    return render(request, 'users/auth/register.html', {
        'form': form,
        'user_type': UserType.COMPANY,
        'user_type_display': UserType.COMPANY.label
    })

def register_accountant_view(request):
    """Vue d'inscription pour les experts-comptables"""
    # Si l'utilisateur est déjà connecté, l'avertir et le rediriger
    if request.user.is_authenticated:
        messages.info(request, _("Vous êtes déjà connecté. Déconnectez-vous pour créer un nouveau compte."))
        return redirect('dashboard')

    # Debug - Afficher le token CSRF reçu
    if settings.DEBUG and request.method == 'POST':
        print(f"CSRF Debug: token received: {request.POST.get('csrfmiddlewaretoken')}")
        print(f"CSRF Debug: cookie value: {request.COOKIES.get('csrftoken')}")

    # Vérifier que le type d'utilisateur a été sélectionné correctement
    if 'registration_user_type' not in request.session or request.session['registration_user_type'] != UserType.ACCOUNTANT:
        # Rediriger vers la page de sélection
        return redirect('register_select_type')

    if request.method == 'POST':
        form = AccountantRegistrationForm(request.POST)
        if form.is_valid():
            # Récupérer les données du formulaire
            registration_data = form.cleaned_data

            # Appeler le service d'inscription
            user, error = RegistrationService.register_accountant(registration_data)

            if user:
                # Générer et envoyer le code de vérification
                verification_code = VerificationService.generate_verification_code()

                # Stocker le code en session pour la vérification ultérieure
                request.session['verification_user_id'] = str(user.id)
                request.session['verification_code'] = verification_code
                request.session['verification_timestamp'] = timezone.now().isoformat()

                # Envoyer le code par email
                success = VerificationCodeService.send_verification_code(user, verification_code)

                # En mode développement, afficher le code dans un message
                if settings.DEBUG:
                    messages.info(request, _(f"Code de vérification généré: {verification_code}"))

                # Rediriger vers la page de vérification
                return redirect('verify_email')
            else:
                messages.error(request, error)
    else:
        form = AccountantRegistrationForm()

    return render(request, 'users/auth/register.html', {
        'form': form,
        'user_type': UserType.ACCOUNTANT,
        'user_type_display': UserType.ACCOUNTANT.label
    })

def verify_email_view(request):
    """Vue de vérification de l'email avec le code"""
    # Vérifier que le processus de vérification est en cours
    if 'verification_user_id' not in request.session:
        return redirect('register_select_type')

    user_id = request.session.get('verification_user_id')
    user = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        form = VerificationCodeForm(request.POST)
        if form.is_valid():
            input_code = form.cleaned_data.get('code')
            stored_code = request.session.get('verification_code')

            # Convertir le timestamp en objet datetime
            timestamp_str = request.session.get('verification_timestamp')
            timestamp = timezone.datetime.fromisoformat(timestamp_str)

            # Vérifier le code
            success, message = VerificationService.activate_user(
                user, input_code, stored_code, timestamp
            )

            if success:
                # Nettoyer les données de session
                for key in ['verification_user_id', 'verification_code', 'verification_timestamp', 'registration_user_type']:
                    if key in request.session:
                        del request.session[key]

                messages.success(request, _("Votre compte a été activé avec succès. Vous pouvez maintenant vous connecter."))
                return redirect('login')
            else:
                messages.error(request, message)
    else:
        form = VerificationCodeForm()

    return render(request, 'users/auth/verify_email.html', {'form': form})

def resend_verification_code_view(request):
    """Vue pour renvoyer un code de vérification"""
    # Vérifier que le processus de vérification est en cours
    if 'verification_user_id' not in request.session:
        return redirect('register_select_type')

    user_id = request.session.get('verification_user_id')
    user = get_object_or_404(User, id=user_id)

    # Générer un nouveau code
    verification_code = VerificationService.generate_verification_code()

    # Mettre à jour les données en session
    request.session['verification_code'] = verification_code
    request.session['verification_timestamp'] = timezone.now().isoformat()

    # Envoyer le code par email
    success = VerificationCodeService.send_verification_code(user, verification_code)

    if success:
        # Afficher le code directement dans l'interface (uniquement en développement)
        if settings.DEBUG:
            messages.success(request, _(f"Un nouveau code de vérification a été envoyé à votre adresse email. Code: {verification_code}"))
        else:
            messages.success(request, _("Un nouveau code de vérification a été envoyé à votre adresse email."))
    else:
        messages.error(request, _("Une erreur est survenue lors de l'envoi du code. Veuillez réessayer."))

    return redirect('verify_email')

def password_reset_request_view(request):
    """Vue de demande de réinitialisation de mot de passe"""
    if request.user.is_authenticated:
        return redirect('dashboard')
        
    if request.method == 'POST':
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('email')
            
            try:
                user = User.objects.get(email=email)
                PasswordResetService.send_password_reset_link(user)
            except User.DoesNotExist:
                # Ne pas révéler si l'email existe dans la base
                pass
            
            # Toujours afficher le même message pour éviter les fuites d'information
            messages.success(request, _("Si votre email est associé à un compte, un lien de réinitialisation vous a été envoyé."))
            return redirect('login')
    else:
        form = PasswordResetRequestForm()
    
    return render(request, 'users/auth/password_reset_request.html', {'form': form})

def password_reset_confirm_view(request, user_id, token):
    """Vue de confirmation de réinitialisation de mot de passe"""
    if request.user.is_authenticated:
        return redirect('dashboard')
        
    user = get_object_or_404(User, id=user_id)
    
    # Vérifier la validité du token
    if not PasswordResetService.validate_password_reset_token(user, token):
        messages.error(request, _("Le lien de réinitialisation est invalide ou a expiré."))
        return redirect('password_reset_request')
    
    if request.method == 'POST':
        form = PasswordResetConfirmForm(user, request.POST)
        if form.is_valid():
            form.save()
            
            # Réinitialiser les tentatives de connexion échouées
            user.failed_login_attempts = 0
            user.locked_until = None
            user.save(update_fields=['failed_login_attempts', 'locked_until'])
            
            messages.success(request, _("Votre mot de passe a été réinitialisé avec succès. Vous pouvez maintenant vous connecter."))
            return redirect('login')
    else:
        form = PasswordResetConfirmForm(user)
    
    return render(request, 'users/auth/password_reset_confirm.html', {'form': form})

def unlock_account_view(request, user_id, token):
    """Vue de déblocage de compte"""
    if request.user.is_authenticated:
        return redirect('dashboard')
        
    user = get_object_or_404(User, id=user_id)
    
    # Vérifier la validité du token
    if not PasswordResetService.validate_password_reset_token(user, token):
        messages.error(request, _("Le lien de déblocage est invalide ou a expiré."))
        return redirect('login')
    
    # Débloquer le compte
    user.unlock_account()
    
    messages.success(request, _("Votre compte a été débloqué avec succès. Vous pouvez maintenant vous connecter."))
    return redirect('login')