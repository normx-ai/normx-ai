import logging
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.translation import gettext_lazy as _

from ..models import User, UserType

logger = logging.getLogger(__name__)

@login_required
def dashboard_view(request):
    """Vue du tableau de bord principal"""
    user = request.user
    
    # Rediriger vers l'onboarding si nécessaire
    if user.user_type == UserType.COMPANY:
        profile = getattr(user, 'company_profile', None)
        if profile and not profile.onboarding_completed:
            return redirect('company_onboarding')
        template = 'users/dashboard/company_dashboard.html'
    else:  # ACCOUNTANT
        profile = getattr(user, 'accountant_profile', None)
        if profile and not profile.onboarding_completed:
            return redirect('accountant_onboarding')
        template = 'users/dashboard/accountant_dashboard.html'
    
    context = {
        'user': user,
        'profile': profile,
    }
    
    # Ajouter des données spécifiques au type d'utilisateur
    if user.user_type == UserType.COMPANY:
        # TODO: Ajouter des données pour le tableau de bord entreprise
        # Par exemple:
        # - Notifications importantes (échéances fiscales)
        # - Tâches en attente
        # - Accès aux fonctionnalités les plus utilisées
        pass
    else:  # ACCOUNTANT
        # TODO: Ajouter des données pour le tableau de bord expert-comptable
        # Par exemple:
        # - Liste des clients avec indicateurs d'activité
        # - Tâches en attente par client
        pass
    
    return render(request, template, context)

@login_required
def company_onboarding_view(request):
    """Vue d'onboarding pour les entreprises (premier accès)"""
    user = request.user
    
    # Vérifier que l'utilisateur est bien une entreprise
    if user.user_type != UserType.COMPANY:
        messages.error(request, _("Vous n'avez pas accès à cette page."))
        return redirect('dashboard')
    
    profile = getattr(user, 'company_profile', None)
    
    if not profile:
        messages.error(request, _("Profil entreprise introuvable."))
        return redirect('dashboard')
    
    # Si l'onboarding est déjà terminé, rediriger vers le tableau de bord
    if profile.onboarding_completed:
        return redirect('dashboard')
    
    # Gérer les étapes d'onboarding
    current_step = request.session.get('onboarding_step', 1)
    total_steps = 6  # Nombre total d'étapes
    
    if request.method == 'POST':
        # TODO: Gérer les différentes étapes de l'onboarding
        # Étape 1: Bienvenue et présentation du système
        # Étape 2: Configuration de l'exercice fiscal initial
        # Étape 3: Paramétrage des préférences comptables
        # Étape 4: Importation du plan comptable OHADA
        # Étape 5: Configuration des journaux comptables
        # Étape 6: Tutoriel rapide des fonctionnalités principales
        
        # Pour cet exemple, on passe simplement à l'étape suivante
        next_step = current_step + 1
        
        if next_step > total_steps:
            # Onboarding terminé
            profile.onboarding_completed = True
            profile.save(update_fields=['onboarding_completed'])
            
            # Nettoyer la session
            if 'onboarding_step' in request.session:
                del request.session['onboarding_step']
            
            messages.success(request, _("Configuration initiale terminée avec succès!"))
            return redirect('dashboard')
        else:
            # Passer à l'étape suivante
            request.session['onboarding_step'] = next_step
            current_step = next_step
    
    context = {
        'current_step': current_step,
        'total_steps': total_steps,
        'progress_percent': int((current_step / total_steps) * 100),
    }
    
    # Déterminer le template à utiliser en fonction de l'étape
    template = f'users/onboarding/company_step{current_step}.html'
    
    return render(request, template, context)

@login_required
def accountant_onboarding_view(request):
    """Vue d'onboarding pour les experts-comptables (premier accès)"""
    user = request.user
    
    # Vérifier que l'utilisateur est bien un expert-comptable
    if user.user_type != UserType.ACCOUNTANT:
        messages.error(request, _("Vous n'avez pas accès à cette page."))
        return redirect('dashboard')
    
    profile = getattr(user, 'accountant_profile', None)
    
    if not profile:
        messages.error(request, _("Profil expert-comptable introuvable."))
        return redirect('dashboard')
    
    # Si l'onboarding est déjà terminé, rediriger vers le tableau de bord
    if profile.onboarding_completed:
        return redirect('dashboard')
    
    # Gérer les étapes d'onboarding
    current_step = request.session.get('onboarding_step', 1)
    total_steps = 5  # Nombre total d'étapes
    
    if request.method == 'POST':
        # TODO: Gérer les différentes étapes de l'onboarding
        # Étape 1: Bienvenue et présentation du système
        # Étape 2: Configuration du cabinet et des paramètres par défaut
        # Étape 3: Options pour ajouter des clients existants
        # Étape 4: Configuration des modèles de documents
        # Étape 5: Tutoriel des fonctionnalités spécifiques aux experts-comptables
        
        # Pour cet exemple, on passe simplement à l'étape suivante
        next_step = current_step + 1
        
        if next_step > total_steps:
            # Onboarding terminé
            profile.onboarding_completed = True
            profile.save(update_fields=['onboarding_completed'])
            
            # Nettoyer la session
            if 'onboarding_step' in request.session:
                del request.session['onboarding_step']
            
            messages.success(request, _("Configuration initiale terminée avec succès!"))
            return redirect('dashboard')
        else:
            # Passer à l'étape suivante
            request.session['onboarding_step'] = next_step
            current_step = next_step
    
    context = {
        'current_step': current_step,
        'total_steps': total_steps,
        'progress_percent': int((current_step / total_steps) * 100),
    }
    
    # Déterminer le template à utiliser en fonction de l'étape
    template = f'users/onboarding/accountant_step{current_step}.html'
    
    return render(request, template, context)