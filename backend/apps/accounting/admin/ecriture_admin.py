# apps/accounting/admin/ecriture_admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse, path
from django.utils.safestring import mark_safe
from django.http import HttpResponseRedirect, JsonResponse
from django.contrib import messages
from django.shortcuts import get_object_or_404
from django.db.models import Sum
from decimal import Decimal
from apps.accounting.models import EcritureComptable, LigneEcriture


class LigneEcritureInline(admin.TabularInline):
    """
    Inline pour reproduire l'interface Sage exactement
    Grille avec colonnes : ☑ | Date(j) | Compte | Tiers | Pièce | Libellé | Débit | Crédit
    """
    model = LigneEcriture
    extra = 1
    min_num = 2  # Minimum 2 lignes pour une écriture équilibrée
    can_delete = False  # Désactiver la suppression Django par défaut

    fields = [
        'numero_ligne',
        'date_ligne',
        'compte',
        'tiers',
        'piece',
        'libelle',
        'montant_debit',
        'montant_credit'
    ]

    # Colonnes affichées dans la grille (style Sage)
    readonly_fields = []

    # Autocomplete pour performance
    autocomplete_fields = ['compte', 'tiers']

    # Désactiver les fonctionnalités Django par défaut
    show_change_link = False

    # CSS personnalisé pour ressembler à Sage
    class Media:
        css = {
            'all': ('admin/css/ecriture.css',)
        }
        js = ('admin/js/ecriture_equilibre.js',)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('compte', 'tiers')

    def has_delete_permission(self, request, obj=None):
        # Désactiver la suppression par défaut Django
        return False


