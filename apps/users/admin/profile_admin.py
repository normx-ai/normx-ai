# -*- coding: utf-8 -*-
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.urls import reverse

from ..models import CompanyProfile, AccountantProfile, AccountingSystem


@admin.register(CompanyProfile)
class CompanyProfileAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'get_user_link', 'tax_id', 'accounting_system_display', 'city', 'created_at')
    list_filter = ('accounting_system', 'onboarding_completed', 'created_at')
    search_fields = ('company_name', 'tax_id', 'user__email', 'user__first_name', 'user__last_name')
    ordering = ('-created_at',)
    
    fieldsets = (
        (_('Utilisateur'), {'fields': ('user', 'get_user_link')}),
        (_('Informations entreprise'), {
            'fields': ('company_name', 'legal_form', 'tax_id', 'accounting_system'),
        }),
        (_('Adresse'), {
            'fields': ('address', 'city', 'postal_code', 'country'),
        }),
        (_('Informations complémentaires'), {
            'fields': ('user_position', 'onboarding_completed'),
        }),
        (_('Dates'), {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )
    readonly_fields = ('created_at', 'updated_at', 'get_user_link')
    
    def accounting_system_display(self, obj):
        return obj.get_accounting_system_display()
    accounting_system_display.short_description = _('Système comptable')
    
    def get_user_link(self, obj):
        """Ajoute un lien vers l'utilisateur"""
        if obj.user:
            url = reverse('admin:users_user_change', args=[obj.user.id])
            return format_html(
                '<a href="{}">{} ({})</a>',
                url,
                obj.user.get_full_name(),
                obj.user.email
            )
        return _('Aucun utilisateur')
    get_user_link.short_description = _('Utilisateur')
    
    def save_model(self, request, obj, form, change):
        """Surcharge pour gérer l'enregistrement du modèle"""
        # Lors de la création, s'assurer que le type d'utilisateur est cohérent
        if not change and obj.user:  # Nouveau profil
            obj.user.user_type = 'COMPANY'
            obj.user.save(update_fields=['user_type'])
        super().save_model(request, obj, form, change)


@admin.register(AccountantProfile)
class AccountantProfileAdmin(admin.ModelAdmin):
    list_display = ('firm_name', 'get_user_link', 'professional_id', 'city', 'certification_status', 'created_at')
    list_filter = (
        'syscohada_certified', 'sysbenyl_certified', 'minimal_certified',
        'onboarding_completed', 'created_at'
    )
    search_fields = ('firm_name', 'professional_id', 'user__email', 'user__first_name', 'user__last_name')
    ordering = ('-created_at',)
    
    fieldsets = (
        (_('Utilisateur'), {'fields': ('user', 'get_user_link')}),
        (_('Informations cabinet'), {
            'fields': ('firm_name', 'professional_id'),
        }),
        (_('Adresse'), {
            'fields': ('address', 'city', 'postal_code', 'country'),
        }),
        (_('Certifications'), {
            'fields': ('syscohada_certified', 'sysbenyl_certified', 'minimal_certified'),
        }),
        (_('Informations complémentaires'), {
            'fields': ('onboarding_completed',),
        }),
        (_('Dates'), {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )
    readonly_fields = ('created_at', 'updated_at', 'get_user_link')
    
    def certification_status(self, obj):
        """Affiche un résumé des certifications"""
        certifications = []
        if obj.syscohada_certified:
            certifications.append('SYSCOHADA')
        if obj.sysbenyl_certified:
            certifications.append('SYSBENYL')
        if obj.minimal_certified:
            certifications.append('Minimal')
        
        if certifications:
            return ', '.join(certifications)
        return _('Aucune certification')
    certification_status.short_description = _('Certifications')
    
    def get_user_link(self, obj):
        """Ajoute un lien vers l'utilisateur"""
        if obj.user:
            url = reverse('admin:users_user_change', args=[obj.user.id])
            return format_html(
                '<a href="{}">{} ({})</a>',
                url,
                obj.user.get_full_name(),
                obj.user.email
            )
        return _('Aucun utilisateur')
    get_user_link.short_description = _('Utilisateur')
    
    def save_model(self, request, obj, form, change):
        """Surcharge pour gérer l'enregistrement du modèle"""
        # Lors de la création, s'assurer que le type d'utilisateur est cohérent
        if not change and obj.user:  # Nouveau profil
            obj.user.user_type = 'ACCOUNTANT'
            obj.user.save(update_fields=['user_type'])
        super().save_model(request, obj, form, change)