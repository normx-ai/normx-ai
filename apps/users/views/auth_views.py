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
    if request.user.is_authenticated:
        return redirect('dashboard')
        
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            remember = form.cleaned_data.get('remember_me', False)
            
            user, error = AuthenticationService.login(request, email, password, remember)
            
            if user:
                # Gérer l'authentification à deux facteurs si activée
                if user.mfa_enabled:
                    # Stocker les informations nécessaires en session
                    request.session['mfa_user_id'] = str(user.id)
                    request.session['mfa_remember'] = remember
                    return redirect('mfa_verification')
                    
                # Connexion standard si MFA non activée
                login(request, user)
                
                # Vérifier si c'est un premier accès
                if user.user_type == UserType.COMPANY:
                    if hasattr(user, 'company_profile') and not user.company_profile.onboarding_completed:
                        return redirect('company_onboarding')
                elif user.user_type == UserType.ACCOUNTANT:
                    if hasattr(user, 'accountant_profile') and not user.accountant_profile.onboarding_completed:
                        return redirect('accountant_onboarding')
                
                # Redirection vers le tableau de bord
                return redirect('dashboard')
            else:
                messages.error(request, error)
    else:
        form = LoginForm()
    
    return render(request, 'users/auth/login.html', {'form': form})

def mfa_verification_view(request):
    """Vue de vérification pour l'authentification à deux facteurs"""
    # Vérifier que l'utilisateur est en cours d'authentification MFA
    if 'mfa_user_id' not in request.session:
        return redirect('login')
    
    user_id = request.session.get('mfa_user_id')
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        form = MFAVerificationForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data.get('code')
            
            # TODO: Implémenter la vérification réelle du code MFA
            # Pour l'instant, on simule une vérification réussie avec n'importe quel code
            is_valid = True  # À remplacer par une vérification réelle
            
            if is_valid:
                # Connecter l'utilisateur
                remember = request.session.get('mfa_remember', False)
                login(request, user)
                
                # Nettoyer les données de session
                if 'mfa_user_id' in request.session:
                    del request.session['mfa_user_id']
                if 'mfa_remember' in request.session:
                    del request.session['mfa_remember']
                
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
                
                # Redirection vers le tableau de bord
                return redirect('dashboard')
            else:
                messages.error(request, _("Code d'authentification invalide. Veuillez réessayer."))
    else:
        form = MFAVerificationForm()
    
    return render(request, 'users/auth/mfa_verification.html', {'form': form})

@login_required
def logout_view(request):
    """Vue de déconnexion"""
    user = request.user
    AuthenticationService.logout(request, user)
    logout(request)
    messages.success(request, _("Vous avez été déconnecté avec succès."))
    return redirect('login')

def register_select_type_view(request):
    """Vue de sélection du type d'utilisateur lors de l'inscription"""
    if request.user.is_authenticated:
        return redirect('dashboard')
        
    if request.method == 'POST':
        form = UserTypeSelectForm(request.POST)
        if form.is_valid():
            user_type = form.cleaned_data.get('user_type')
            request.session['registration_user_type'] = user_type
            
            if user_type == UserType.COMPANY:
                return redirect('register_company')
            else:
                return redirect('register_accountant')
    else:
        form = UserTypeSelectForm()
    
    return render(request, 'users/auth/register_select_type.html', {'form': form})

def register_company_view(request):
    """Vue d'inscription pour les entreprises"""
    if request.user.is_authenticated:
        return redirect('dashboard')
        
    # Vérifier que le type d'utilisateur a été sélectionné
    if 'registration_user_type' not in request.session or request.session['registration_user_type'] != UserType.COMPANY:
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
                VerificationCodeService.send_verification_code(user, verification_code)
                
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
    if request.user.is_authenticated:
        return redirect('dashboard')
        
    # Vérifier que le type d'utilisateur a été sélectionné
    if 'registration_user_type' not in request.session or request.session['registration_user_type'] != UserType.ACCOUNTANT:
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
                VerificationCodeService.send_verification_code(user, verification_code)
                
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