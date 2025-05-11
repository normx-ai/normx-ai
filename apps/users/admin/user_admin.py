# -*- coding: utf-8 -*-
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.urls import reverse

from ..models import User, UserType


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('email', 'first_name', 'last_name', 'user_type_display', 'is_active', 'is_verified', 'is_staff')
    list_filter = ('user_type', 'is_active', 'is_verified', 'is_staff', 'is_superuser', 'date_joined')
    search_fields = ('email', 'first_name', 'last_name', 'phone_number')
    ordering = ('-date_joined',)
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Informations personnelles'), {'fields': ('first_name', 'last_name', 'phone_number')}),
        (_('Type et profil'), {'fields': ('user_type', 'get_profile_link')}),
        (_('Permissions'), {
            'fields': ('is_active', 'is_verified', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_('Sécurité'), {
            'fields': ('failed_login_attempts', 'locked_until', 'mfa_enabled'),
            'classes': ('collapse',),
        }),
        (_('Dates importantes'), {'fields': ('last_login', 'date_joined')}),
    )
    readonly_fields = ('last_login', 'date_joined', 'get_profile_link')
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'user_type', 'is_active', 'is_staff'),
        }),
    )
    
    actions = ['unlock_accounts', 'activate_users', 'deactivate_users', 'export_users_as_csv']
    
    def user_type_display(self, obj):
        return obj.get_user_type_display()
    user_type_display.short_description = _("Type d'utilisateur")
    
    def get_profile_link(self, obj):
        """Ajoute un lien vers le profil spécifique de l'utilisateur"""
        if obj.user_type == UserType.COMPANY and hasattr(obj, 'company_profile'):
            url = reverse('admin:users_companyprofile_change', args=[obj.company_profile.id])
            return format_html('<a href="{}">{}</a>', url, _('Profil entreprise'))
        elif obj.user_type == UserType.ACCOUNTANT and hasattr(obj, 'accountant_profile'):
            url = reverse('admin:users_accountantprofile_change', args=[obj.accountant_profile.id])
            return format_html('<a href="{}">{}</a>', url, _('Profil expert-comptable'))
        return _('Aucun profil')
    get_profile_link.short_description = _('Profil')
    
    def unlock_accounts(self, request, queryset):
        """Action pour débloquer des comptes verrouillés"""
        updated = 0
        for user in queryset:
            if user.locked_until is not None:
                user.unlock_account()
                updated += 1
        
        self.message_user(
            request,
            _("%(count)d compte(s) débloqué(s) avec succès.") % {'count': updated}
        )
    unlock_accounts.short_description = _("Débloquer les comptes sélectionnés")
    
    def activate_users(self, request, queryset):
        """Action pour activer des utilisateurs"""
        queryset.update(is_active=True)
        self.message_user(
            request,
            _("%(count)d utilisateur(s) activé(s) avec succès.") % {'count': queryset.count()}
        )
    activate_users.short_description = _("Activer les utilisateurs sélectionnés")
    
    def deactivate_users(self, request, queryset):
        """Action pour désactiver des utilisateurs"""
        queryset.update(is_active=False)
        self.message_user(
            request,
            _("%(count)d utilisateur(s) désactivé(s) avec succès.") % {'count': queryset.count()}
        )
    deactivate_users.short_description = _("Désactiver les utilisateurs sélectionnés")

    def export_users_as_csv(self, request, queryset):
        """Exporte les utilisateurs sélectionnés au format CSV"""
        import csv
        from django.http import HttpResponse
        from datetime import datetime

        # Champs à exporter (éviter les informations sensibles comme les mots de passe)
        field_names = ['id', 'email', 'first_name', 'last_name', 'phone_number',
                       'user_type', 'is_active', 'is_verified', 'is_staff', 'date_joined', 'last_login']

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename=utilisateurs-{datetime.now().strftime("%Y%m%d-%H%M%S")}.csv'

        writer = csv.writer(response)
        writer.writerow(field_names)
        for obj in queryset:
            row = []
            for field in field_names:
                value = getattr(obj, field)
                row.append(str(value) if value is not None else '')
            writer.writerow(row)

        return response
    export_users_as_csv.short_description = _("Exporter les utilisateurs sélectionnés en CSV")