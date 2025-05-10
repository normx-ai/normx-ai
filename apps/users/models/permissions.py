from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from .user import User

class Role(models.Model):
    name = models.CharField(_('nom'), max_length=100, unique=True)
    description = models.TextField(_('description'), blank=True)
    permissions = models.ManyToManyField(
        Permission,
        verbose_name=_('permissions'),
        blank=True,
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True, 
        blank=True,
        related_name='children',
        verbose_name=_('rôle parent')
    )
    is_system = models.BooleanField(_('rôle système'), default=False, help_text=_('Les rôles système ne peuvent pas être supprimés'))
    created_at = models.DateTimeField(_('date de création'), auto_now_add=True)
    updated_at = models.DateTimeField(_('date de mise à jour'), auto_now=True)
    
    class Meta:
        verbose_name = _('rôle')
        verbose_name_plural = _('rôles')
    
    def __str__(self):
        return self.name
    
    def get_all_permissions(self):
        """Récupère toutes les permissions, y compris celles héritées des rôles parents"""
        all_permissions = set(self.permissions.all())
        if self.parent:
            all_permissions.update(self.parent.get_all_permissions())
        return all_permissions

class UserRole(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='user_roles',
        verbose_name=_('utilisateur')
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name='user_assignments',
        verbose_name=_('rôle')
    )
    scope = models.CharField(_('portée'), max_length=255, blank=True, help_text=_('Identifiant de l\'objet auquel ce rôle s\'applique, si applicable'))
    assigned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_roles',
        verbose_name=_('assigné par')
    )
    created_at = models.DateTimeField(_('date de création'), auto_now_add=True)
    updated_at = models.DateTimeField(_('date de mise à jour'), auto_now=True)
    
    class Meta:
        verbose_name = _('rôle utilisateur')
        verbose_name_plural = _('rôles utilisateurs')
        unique_together = ('user', 'role', 'scope')
    
    def __str__(self):
        return f"{self.user.email} - {self.role.name} ({self.scope})" if self.scope else f"{self.user.email} - {self.role.name}"

class AuditLog(models.Model):
    class ActionType(models.TextChoices):
        CREATE = 'CREATE', _('Création')
        READ = 'READ', _('Lecture')
        UPDATE = 'UPDATE', _('Mise à jour')
        DELETE = 'DELETE', _('Suppression')
        LOGIN = 'LOGIN', _('Connexion')
        LOGOUT = 'LOGOUT', _('Déconnexion')
        PERMISSION = 'PERMISSION', _('Changement de permission')
        CUSTOM = 'CUSTOM', _('Action personnalisée')
    
    timestamp = models.DateTimeField(_('horodatage'), auto_now_add=True)
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='audit_logs',
        verbose_name=_('utilisateur')
    )
    action_type = models.CharField(
        _('type d\'action'),
        max_length=20,
        choices=ActionType.choices
    )
    object_type = models.CharField(_('type d\'objet'), max_length=255, blank=True)
    object_id = models.CharField(_('identifiant d\'objet'), max_length=255, blank=True)
    description = models.TextField(_('description'))
    ip_address = models.GenericIPAddressField(_('adresse IP'), null=True, blank=True)
    user_agent = models.TextField(_('user agent'), blank=True)
    metadata = models.JSONField(_('métadonnées'), default=dict, blank=True)
    
    class Meta:
        verbose_name = _('journal d\'audit')
        verbose_name_plural = _('journaux d\'audit')
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.timestamp} - {self.user} - {self.action_type}"