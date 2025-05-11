# -*- coding: utf-8 -*-
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.urls import reverse

from ..models import Role, UserRole, AuditLog


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'description', 'parent', 'is_system')
    list_filter = ('is_system',)
    search_fields = ('name', 'code', 'description')

    fieldsets = (
        (None, {'fields': ('name', 'code', 'description')}),
        (_('Hiérarchie et permissions'), {
            'fields': ('parent', 'permissions'),
        }),
        (_('Statut'), {
            'fields': ('is_system',),
        }),
        (_('Dates'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    readonly_fields = ('created_at', 'updated_at')


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ('get_user_link', 'get_role_link', 'get_assigned_by', 'created_at')
    list_filter = ('role__name', 'created_at')
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'role__name', 'role__code')
    ordering = ('-created_at',)

    fieldsets = (
        (None, {'fields': ('user', 'role')}),
        (_('Attribution'), {
            'fields': ('assigned_by', 'created_at'),
        }),
    )
    readonly_fields = ('created_at',)
    
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
    
    def get_role_link(self, obj):
        """Ajoute un lien vers le rôle"""
        if obj.role:
            url = reverse('admin:users_role_change', args=[obj.role.id])
            if hasattr(obj.role, 'code'):
                return format_html(
                    '<a href="{}">{} ({})</a>',
                    url,
                    obj.role.name,
                    obj.role.code
                )
            else:
                return format_html(
                    '<a href="{}">{}</a>',
                    url,
                    obj.role.name
                )
        return _('Aucun rôle')
    get_role_link.short_description = _('Rôle')
    
    def get_assigned_by(self, obj):
        """Ajoute un lien vers l'assignateur"""
        if obj.assigned_by:
            url = reverse('admin:users_user_change', args=[obj.assigned_by.id])
            return format_html(
                '<a href="{}">{}</a>',
                url,
                obj.assigned_by.get_full_name()
            )
        return _('Système')
    get_assigned_by.short_description = _('Assigné par')
    
    def save_model(self, request, obj, form, change):
        """Surcharge pour définir l'assignateur lors de la création"""
        if not change:  # Nouvelle attribution
            obj.assigned_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'get_user_link', 'action', 'resource_type', 'resource_id', 'get_ip_address')
    list_filter = ('action', 'resource_type', 'timestamp')
    search_fields = (
        'user__email', 'user__first_name', 'user__last_name',
        'resource_type', 'resource_id', 'action', 'ip_address'
    )
    ordering = ('-timestamp',)
    date_hierarchy = 'timestamp'

    fieldsets = (
        (None, {'fields': ('user', 'action', 'timestamp')}),
        (_('Ressource'), {
            'fields': ('resource_type', 'resource_id', 'resource_representation'),
        }),
        (_('Détails'), {
            'fields': ('ip_address', 'user_agent', 'additional_data'),
            'classes': ('collapse',),
        }),
    )
    readonly_fields = ('timestamp', 'user', 'action', 'resource_type', 'resource_id',
                      'resource_representation', 'ip_address', 'user_agent', 'additional_data')

    actions = ['export_as_csv']

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
        return _('Système')
    get_user_link.short_description = _('Utilisateur')

    def get_ip_address(self, obj):
        """Affiche l'adresse IP de manière plus conviviale"""
        return obj.ip_address or _('Inconnue')
    get_ip_address.short_description = _('Adresse IP')

    def export_as_csv(self, request, queryset):
        """Exporte les logs d'audit sélectionnés au format CSV"""
        import csv
        from django.http import HttpResponse
        from datetime import datetime

        meta = self.model._meta
        field_names = [field.name for field in meta.fields]

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename={meta.verbose_name_plural}-{datetime.now().strftime("%Y%m%d-%H%M%S")}.csv'

        writer = csv.writer(response)
        writer.writerow(field_names)
        for obj in queryset:
            row = []
            for field in field_names:
                value = getattr(obj, field)
                # Convertir les valeurs complexes en chaînes
                if field == 'additional_data' and value:
                    import json
                    value = json.dumps(value)
                row.append(str(value) if value is not None else '')
            writer.writerow(row)

        return response
    export_as_csv.short_description = _("Exporter les logs sélectionnés en CSV")

    def has_add_permission(self, request):
        """Désactive l'ajout manuel de logs d'audit"""
        return False

    def has_change_permission(self, request, obj=None):
        """Désactive la modification des logs d'audit"""
        return False

    def has_delete_permission(self, request, obj=None):
        """Désactive la suppression des logs d'audit"""
        return False