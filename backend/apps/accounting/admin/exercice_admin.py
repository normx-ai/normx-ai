# apps/accounting/admin/exercice_admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse, path
from django.utils.safestring import mark_safe
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.shortcuts import get_object_or_404
from apps.accounting.models import ExerciceComptable, PeriodeComptable


class PeriodeComptableInline(admin.TabularInline):
    """Inline pour afficher les périodes dans l'exercice"""
    model = PeriodeComptable
    extra = 0
    fields = ['numero', 'date_debut', 'date_fin', 'statut', 'date_cloture']
    readonly_fields = ['numero', 'date_debut', 'date_fin', 'date_cloture']
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(ExerciceComptable)
class ExerciceComptableAdmin(admin.ModelAdmin):
    """Administration des exercices comptables"""

    list_display = [
        'code',
        'libelle',
        'periode_display',
        'statut_display',
        'jours_restants_display',
        'actions_buttons'  # Changé de actions_display
    ]

    list_filter = ['statut', 'is_premier_exercice', 'date_debut']
    search_fields = ['code', 'libelle']
    ordering = ['-date_debut']

    fieldsets = (
        ('Identification', {
            'fields': ('code', 'libelle', 'is_premier_exercice')
        }),
        ('Période', {
            'fields': ('date_debut', 'date_fin'),
            'description': "L'exercice dure généralement 12 mois (du 01/01 au 31/12)"
        }),
        ('Statut et Clôture', {
            'fields': (
                'statut',
                'date_cloture_provisoire',
                'date_cloture_definitive',
                'date_limite_cloture_display',
                'jours_restants_display'
            )
        }),
        ('Report à nouveau', {
            'fields': ('report_a_nouveau_genere', 'date_generation_an'),
            'classes': ('collapse',)
        }),
        ('Informations système', {
            'fields': ('created_at', 'updated_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = [
        'date_limite_cloture_display',
        'jours_restants_display',
        'created_at',
        'updated_at',
        'date_generation_an'
    ]

    inlines = [PeriodeComptableInline]

    actions = ['ouvrir_exercices', 'cloturer_provisoirement', 'generer_periodes']

    def get_urls(self):
        """Ajoute des URLs personnalisées pour les actions"""
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:exercice_id>/ouvrir/',
                self.admin_site.admin_view(self.ouvrir_exercice_view),
                name='accounting_exercicecomptable_ouvrir'
            ),
            path(
                '<int:exercice_id>/cloturer-provisoire/',
                self.admin_site.admin_view(self.cloturer_provisoire_view),
                name='accounting_exercicecomptable_cloturer_provisoire'
            ),
            path(
                '<int:exercice_id>/cloturer-definitive/',
                self.admin_site.admin_view(self.cloturer_definitive_view),
                name='accounting_exercicecomptable_cloturer_definitive'
            ),
        ]
        return custom_urls + urls

    def ouvrir_exercice_view(self, request, exercice_id):
        """Vue pour ouvrir un exercice"""
        exercice = get_object_or_404(ExerciceComptable, pk=exercice_id)
        try:
            nb_periodes_avant = exercice.periodes.count()
            exercice.ouvrir()
            nb_periodes_apres = exercice.periodes.count()
            nb_periodes_creees = nb_periodes_apres - nb_periodes_avant

            message = f"L'exercice {exercice.code} a été ouvert avec succès."
            if nb_periodes_creees > 0:
                message += f" {nb_periodes_creees} périodes mensuelles ont été créées automatiquement."

            messages.success(request, message)
        except Exception as e:
            messages.error(request, str(e))

        return HttpResponseRedirect(reverse('admin:accounting_exercicecomptable_changelist'))

    def cloturer_provisoire_view(self, request, exercice_id):
        """Vue pour clôturer provisoirement un exercice"""
        exercice = get_object_or_404(ExerciceComptable, pk=exercice_id)
        try:
            exercice.cloturer_provisoirement()
            messages.success(request, f"L'exercice {exercice.code} est en clôture provisoire.")
        except Exception as e:
            messages.error(request, str(e))

        return HttpResponseRedirect(reverse('admin:accounting_exercicecomptable_changelist'))

    def cloturer_definitive_view(self, request, exercice_id):
        """Vue pour clôturer définitivement un exercice"""
        exercice = get_object_or_404(ExerciceComptable, pk=exercice_id)
        try:
            exercice.cloturer_definitivement()
            messages.success(request, f"L'exercice {exercice.code} a été clôturé définitivement.")
        except Exception as e:
            messages.error(request, str(e))

        return HttpResponseRedirect(reverse('admin:accounting_exercicecomptable_changelist'))

    def periode_display(self, obj):
        """Affiche la période de l'exercice"""
        return f"Du {obj.date_debut.strftime('%d/%m/%Y')} au {obj.date_fin.strftime('%d/%m/%Y')}"

    periode_display.short_description = "Période"

    def statut_display(self, obj):
        """Affiche le statut avec une couleur"""
        colors = {
            'PREPARATION': 'gray',
            'OUVERT': 'green',
            'CLOTURE_PROVISOIRE': 'orange',
            'CLOTURE': 'red',
            'ARCHIVE': 'black'
        }
        color = colors.get(obj.statut, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_statut_display()
        )

    statut_display.short_description = "Statut"

    def date_limite_cloture_display(self, obj):
        """Affiche la date limite de clôture"""
        if obj.date_limite_cloture:
            return obj.date_limite_cloture.strftime('%d/%m/%Y')
        return "-"

    date_limite_cloture_display.short_description = "Date limite de clôture"

    def jours_restants_display(self, obj):
        """Affiche les jours restants pour clôturer"""
        if obj.statut in ['CLOTURE', 'ARCHIVE']:
            return format_html('<span style="color: green;">✓ Clôturé</span>')

        jours = obj.jours_restants_cloture
        if jours is None:
            return "-"

        if jours > 90:
            color = 'green'
        elif jours > 30:
            color = 'orange'
        else:
            color = 'red'

        return format_html(
            '<span style="color: {};">{} jours</span>',
            color,
            jours
        )

    jours_restants_display.short_description = "Délai de clôture"

    def actions_buttons(self, obj):
        """Affiche les boutons d'action fonctionnels"""
        buttons = []

        if obj.statut == 'PREPARATION':
            url = reverse('admin:accounting_exercicecomptable_ouvrir', args=[obj.pk])
            buttons.append(
                f'<a href="{url}" class="button" style="padding: 5px 10px; background: #417690; color: white; text-decoration: none; border-radius: 4px;">Ouvrir</a>'
            )
        elif obj.statut == 'OUVERT' and obj.is_cloture_possible:
            url = reverse('admin:accounting_exercicecomptable_cloturer_provisoire', args=[obj.pk])
            buttons.append(
                f'<a href="{url}" class="button" style="padding: 5px 10px; background: #ffa500; color: white; text-decoration: none; border-radius: 4px;">Clôture provisoire</a>'
            )
        elif obj.statut == 'CLOTURE_PROVISOIRE':
            url = reverse('admin:accounting_exercicecomptable_cloturer_definitive', args=[obj.pk])
            buttons.append(
                f'<a href="{url}" class="button" style="padding: 5px 10px; background: #dc3545; color: white; text-decoration: none; border-radius: 4px;">Clôture définitive</a>'
            )
        elif obj.statut == 'CLOTURE' and not obj.report_a_nouveau_genere:
            buttons.append(
                '<span style="color: green;">✓ Clôturé - À Nouveaux à générer</span>'
            )
        else:
            return format_html('<span style="color: gray;">-</span>')

        return mark_safe(' '.join(buttons))

    actions_buttons.short_description = "Actions"
    actions_buttons.allow_tags = True

    def ouvrir_exercices(self, request, queryset):
        """Action pour ouvrir les exercices sélectionnés"""
        for exercice in queryset:
            try:
                exercice.ouvrir()
                self.message_user(
                    request,
                    f"L'exercice {exercice.code} a été ouvert avec succès."
                )
            except Exception as e:
                self.message_user(
                    request,
                    f"Erreur pour l'exercice {exercice.code}: {str(e)}",
                    level='ERROR'
                )

    ouvrir_exercices.short_description = "Ouvrir les exercices sélectionnés"

    def cloturer_provisoirement(self, request, queryset):
        """Action pour clôturer provisoirement"""
        for exercice in queryset:
            try:
                exercice.cloturer_provisoirement()
                self.message_user(
                    request,
                    f"L'exercice {exercice.code} est en clôture provisoire."
                )
            except Exception as e:
                self.message_user(
                    request,
                    f"Erreur pour l'exercice {exercice.code}: {str(e)}",
                    level='ERROR'
                )

    cloturer_provisoirement.short_description = "Clôture provisoire"

    def generer_periodes(self, request, queryset):
        """Génère automatiquement les 12 périodes mensuelles"""
        for exercice in queryset:
            if exercice.periodes.exists():
                self.message_user(
                    request,
                    f"L'exercice {exercice.code} a déjà des périodes.",
                    level='WARNING'
                )
                continue

            # Générer les 12 mois
            from datetime import date
            from dateutil.relativedelta import relativedelta

            for mois in range(1, 13):
                date_debut = date(exercice.date_debut.year, mois, 1)
                if mois == 12:
                    date_fin = date(exercice.date_debut.year, 12, 31)
                else:
                    date_fin = date(exercice.date_debut.year, mois + 1, 1) - relativedelta(days=1)

                PeriodeComptable.objects.create(
                    exercice=exercice,
                    numero=mois,
                    date_debut=date_debut,
                    date_fin=date_fin
                )

            self.message_user(
                request,
                f"12 périodes créées pour l'exercice {exercice.code}."
            )

    generer_periodes.short_description = "Générer les périodes mensuelles"

    def save_model(self, request, obj, form, change):
        if not change:  # Nouvelle création
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(PeriodeComptable)
class PeriodeComptableAdmin(admin.ModelAdmin):
    """Administration des périodes comptables"""

    list_display = [
        '__str__',
        'exercice',
        'periode_display',
        'statut_display',
        'date_cloture',
        'cloture_par'
    ]

    list_filter = ['statut', 'exercice', 'numero']
    ordering = ['-exercice__date_debut', 'numero']

    readonly_fields = ['date_cloture', 'cloture_par']

    actions = ['cloturer_periodes', 'verrouiller_periodes']

    def periode_display(self, obj):
        """Affiche la période"""
        return f"Du {obj.date_debut.strftime('%d/%m')} au {obj.date_fin.strftime('%d/%m')}"

    periode_display.short_description = "Période"

    def statut_display(self, obj):
        """Affiche le statut avec une couleur"""
        colors = {
            'OUVERTE': 'green',
            'CLOTUREE': 'orange',
            'VERROUILLEE': 'red'
        }
        color = colors.get(obj.statut, 'black')
        icon = '🔓' if obj.statut == 'OUVERTE' else ('🔒' if obj.statut == 'VERROUILLEE' else '⏸')
        return format_html(
            '{} <span style="color: {};">{}</span>',
            icon,
            color,
            obj.get_statut_display()
        )

    statut_display.short_description = "Statut"

    def cloturer_periodes(self, request, queryset):
        """Clôture les périodes sélectionnées"""
        for periode in queryset.order_by('exercice', 'numero'):
            try:
                periode.cloturer(user=request.user)
                self.message_user(
                    request,
                    f"Période {periode} clôturée avec succès."
                )
            except Exception as e:
                self.message_user(
                    request,
                    f"Erreur pour {periode}: {str(e)}",
                    level='ERROR'
                )

    cloturer_periodes.short_description = "Clôturer les périodes"

    def verrouiller_periodes(self, request, queryset):
        """Verrouille les périodes sélectionnées"""
        for periode in queryset:
            try:
                periode.verrouiller()
                self.message_user(
                    request,
                    f"Période {periode} verrouillée avec succès."
                )
            except Exception as e:
                self.message_user(
                    request,
                    f"Erreur pour {periode}: {str(e)}",
                    level='ERROR'
                )

    verrouiller_periodes.short_description = "Verrouiller les périodes"