@admin.register(EcritureComptable)
class EcritureComptableAdmin(admin.ModelAdmin):
    """
    Administration des écritures avec style Sage
    Interface unifiée en-tête + lignes comme dans Sage
    """

    list_display = [
        'numero_colore',
        'journal_badge',
        'date_ecriture',
        'libelle_display',
        'montant_display',
        'equilibre_display',
        'statut_display',
        'actions_rapides'
    ]

    list_filter = [
        'statut',
        'journal',
        'exercice',
        ('date_ecriture', admin.DateFieldListFilter),
        'is_equilibree'
    ]

    search_fields = [
        'numero',
        'libelle',
        'reference',
        'lignes__piece',
        'lignes__libelle'
    ]

    ordering = ['-date_ecriture', '-numero']
    list_per_page = 25

    # Fieldsets organisés comme Sage
    fieldsets = (
        ('📋 En-tête d\'écriture', {
            'fields': (
                ('journal', 'numero'),
                ('date_ecriture', 'date_piece'),
                'libelle',
                'reference'
            ),
            'classes': ('wide',)
        }),
        ('📊 État de l\'écriture', {
            'fields': (
                ('statut', 'is_equilibree'),
                ('montant_total', 'difference_display'),
                ('date_validation', 'validee_par')
            ),
            'classes': ('collapse',)
        }),
        ('🗓️ Période comptable', {
            'fields': (
                ('exercice', 'periode'),
            ),
            'classes': ('collapse',)
        }),
        ('ℹ️ Informations système', {
            'fields': (
                ('created_at', 'updated_at'),
                'created_by'
            ),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = [
        'numero',
        'is_equilibree',
        'montant_total',
        'difference_display',
        'date_validation',
        'created_at',
        'updated_at'
    ]

    # Inline pour les lignes (style Sage)
    inlines = [LigneEcritureInline]

    # Actions personnalisées
    actions = ['valider_ecritures', 'dupliquer_ecritures', 'calculer_equilibre']

    def get_urls(self):
        """URLs personnalisées pour actions AJAX"""
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:ecriture_id>/valider/',
                self.admin_site.admin_view(self.valider_ecriture_view),
                name='accounting_ecriturecomptable_valider'
            ),
            path(
                '<int:ecriture_id>/dupliquer/',
                self.admin_site.admin_view(self.dupliquer_ecriture_view),
                name='accounting_ecriturecomptable_dupliquer'
            ),
            path(
                'equilibre-ajax/',
                self.admin_site.admin_view(self.equilibre_ajax_view),
                name='accounting_ecriturecomptable_equilibre_ajax'
            ),
        ]
        return custom_urls + urls

    def valider_ecriture_view(self, request, ecriture_id):
        """Vue pour valider une écriture"""
        ecriture = get_object_or_404(EcritureComptable, pk=ecriture_id)
        try:
            ecriture.valider(user=request.user)
            messages.success(
                request,
                f"✓ L'écriture {ecriture.numero} a été validée avec succès."
            )
        except Exception as e:
            messages.error(request, f"❌ Erreur: {str(e)}")

        return HttpResponseRedirect(reverse('admin:accounting_ecriturecomptable_changelist'))

    def dupliquer_ecriture_view(self, request, ecriture_id):
        """Vue pour dupliquer une écriture"""
        ecriture = get_object_or_404(EcritureComptable, pk=ecriture_id)
        try:
            nouvelle_ecriture = ecriture.dupliquer()
            messages.success(
                request,
                f"✓ Écriture dupliquée: {nouvelle_ecriture.numero}"
            )
            # Rediriger vers l'édition de la nouvelle écriture
            return HttpResponseRedirect(
                reverse('admin:accounting_ecriturecomptable_change', args=[nouvelle_ecriture.pk])
            )
        except Exception as e:
            messages.error(request, f"❌ Erreur: {str(e)}")
            return HttpResponseRedirect(reverse('admin:accounting_ecriturecomptable_changelist'))

    def equilibre_ajax_view(self, request):
        """Vue AJAX pour calculer l'équilibre en temps réel"""
        if request.method == 'POST':
            ecriture_id = request.POST.get('ecriture_id')
            if ecriture_id:
                try:
                    ecriture = EcritureComptable.objects.get(pk=ecriture_id)
                    ecriture._calculer_equilibre()
                    return JsonResponse({
                        'success': True,
                        'total_debit': float(ecriture.total_debit),
                        'total_credit': float(ecriture.total_credit),
                        'difference': float(ecriture.difference),
                        'is_equilibree': ecriture.is_equilibree
                    })
                except Exception as e:
                    return JsonResponse({'success': False, 'error': str(e)})

        return JsonResponse({'success': False, 'error': 'Méthode non autorisée'})

    # Affichages personnalisés pour la liste
    def numero_colore(self, obj):
        """Numéro avec couleur selon le statut"""
        colors = {
            'BROUILLON': '#f39c12',  # Orange
            'VALIDEE': '#27ae60',  # Vert
            'CLOTUREE': '#95a5a6'  # Gris
        }
        color = colors.get(obj.statut, '#000000')

        return format_html(
            '<span style="color: {}; font-weight: bold; font-family: monospace;">{}</span>',
            color,
            obj.numero
        )

    numero_colore.short_description = "Numéro"

    def journal_badge(self, obj):
        """Badge du journal style Sage"""
        return format_html(
            '<span style="background: #3498db; color: white; padding: 2px 6px; '
            'border-radius: 3px; font-size: 11px; font-weight: bold;">{}</span>',
            obj.journal.code
        )

    journal_badge.short_description = "Journal"

    def libelle_display(self, obj):
        """Libellé avec référence"""
        display = f"<strong>{obj.libelle}</strong>"
        if obj.reference:
            display += f"<br><small style='color: #7f8c8d;'>Réf: {obj.reference}</small>"
        return format_html(display)

    libelle_display.short_description = "Libellé"

    def montant_display(self, obj):
        """Montant total formaté"""
        return format_html(
            '<span style="font-family: monospace; font-weight: bold;">{:,.2f} XAF</span>',
            obj.montant_total
        )

    montant_display.short_description = "Montant"

    def equilibre_display(self, obj):
        """Indicateur d'équilibre style Sage"""
        if obj.is_equilibree:
            return format_html(
                '<span style="color: #27ae60; font-weight: bold;">✓ Équilibrée</span>'
            )
        else:
            difference = abs(obj.difference)
            return format_html(
                '<span style="color: #e74c3c; font-weight: bold;">❌ Écart: {:,.2f}</span>',
                difference
            )

    equilibre_display.short_description = "Équilibre"

    def statut_display(self, obj):
        """Statut avec icône"""
        icons = {
            'BROUILLON': '📝',
            'VALIDEE': '✅',
            'CLOTUREE': '🔒'
        }
        colors = {
            'BROUILLON': '#f39c12',
            'VALIDEE': '#27ae60',
            'CLOTUREE': '#95a5a6'
        }

        icon = icons.get(obj.statut, '❓')
        color = colors.get(obj.statut, '#000000')

        return format_html(
            '{} <span style="color: {};">{}</span>',
            icon,
            color,
            obj.get_statut_display()
        )

    statut_display.short_description = "Statut"

    def actions_rapides(self, obj):
        """Boutons d'action rapide style Sage"""
        buttons = []

        if obj.statut == 'BROUILLON':
            if obj.is_equilibree:
                # Bouton Valider
                url = reverse('admin:accounting_ecriturecomptable_valider', args=[obj.pk])
                buttons.append(
                    f'<a href="{url}" class="button" style="padding: 4px 8px; background: #27ae60; '
                    f'color: white; text-decoration: none; border-radius: 3px; font-size: 11px;">Valider</a>'
                )

            # Bouton Dupliquer
            url = reverse('admin:accounting_ecriturecomptable_dupliquer', args=[obj.pk])
            buttons.append(
                f'<a href="{url}" class="button" style="padding: 4px 8px; background: #3498db; '
                f'color: white; text-decoration: none; border-radius: 3px; font-size: 11px;">Dupliquer</a>'
            )

        if not buttons:
            return format_html('<span style="color: #bdc3c7;">-</span>')

        return mark_safe(' '.join(buttons))

    actions_rapides.short_description = "Actions"

    def difference_display(self, obj):
        """Affiche la différence débit-crédit"""
        diff = obj.difference
        if diff == 0:
            return format_html('<span style="color: #27ae60;">0,00</span>')
        else:
            color = '#e74c3c'
            return format_html(
                '<span style="color: {};">{:,.2f}</span>',
                color,
                diff
            )

    difference_display.short_description = "Différence"

    # Actions en masse
    def valider_ecritures(self, request, queryset):
        """Valide les écritures sélectionnées"""
        validees = 0
        erreurs = 0

        for ecriture in queryset.filter(statut='BROUILLON'):
            try:
                ecriture.valider(user=request.user)
                validees += 1
            except Exception as e:
                erreurs += 1
                self.message_user(
                    request,
                    f"Erreur {ecriture.numero}: {str(e)}",
                    level='ERROR'
                )

        if validees > 0:
            self.message_user(
                request,
                f"✓ {validees} écriture(s) validée(s) avec succès."
            )

    valider_ecritures.short_description = "Valider les écritures sélectionnées"

    def dupliquer_ecritures(self, request, queryset):
        """Duplique les écritures sélectionnées"""
        dupliquees = 0

        for ecriture in queryset:
            try:
                nouvelle = ecriture.dupliquer()
                dupliquees += 1
            except Exception as e:
                self.message_user(
                    request,
                    f"Erreur {ecriture.numero}: {str(e)}",
                    level='ERROR'
                )

        if dupliquees > 0:
            self.message_user(
                request,
                f"✓ {dupliquees} écriture(s) dupliquée(s) avec succès."
            )

    dupliquer_ecritures.short_description = "Dupliquer les écritures sélectionnées"

    def calculer_equilibre(self, request, queryset):
        """Recalcule l'équilibre des écritures"""
        for ecriture in queryset:
            ecriture._calculer_equilibre()

        self.message_user(
            request,
            f"✓ Équilibre recalculé pour {queryset.count()} écriture(s)."
        )

    calculer_equilibre.short_description = "Recalculer l'équilibre"

    def save_model(self, request, obj, form, change):
        """Enregistre l'utilisateur créateur"""
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    def get_readonly_fields(self, request, obj=None):
        """Champs readonly selon le statut"""
        readonly = list(self.readonly_fields)

        if obj and obj.statut == 'VALIDEE':
            # Écriture validée : seules les métadonnées sont modifiables
            readonly.extend([
                'journal', 'date_ecriture', 'date_piece',
                'libelle', 'reference', 'exercice', 'periode'
            ])
        elif obj and obj.statut == 'CLOTUREE':
            # Écriture clôturée : tout en readonly sauf consultation
            readonly.extend([
                'journal', 'date_ecriture', 'date_piece',
                'libelle', 'reference', 'exercice', 'periode', 'statut'
            ])

        return readonly

    class Media:
        css = {
            'all': ('admin/css/ecriture.css',)
        }
        js = ('admin/js/ecriture_equilibre.js',)


@admin.register(LigneEcriture)
class LigneEcritureAdmin(admin.ModelAdmin):
    """
    Administration des lignes (pour consultation détaillée)
    """

    list_display = [
        'ecriture_numero',
        'numero_ligne',
        'compte_display',
        'tiers_display',
        'piece',
        'libelle_court',
        'montant_debit',
        'montant_credit',
        'sens_display'
    ]

    list_filter = [
        'ecriture__journal',
        'ecriture__statut',
        'compte__classe',
        ('ecriture__date_ecriture', admin.DateFieldListFilter),
        'is_lettree'
    ]

    search_fields = [
        'ecriture__numero',
        'compte__code',
        'compte__libelle',
        'tiers__code',
        'tiers__raison_sociale',
        'piece',
        'libelle'
    ]

    ordering = ['-ecriture__date_ecriture', 'ecriture', 'numero_ligne']

    def ecriture_numero(self, obj):
        return obj.ecriture.numero

    ecriture_numero.short_description = "Écriture"

    def compte_display(self, obj):
        return f"{obj.compte.code} - {obj.compte.libelle[:30]}"

    compte_display.short_description = "Compte"

    def tiers_display(self, obj):
        if obj.tiers:
            return f"{obj.tiers.code} - {obj.tiers.raison_sociale[:20]}"
        return "-"

    tiers_display.short_description = "Tiers"

    def libelle_court(self, obj):
        return obj.libelle[:40] + "..." if len(obj.libelle) > 40 else obj.libelle

    libelle_court.short_description = "Libellé"

    def sens_display(self, obj):
        if obj.montant_debit > 0:
            return format_html('<span style="color: #e74c3c;">DÉBIT</span>')
        else:
            return format_html('<span style="color: #27ae60;">CRÉDIT</span>')

    sens_display.short_description = "Sens"

