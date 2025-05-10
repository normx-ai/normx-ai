import random
import string
import logging
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError
from django.db import transaction

from ..models import User, UserType, CompanyProfile, AccountantProfile

logger = logging.getLogger(__name__)

class VerificationService:
    """Service de gestion des codes de vérification et activation des comptes"""
    
    CODE_LENGTH = 6
    CODE_EXPIRY_MINUTES = 30
    
    @staticmethod
    def generate_verification_code():
        """Génère un code de vérification numérique à 6 chiffres"""
        return ''.join(random.choices(string.digits, k=VerificationService.CODE_LENGTH))
    
    @staticmethod
    def is_code_valid(code, stored_code, created_at):
        """Vérifie si un code est valide et non expiré"""
        if not stored_code or not created_at:
            return False
            
        # Vérifier que le code n'est pas expiré
        expiry_time = created_at + timedelta(minutes=VerificationService.CODE_EXPIRY_MINUTES)
        if timezone.now() > expiry_time:
            return False
            
        # Vérifier que le code correspond
        return code == stored_code
    
    @staticmethod
    def activate_user(user, verification_code, stored_code, code_created_at):
        """Active un compte utilisateur si le code est valide"""
        if not VerificationService.is_code_valid(verification_code, stored_code, code_created_at):
            return False, "Code de vérification invalide ou expiré"
            
        user.is_active = True
        user.is_verified = True
        user.save(update_fields=['is_active', 'is_verified'])
        
        logger.info(f"Compte activé avec succès pour l'utilisateur {user.email}")
        return True, "Compte activé avec succès"

class RegistrationService:
    """Service de gestion des inscriptions utilisateur"""
    
    @staticmethod
    @transaction.atomic
    def register_company(data):
        """Inscrit une nouvelle entreprise"""
        try:
            # Création de l'utilisateur
            user_data = {
                'email': data.get('email'),
                'password': data.get('password'),
                'first_name': data.get('first_name'),
                'last_name': data.get('last_name'),
                'phone_number': data.get('phone_number'),
                'user_type': UserType.COMPANY,
            }
            
            user = User.objects.create_user(**user_data)
            
            # Création du profil entreprise
            company_data = {
                'user': user,
                'company_name': data.get('company_name'),
                'legal_form': data.get('legal_form'),
                'tax_id': data.get('tax_id'),
                'address': data.get('address'),
                'city': data.get('city'),
                'postal_code': data.get('postal_code'),
                'country': data.get('country', 'Bénin'),
                'user_position': data.get('user_position'),
                'accounting_system': data.get('accounting_system'),
            }
            
            CompanyProfile.objects.create(**company_data)
            
            logger.info(f"Entreprise inscrite avec succès: {data.get('company_name')}")
            return user, None
        
        except Exception as e:
            logger.error(f"Erreur lors de l'inscription d'une entreprise: {str(e)}")
            if isinstance(e, ValidationError):
                return None, str(e)
            return None, "Une erreur est survenue lors de l'inscription"
    
    @staticmethod
    @transaction.atomic
    def register_accountant(data):
        """Inscrit un nouvel expert-comptable"""
        try:
            # Création de l'utilisateur
            user_data = {
                'email': data.get('email'),
                'password': data.get('password'),
                'first_name': data.get('first_name'),
                'last_name': data.get('last_name'),
                'phone_number': data.get('phone_number'),
                'user_type': UserType.ACCOUNTANT,
            }
            
            user = User.objects.create_user(**user_data)
            
            # Création du profil expert-comptable
            accountant_data = {
                'user': user,
                'firm_name': data.get('firm_name'),
                'professional_id': data.get('professional_id'),
                'address': data.get('address'),
                'city': data.get('city'),
                'postal_code': data.get('postal_code'),
                'country': data.get('country', 'Bénin'),
                'syscohada_certified': data.get('syscohada_certified', False),
                'sysbenyl_certified': data.get('sysbenyl_certified', False),
                'minimal_certified': data.get('minimal_certified', False),
            }
            
            AccountantProfile.objects.create(**accountant_data)
            
            # Activer MFA par défaut pour les experts-comptables
            if user.user_type == UserType.ACCOUNTANT:
                user.mfa_enabled = True
                user.save(update_fields=['mfa_enabled'])
            
            logger.info(f"Expert-comptable inscrit avec succès: {data.get('firm_name')}")
            return user, None
        
        except Exception as e:
            logger.error(f"Erreur lors de l'inscription d'un expert-comptable: {str(e)}")
            if isinstance(e, ValidationError):
                return None, str(e)
            return None, "Une erreur est survenue lors de l'inscription"

