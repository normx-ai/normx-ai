import jwt
import uuid
import logging
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.contrib.auth.tokens import PasswordResetTokenGenerator

from ..models import User

logger = logging.getLogger(__name__)

class TokenService:
    """Service de gestion des tokens pour l'authentification API et les processus de sécurité"""
    
    @staticmethod
    def generate_jwt_token(user):
        """Génère un token JWT pour l'authentification API"""
        payload = {
            'user_id': str(user.id),
            'email': user.email,
            'user_type': user.user_type,
            'exp': datetime.utcnow() + timedelta(days=1),  # Expiration après 1 jour
            'iat': datetime.utcnow(),
            'jti': str(uuid.uuid4())  # JWT ID unique
        }
        
        token = jwt.encode(
            payload,
            settings.SECRET_KEY,
            algorithm='HS256'
        )
        
        logger.info(f"Token JWT généré pour l'utilisateur {user.email}")
        return token
    
    @staticmethod
    def validate_jwt_token(token):
        """Valide un token JWT et retourne les informations de l'utilisateur"""
        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=['HS256']
            )
            
            user_id = payload.get('user_id')
            user = User.objects.get(id=user_id)
            
            if not user.is_active:
                logger.warning(f"Tentative d'utilisation d'un token pour un utilisateur inactif: {user.email}")
                return None
            
            return user
            
        except jwt.ExpiredSignatureError:
            logger.warning("Token JWT expiré")
            return None
        except (jwt.InvalidTokenError, User.DoesNotExist):
            logger.warning("Token JWT invalide")
            return None

class VerificationCodeService:
    """Service de gestion des codes de vérification pour l'activation de compte"""
    
    @staticmethod
    def send_verification_code(user, code):
        """Envoie un email contenant le code de vérification"""
        subject = "Normx-AI - Vérification de votre compte"
        message = f"""
        Bonjour {user.get_full_name()},
        
        Votre code de vérification pour activer votre compte Normx-AI est : {code}
        
        Ce code est valable pendant 30 minutes.
        
        Si vous n'avez pas créé de compte sur Normx-AI, veuillez ignorer cet email.
        
        L'équipe Normx-AI
        """
        
        html_message = render_to_string('users/emails/verification_code.html', {
            'user': user,
            'code': code,
            'expiry_minutes': 30
        })
        
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False
            )
            logger.info(f"Code de vérification envoyé à {user.email}")
            return True
        except Exception as e:
            logger.error(f"Échec de l'envoi du code de vérification à {user.email}: {str(e)}")
            return False

class PasswordResetService:
    """Service de gestion des réinitialisations de mot de passe"""
    
    token_generator = PasswordResetTokenGenerator()
    
    @staticmethod
    def send_password_reset_link(user):
        """Envoie un email contenant le lien de réinitialisation de mot de passe"""
        token = PasswordResetService.token_generator.make_token(user)
        
        # Dans un contexte réel, vous utiliseriez une URL de front-end
        reset_url = f"{settings.SITE_URL}/reset-password/{user.id}/{token}/"
        
        subject = "Normx-AI - Réinitialisation de votre mot de passe"
        message = f"""
        Bonjour {user.get_full_name()},
        
        Vous avez demandé la réinitialisation de votre mot de passe sur Normx-AI.
        
        Pour définir un nouveau mot de passe, veuillez cliquer sur le lien suivant :
        {reset_url}
        
        Ce lien est valable pendant 24 heures.
        
        Si vous n'avez pas demandé de réinitialisation de mot de passe, veuillez ignorer cet email.
        
        L'équipe Normx-AI
        """
        
        html_message = render_to_string('users/emails/password_reset.html', {
            'user': user,
            'reset_url': reset_url
        })
        
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False
            )
            logger.info(f"Lien de réinitialisation de mot de passe envoyé à {user.email}")
            return True
        except Exception as e:
            logger.error(f"Échec de l'envoi du lien de réinitialisation à {user.email}: {str(e)}")
            return False
    
    @staticmethod
    def validate_password_reset_token(user, token):
        """Valide un token de réinitialisation de mot de passe"""
        return PasswordResetService.token_generator.check_token(user, token)
    
    @staticmethod
    def send_account_locked_notification(user):
        """Envoie un email de notification lorsqu'un compte est verrouillé"""
        token = PasswordResetService.token_generator.make_token(user)
        
        # URL pour débloquer le compte
        unlock_url = f"{settings.SITE_URL}/unlock-account/{user.id}/{token}/"
        
        subject = "Normx-AI - Votre compte a été temporairement verrouillé"
        message = f"""
        Bonjour {user.get_full_name()},
        
        Votre compte Normx-AI a été temporairement verrouillé suite à plusieurs tentatives de connexion échouées.
        
        Si c'était vous, vous pouvez débloquer votre compte immédiatement en cliquant sur le lien suivant :
        {unlock_url}
        
        Si ce n'était pas vous, quelqu'un a peut-être essayé d'accéder à votre compte. Pour plus de sécurité, nous vous recommandons de changer votre mot de passe après avoir débloqué votre compte.
        
        L'équipe Normx-AI
        """
        
        html_message = render_to_string('users/emails/account_locked.html', {
            'user': user,
            'unlock_url': unlock_url
        })
        
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False
            )
            logger.info(f"Notification de verrouillage de compte envoyée à {user.email}")
            return True
        except Exception as e:
            logger.error(f"Échec de l'envoi de la notification de verrouillage à {user.email}: {str(e)}")
            return False