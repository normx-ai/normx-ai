# apps/accounting/admin/journal_admin.py
from django.contrib import admin
from django.utils.html import format_html
from apps.accounting.models import Journal


@admin.register(Journal)
class JournalAdmin(admin.ModelAdmin):
    """Administration des journaux comptables"""

    list_display = [
        'code',
        'libelle',
        'type_display',
        'compte_contrepartie',
        'is_active_icon',
        'created_at'
    ]

    list_filter = ['type', 'is_active', ('created_at', admin.DateFieldListFilter)]
    search_fields = ['code', 'libelle']
    ordering = ['code']
    list_per_page = 25

    # Configuration du formulaire
    fieldsets = (
        ('Informations principales', {
            'fields': ('code', 'libelle', 'type')
        }),
        ('Configuration', {
            'fields': ('compte_contrepartie', 'is_active'),
            'classes': ('wide',)
        }),
        ('Informations système', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ('created_at', 'updated_at')
    autocomplete_fields = ['compte_contrepartie']

    # Actions personnalisées
    actions = ['activer_journaux', 'desactiver_journaux']

    def type_display(self, obj):
        """Affiche le type avec son libellé complet"""
        return f"{obj.type} - {obj.get_type_display()}"

    type_display.short_description = "Type de journal"

    def is_active_icon(self, obj):
        """Affiche une icône pour le statut actif/inactif"""
        if obj.is_active:
            return format_html(
                '<span style="color: green;">✓ Actif</span>'
            )
        return format_html(
            '<span style="color: red;">✗ Inactif</span>'
        )

    is_active_icon.short_description = "Statut"

    def activer_journaux(self, request, queryset):
        """Active les journaux sélectionnés"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} journal(aux) activé(s) avec succès.")

    activer_journaux.short_description = "Activer les journaux sélectionnés"

    def desactiver_journaux(self, request, queryset):
        """Désactive les journaux sélectionnés"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} journal(aux) désactivé(s) avec succès.")

    desactiver_journaux.short_description = "Désactiver les journaux sélectionnés"