class AuthenticationService:
    """Service de gestion de l'authentification des utilisateurs"""
    
    @staticmethod
    def login(request, email, password, remember=False):
        """Authentifie un utilisateur"""
        ip_address = request.META.get('REMOTE_ADDR')
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Rechercher l'utilisateur
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            logger.warning(f"Tentative de connexion avec un email inexistant: {email}")
            return None, "Identifiants invalides"
        
        # Vérifier si le compte est verrouillé
        if user.is_locked():
            logger.warning(f"Tentative de connexion sur un compte verrouillé: {email}")
            return None, "Ce compte est temporairement verrouillé. Veuillez réessayer plus tard ou utilisez le lien de déblocage envoyé par email."
        
        # Vérifier si le compte est activé
        if not user.is_active:
            logger.warning(f"Tentative de connexion sur un compte non activé: {email}")
            return None, "Ce compte n'est pas activé. Veuillez vérifier votre email pour activer votre compte."
        
        # Authentifier l'utilisateur
        user = authenticate(request=request, username=email, password=password)
        
        if user is None:
            # Enregistrer la tentative échouée
            found_user = User.objects.get(email=email)
            found_user.record_login_attempt(
                success=False, 
                ip_address=ip_address,
                device_info={
                    'user_agent': user_agent,
                    'timestamp': timezone.now().isoformat()
                }
            )
            
            # Message d'erreur générique pour des raisons de sécurité
            return None, "Identifiants invalides"
        
        # Connexion réussie
        device_info = {
            'user_agent': user_agent,
            'timestamp': timezone.now().isoformat()
        }
        
        user.record_login_attempt(
            success=True, 
            ip_address=ip_address,
            device_info=device_info
        )
        
        # Gérer la session selon l'option "se souvenir de moi"
        if remember:
            # Session de 2 semaines
            request.session.set_expiry(1209600)
        else:
            # Session qui expire à la fermeture du navigateur
            request.session.set_expiry(0)
        
        logger.info(f"Connexion réussie pour l'utilisateur {user.email}")
        return user, None
    
    @staticmethod
    def is_unusual_login(user, request):
        """Détecte si la connexion provient d'un appareil ou d'une localisation inhabituelle"""
        ip_address = request.META.get('REMOTE_ADDR')
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Vérifier si l'adresse IP est connue
        known_ips = [entry.get('ip_address') for entry in user.login_history if entry.get('success', False)]
        if ip_address not in known_ips:
            logger.info(f"Connexion depuis une IP inhabituelle pour {user.email}: {ip_address}")
            return True
        
        # Vérifier si l'appareil est connu
        for device in user.known_devices:
            if device.get('user_agent') == user_agent:
                return False
        
        logger.info(f"Connexion depuis un appareil inhabituel pour {user.email}")
        return True
    
    @staticmethod
    def logout(request, user):
        """Déconnecte un utilisateur et enregistre l'événement"""
        if user and user.is_authenticated:
            ip_address = request.META.get('REMOTE_ADDR')
            timestamp = timezone.now()
            
            # Enregistrer la déconnexion dans l'historique
            logout_entry = {
                'timestamp': timestamp.isoformat(),
                'ip_address': ip_address,
                'action': 'logout',
                'success': True
            }
            
            # Mettre à jour l'historique
            user.login_history = [logout_entry] + user.login_history[:9]
            user.save(update_fields=['login_history'])
            
            logger.info(f"Déconnexion réussie pour l'utilisateur {user.email}")
            
        # Effacer la session
        request.session.flush()