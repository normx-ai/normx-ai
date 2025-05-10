import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.translation import gettext_lazy as _

from ..models import User, UserType
from ..forms import (
    UserBasicInfoForm, CompanyProfileForm, AccountantProfileForm,
    SecuritySettingsForm, CustomPasswordChangeForm, AccountingSettingsForm
)
from ..services import PasswordResetService

logger = logging.getLogger(__name__)

@login_required
def profile_view(request):
    """Vue d'affichage du profil utilisateur"""
    user = request.user
    
    # Déterminer le type de profil
    if user.user_type == UserType.COMPANY:
        profile = getattr(user, 'company_profile', None)
        template = 'users/profile/company_detail.html'
    else:
        profile = getattr(user, 'accountant_profile', None)
        template = 'users/profile/accountant_detail.html'
    
    context = {
        'user': user,
        'profile': profile
    }
    
    return render(request, template, context)

@login_required
def edit_basic_info_view(request):
    """Vue de modification des informations de base"""
    user = request.user
    
    if request.method == 'POST':
        form = UserBasicInfoForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, _("Vos informations ont été mises à jour avec succès."))
            return redirect('profile')
    else:
        form = UserBasicInfoForm(instance=user)
    
    return render(request, 'users/profile/edit_basic_info.html', {'form': form})

@login_required
def edit_company_profile_view(request):
    """Vue de modification du profil entreprise"""
    user = request.user
    
    # Vérifier que l'utilisateur est bien une entreprise
    if user.user_type != UserType.COMPANY:
        messages.error(request, _("Vous n'avez pas accès à cette page."))
        return redirect('profile')
    
    profile = getattr(user, 'company_profile', None)
    
    if not profile:
        messages.error(request, _("Profil entreprise introuvable."))
        return redirect('profile')
    
    if request.method == 'POST':
        form = CompanyProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, _("Votre profil entreprise a été mis à jour avec succès."))
            return redirect('profile')
    else:
        form = CompanyProfileForm(instance=profile)
    
    return render(request, 'users/profile/edit_company.html', {'form': form})

@login_required
def edit_accountant_profile_view(request):
    """Vue de modification du profil expert-comptable"""
    user = request.user
    
    # Vérifier que l'utilisateur est bien un expert-comptable
    if user.user_type != UserType.ACCOUNTANT:
        messages.error(request, _("Vous n'avez pas accès à cette page."))
        return redirect('profile')
    
    profile = getattr(user, 'accountant_profile', None)
    
    if not profile:
        messages.error(request, _("Profil expert-comptable introuvable."))
        return redirect('profile')
    
    if request.method == 'POST':
        form = AccountantProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, _("Votre profil expert-comptable a été mis à jour avec succès."))
            return redirect('profile')
    else:
        form = AccountantProfileForm(instance=profile)
    
    return render(request, 'users/profile/edit_accountant.html', {'form': form})

@login_required
def security_settings_view(request):
    """Vue des paramètres de sécurité"""
    user = request.user
    
    if request.method == 'POST':
        form = SecuritySettingsForm(request.POST, instance=user, user=user)
        if form.is_valid():
            form.save()
            messages.success(request, _("Vos paramètres de sécurité ont été mis à jour avec succès."))
            return redirect('profile')
    else:
        form = SecuritySettingsForm(instance=user, user=user)
    
    return render(request, 'users/profile/security_settings.html', {'form': form})

@login_required
def change_password_view(request):
    """Vue de changement de mot de passe"""
    user = request.user
    
    if request.method == 'POST':
        form = CustomPasswordChangeForm(user, request.POST)
        if form.is_valid():
            form.save()
            
            # Réinitialiser les tentatives de connexion échouées
            user.failed_login_attempts = 0
            user.locked_until = None
            user.save(update_fields=['failed_login_attempts', 'locked_until'])
            
            # Envoyer une notification par email
            try:
                send_password_change_notification(user)
            except Exception as e:
                logger.error(f"Erreur lors de l'envoi de la notification de changement de mot de passe: {str(e)}")
            
            messages.success(request, _("Votre mot de passe a été changé avec succès."))
            return redirect('profile')
    else:
        form = CustomPasswordChangeForm(user)
    
    return render(request, 'users/profile/change_password.html', {'form': form})

@login_required
def accounting_settings_view(request):
    """Vue des paramètres comptables (pour les entreprises uniquement)"""
    user = request.user
    
    # Vérifier que l'utilisateur est bien une entreprise
    if user.user_type != UserType.COMPANY:
        messages.error(request, _("Vous n'avez pas accès à cette page."))
        return redirect('profile')
    
    profile = getattr(user, 'company_profile', None)
    
    if not profile:
        messages.error(request, _("Profil entreprise introuvable."))
        return redirect('profile')
    
    if request.method == 'POST':
        form = AccountingSettingsForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, _("Vos paramètres comptables ont été mis à jour avec succès."))
            return redirect('profile')
    else:
        form = AccountingSettingsForm(instance=profile)
    
    return render(request, 'users/profile/accounting_settings.html', {'form': form})

def send_password_change_notification(user):
    """Envoie une notification par email lors d'un changement de mot de passe"""
    subject = "Normx-AI - Confirmation de changement de mot de passe"
    message = f"""
    Bonjour {user.get_full_name()},
    
    Nous vous confirmons que votre mot de passe a été changé avec succès.
    
    Si vous n'avez pas effectué cette action, veuillez contacter immédiatement notre support.
    
    L'équipe Normx-AI
    """
    
    try:
        from django.core.mail import send_mail
        from django.template.loader import render_to_string
        
        html_message = render_to_string('users/emails/password_changed.html', {'user': user})
        
        send_mail(
            subject=subject,
            message=message,
            from_email=None,  # Utiliser l'email par défaut
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False
        )
        return True
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi de la notification: {str(e)}")
        return False