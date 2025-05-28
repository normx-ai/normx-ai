# apps/accounting/admin/compte_admin.py
from django.contrib import admin
from apps.accounting.models import CompteOHADA


@admin.register(CompteOHADA)
class CompteOHADAAdmin(admin.ModelAdmin):
    """Administration des comptes OHADA avec fonctionnalités étendues"""

    list_display = ['code', 'libelle', 'classe', 'type', 'ref', 'is_active']
    list_filter = ['classe', 'type', 'is_active']
    search_fields = ['code', 'libelle']
    ordering = ['code']
    list_per_page = 50

    # Actions en masse
    actions = ['activer_comptes', 'desactiver_comptes']

    # Fieldsets pour une meilleure organisation du formulaire
    fieldsets = (
        ('Informations principales', {
            'fields': ('code', 'libelle', 'classe', 'type', 'ref')
        }),
        ('Statut', {
            'fields': ('is_active',)
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Grouper par classe pour une meilleure lisibilité
        return qs.order_by('classe', 'code')

    def activer_comptes(self, request, queryset):
        """Active les comptes sélectionnés"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} compte(s) activé(s) avec succès.")

    activer_comptes.short_description = "Activer les comptes sélectionnés"

    def desactiver_comptes(self, request, queryset):
        """Désactive les comptes sélectionnés"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} compte(s) désactivé(s) avec succès.")

    desactiver_comptes.short_description = "Désactiver les comptes sélectionnés"