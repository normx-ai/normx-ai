# apps/accounting/admin/tiers_admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Q
from django.urls import reverse
from apps.accounting.models import Tiers


@admin.register(Tiers)
class TiersAdmin(admin.ModelAdmin):
    """Administration des tiers avec interface stylée"""

    list_display = [
        'code_colore',
        'raison_sociale_display',
        'type_badge',
        'compte_collectif_display',
        'contact_info',
        'solde_display',
        'statut_display'
    ]

    list_filter = [
        'type_tiers',
        'is_active',
        'is_bloque',
        ('created_at', admin.DateFieldListFilter),
        'ville',
        'pays'
    ]

    search_fields = [
        'code',
        'raison_sociale',
        'sigle',
        'numero_contribuable',
        'matricule',
        'email',
        'telephone'
    ]

    ordering = ['type_tiers', 'code']
    list_per_page = 25

    fieldsets = (
        ('🏢 Identification', {
            'fields': ('type_tiers', 'code', 'raison_sociale', 'sigle')
        }),
        ('📋 Informations légales', {
            'fields': ('numero_contribuable', 'rccm', 'matricule'),
            'classes': ('collapse',)
        }),
        ('📍 Coordonnées', {
            'fields': ('adresse', 'ville', 'pays', 'telephone', 'email')
        }),
        ('🏦 Informations bancaires', {
            'fields': ('banque', 'numero_compte_bancaire'),
            'classes': ('collapse',)
        }),
        ('💼 Conditions commerciales', {
            'fields': ('delai_paiement', 'plafond_credit', 'exonere_tva'),
            'classes': ('collapse',),
            'description': 'Applicable pour clients et fournisseurs'
        }),
        ('👤 Contact principal', {
            'fields': ('contact_principal', 'fonction_contact'),
            'classes': ('collapse',)
        }),
        ('📝 Notes et statut', {
            'fields': ('notes', 'is_active', 'is_bloque', 'motif_blocage')
        }),
        ('ℹ️ Informations système', {
            'fields': ('compte_collectif', 'created_at', 'updated_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ['code', 'compte_collectif', 'created_at', 'updated_at']

    actions = ['activer_tiers', 'desactiver_tiers', 'bloquer_tiers', 'debloquer_tiers']

    def get_fieldsets(self, request, obj=None):
        """Adapter les fieldsets selon le type de tiers"""
        fieldsets = super().get_fieldsets(request, obj)

        if obj:
            # Cacher le matricule sauf pour les employés
            if obj.type_tiers != 'EMPL':
                for fieldset in fieldsets:
                    if '📋 Informations légales' in fieldset[0]:
                        fields = list(fieldset[1]['fields'])
                        if 'matricule' in fields:
                            fields.remove('matricule')
                        fieldset[1]['fields'] = tuple(fields)

            # Cacher les conditions commerciales pour les employés
            if obj.type_tiers == 'EMPL':
                fieldsets = [fs for fs in fieldsets if '💼 Conditions commerciales' not in fs[0]]

        return fieldsets

    def code_colore(self, obj):
        """Affiche le code avec une couleur selon le type"""
        colors = {
            'FLOC': '#e74c3c',  # Rouge - Fournisseur local
            'FGRP': '#c0392b',  # Rouge foncé - Fournisseur groupe
            'CLOC': '#27ae60',  # Vert - Client local
            'CGRP': '#229954',  # Vert foncé - Client groupe
            'EMPL': '#3498db',  # Bleu - Employé
        }
        color = colors.get(obj.type_tiers, '#95a5a6')
        return format_html(
            '<span style="color: {}; font-weight: bold; font-family: monospace; font-size: 14px;">{}</span>',
            color,
            obj.code
        )

    code_colore.short_description = "Code"

    def raison_sociale_display(self, obj):
        """Affiche la raison sociale avec des icônes"""
        icon = ''
        if obj.type_tiers in ['FLOC', 'FGRP']:
            icon = '🏭'  # Fournisseur
        elif obj.type_tiers in ['CLOC', 'CGRP']:
            icon = '🛍️'  # Client
        elif obj.type_tiers == 'EMPL':
            icon = '👤'  # Employé

        display = f"{icon} <strong>{obj.raison_sociale}</strong>"
        if obj.sigle:
            display += f" ({obj.sigle})"
        if obj.type_tiers == 'EMPL' and obj.matricule:
            display += f" - Mat: {obj.matricule}"

        return format_html(display)

    raison_sociale_display.short_description = "Raison sociale"

    def type_badge(self, obj):
        """Badge coloré pour le type"""
        badges = {
            'FLOC': ('Fournisseur Local', '#e74c3c', 'white'),
            'FGRP': ('Fournisseur Groupe', '#c0392b', 'white'),
            'CLOC': ('Client Local', '#27ae60', 'white'),
            'CGRP': ('Client Groupe', '#229954', 'white'),
            'EMPL': ('Employé', '#3498db', 'white'),
        }

        label, bg_color, text_color = badges.get(obj.type_tiers, ('Autre', '#95a5a6', 'white'))

        return format_html(
            '<span style="background-color: {}; color: {}; padding: 3px 8px; '
            'border-radius: 4px; font-size: 11px; font-weight: bold;">{}</span>',
            bg_color,
            text_color,
            label
        )

    type_badge.short_description = "Type"

    def compte_collectif_display(self, obj):
        """Affiche le compte collectif avec style"""
        return format_html(
            '<span style="background-color: #ecf0f1; padding: 2px 6px; '
            'border-radius: 3px; font-family: monospace;">{}</span>',
            obj.compte_collectif.code
        )

    compte_collectif_display.short_description = "Collectif"

    def contact_info(self, obj):
        """Affiche les infos de contact principales"""
        infos = []

        if obj.telephone:
            infos.append(f'📱 {obj.telephone}')
        if obj.email:
            infos.append(f'✉️ {obj.email}')
        if obj.ville:
            infos.append(f'📍 {obj.ville}')

        if infos:
            return format_html('<br>'.join(infos))
        return format_html('<span style="color: #bdc3c7;">Aucun contact</span>')

    contact_info.short_description = "Contact"
    contact_info.allow_tags = True

    def solde_display(self, obj):
        """Affiche le solde comptable avec couleur"""
        solde = obj.solde_comptable  # Pour l'instant retourne 0

        if solde > 0:
            color = '#e74c3c' if obj.est_fournisseur else '#27ae60'
            signe = '+' if obj.est_client else ''
        elif solde < 0:
            color = '#27ae60' if obj.est_fournisseur else '#e74c3c'
            signe = ''
        else:
            color = '#95a5a6'
            signe = ''

        # Formater le montant séparément pour éviter les conflits
        montant_formate = "{:,.0f}".format(abs(solde))

        return format_html(
            '<span style="color: {}; font-weight: bold;">{}{} XAF</span>',
            color,
            signe,
            montant_formate
        )

    solde_display.short_description = "Solde"

    def statut_display(self, obj):
        """Affiche le statut avec des icônes"""
        statuts = []

        if obj.is_active:
            statuts.append('<span style="color: #27ae60;">✓ Actif</span>')
        else:
            statuts.append('<span style="color: #e74c3c;">✗ Inactif</span>')

        if obj.is_bloque:
            statuts.append('<span style="color: #e74c3c;">🔒 Bloqué</span>')

        if obj.exonere_tva:
            statuts.append('<span style="color: #f39c12;">📋 Exonéré TVA</span>')

        return format_html(' | '.join(statuts))

    statut_display.short_description = "Statut"

    def get_readonly_fields(self, request, obj=None):
        """Le code devient readonly après création"""
        readonly = list(self.readonly_fields)
        if obj:  # Modification
            readonly.append('type_tiers')
        return readonly

    # Actions personnalisées
    def activer_tiers(self, request, queryset):
        """Active les tiers sélectionnés"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f"✓ {updated} tiers activé(s) avec succès.")

    activer_tiers.short_description = "Activer les tiers sélectionnés"

    def desactiver_tiers(self, request, queryset):
        """Désactive les tiers sélectionnés"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f"✓ {updated} tiers désactivé(s) avec succès.")

    desactiver_tiers.short_description = "Désactiver les tiers sélectionnés"

    def bloquer_tiers(self, request, queryset):
        """Bloque les tiers sélectionnés"""
        for tiers in queryset:
            tiers.bloquer("Bloqué via l'administration")
        self.message_user(
            request,
            f"🔒 {queryset.count()} tiers bloqué(s) avec succès.",
            level='WARNING'
        )

    bloquer_tiers.short_description = "Bloquer les tiers sélectionnés"

    def debloquer_tiers(self, request, queryset):
        """Débloque les tiers sélectionnés"""
        for tiers in queryset:
            tiers.debloquer()
        self.message_user(
            request,
            f"🔓 {queryset.count()} tiers débloqué(s) avec succès."
        )

    debloquer_tiers.short_description = "Débloquer les tiers sélectionnés"

    def save_model(self, request, obj, form, change):
        """Enregistre l'utilisateur créateur"""
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    class Media:
        css = {
            'all': ('admin/css/custom_tiers.css',)
        }