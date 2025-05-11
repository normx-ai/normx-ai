# -*- coding: utf-8 -*-
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator
from .user import User, UserType

class AccountingSystem(models.TextChoices):
    SYSCOHADA = 'SYSCOHADA', _('SYSCOHADA (standard)')
    SYSBENYL = 'SYSBENYL', _('SYSBENYL (associations/ONG)')
    MINIMAL = 'MINIMAL', _('Système minimal (TPE)')

class CompanyProfile(models.Model):
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='company_profile',
        verbose_name=_('utilisateur')
    )
    company_name = models.CharField(_('nom de l\'entreprise'), max_length=255)
    legal_form = models.CharField(_('forme juridique'), max_length=100)
    tax_id = models.CharField(
        _('numéro d\'identification fiscale'), 
        max_length=50,
        unique=True,
    )
    address = models.CharField(_('adresse'), max_length=255)
    city = models.CharField(_('ville'), max_length=100)
    postal_code = models.CharField(_('code postal'), max_length=20)
    country = models.CharField(_('pays'), max_length=100, default='Bénin')
    user_position = models.CharField(_('fonction dans l\'entreprise'), max_length=100)
    accounting_system = models.CharField(
        _('système comptable'),
        max_length=20,
        choices=AccountingSystem.choices,
        default=AccountingSystem.SYSCOHADA
    )
    onboarding_completed = models.BooleanField(_('configuration initiale terminée'), default=False)
    
    created_at = models.DateTimeField(_('date de création'), auto_now_add=True)
    updated_at = models.DateTimeField(_('date de mise à jour'), auto_now=True)
    
    class Meta:
        verbose_name = _('profil entreprise')
        verbose_name_plural = _('profils entreprises')
    
    def __str__(self):
        return self.company_name

class AccountantProfile(models.Model):
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='accountant_profile',
        verbose_name=_('utilisateur')
    )
    firm_name = models.CharField(_('nom du cabinet'), max_length=255)
    professional_id = models.CharField(
        _('numéro d\'agrément professionnel'), 
        max_length=50,
        unique=True
    )
    address = models.CharField(_('adresse'), max_length=255)
    city = models.CharField(_('ville'), max_length=100)
    postal_code = models.CharField(_('code postal'), max_length=20)
    country = models.CharField(_('pays'), max_length=100, default='Bénin')
    
    # Compétences/certifications
    syscohada_certified = models.BooleanField(_('certifié SYSCOHADA'), default=False)
    sysbenyl_certified = models.BooleanField(_('certifié SYSBENYL'), default=False)
    minimal_certified = models.BooleanField(_('certifié Système minimal'), default=False)
    
    onboarding_completed = models.BooleanField(_('configuration initiale terminée'), default=False)
    
    created_at = models.DateTimeField(_('date de création'), auto_now_add=True)
    updated_at = models.DateTimeField(_('date de mise à jour'), auto_now=True)
    
    class Meta:
        verbose_name = _('profil expert-comptable')
        verbose_name_plural = _('profils experts-comptables')
    
    def __str__(self):
        return self.firm_name