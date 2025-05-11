import logging
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from .models import User, AuditLog
from .services import PasswordResetService

logger = logging.getLogger(__name__)

@receiver(post_save, sender=User)
def user_created(sender, instance, created, **kwargs):
    """Signal pour traiter la création d'un nouvel utilisateur"""
    if created:
        # Enregistrer l'événement dans le journal d'audit
        AuditLog.objects.create(
            user=None,  # L'action est effectuée par le système
            action='CREATE',
            resource_type='User',
            resource_id=str(instance.id),
            resource_representation=f"{instance.email}",
            additional_data={'user_type': instance.user_type}
        )

        logger.info(f"Nouvel utilisateur créé: {instance.email}")

@receiver(pre_save, sender=User)
def check_account_lock(sender, instance, **kwargs):
    """Signal pour vérifier si un compte doit être verrouillé ou déverrouillé"""
    try:
        # Obtenir l'état précédent de l'utilisateur (s'il existe)
        old_instance = User.objects.get(pk=instance.pk)

        # Si le compte vient d'être verrouillé
        if not old_instance.is_locked() and instance.is_locked():
            # Envoyer une notification par email
            PasswordResetService.send_account_locked_notification(instance)

            # Enregistrer l'événement dans le journal d'audit
            AuditLog.objects.create(
                user=None,  # L'action est effectuée par le système
                action='SECURITY',
                resource_type='User',
                resource_id=str(instance.id),
                resource_representation=f"{instance.email}",
                additional_data={'reason': 'account_locked', 'attempts': instance.failed_login_attempts}
            )

            logger.warning(f"Compte verrouillé pour l'utilisateur: {instance.email}")

        # Si le compte vient d'être déverrouillé
        elif old_instance.is_locked() and not instance.is_locked():
            # Enregistrer l'événement dans le journal d'audit
            AuditLog.objects.create(
                user=None,  # L'action est effectuée par le système
                action='SECURITY',
                resource_type='User',
                resource_id=str(instance.id),
                resource_representation=f"{instance.email}",
                additional_data={'reason': 'account_unlocked'}
            )

            logger.info(f"Compte déverrouillé pour l'utilisateur: {instance.email}")

    except User.DoesNotExist:
        # C'est un nouvel utilisateur, rien à faire
        pass