from django.contrib import admin
from django.db import connection
from .models import Tenant, Domain, PlanFeature, PlanLimit


class PublicSchemaOnlyAdmin(admin.ModelAdmin):
    """Admin qui s'affiche uniquement dans le schéma public"""
    def has_module_permission(self, request):
        return connection.schema_name == 'public'


@admin.register(Tenant)
class TenantAdmin(PublicSchemaOnlyAdmin):
    list_display = ['name', 'tenant_type', 'plan', 'created_on']
    list_filter = ['tenant_type', 'plan', 'created_on']
    search_fields = ['name', 'email']
    readonly_fields = ['created_on']


@admin.register(Domain)
class DomainAdmin(PublicSchemaOnlyAdmin):
    list_display = ['domain', 'tenant', 'is_primary']
    list_filter = ['is_primary']
    search_fields = ['domain', 'tenant__name']


@admin.register(PlanFeature)
class PlanFeatureAdmin(PublicSchemaOnlyAdmin):
    list_display = ['name', 'code', 'description']
    search_fields = ['name', 'code']


@admin.register(PlanLimit)
class PlanLimitAdmin(PublicSchemaOnlyAdmin):
    list_display = ['plan_type', 'max_users', 'max_enterprises', 'max_ai_calls', 'storage_gb']
    filter_horizontal = ['features']