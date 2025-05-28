# apps/accounting/serializers/exercices.py
"""
Serializers pour les exercices et périodes comptables OHADA
- ExerciceComptable : Exercices annuels
- PeriodeComptable : Périodes mensuelles
"""

from rest_framework import serializers
from django.utils import timezone
from django.db.models import Count, Q
from datetime import date, timedelta

from apps.accounting.models import ExerciceComptable, PeriodeComptable


class PeriodeComptableSerializer(serializers.ModelSerializer):
    """
    Serializer pour les périodes comptables

    Fonctionnalités :
    - Affichage du mois en français
    - Validation des dates
    - Statut d'ouverture/clôture
    - Statistiques d'utilisation
    """

    # Champs calculés
    mois_libelle = serializers.SerializerMethodField()
    periode_complete = serializers.SerializerMethodField()
    nb_ecritures = serializers.SerializerMethodField()
    peut_etre_cloturee = serializers.SerializerMethodField()
    jours_restants = serializers.SerializerMethodField()

    class Meta:
        model = PeriodeComptable
        fields = [
            'id',
            'exercice',
            'numero',
            'date_debut',
            'date_fin',
            'statut',
            'date_cloture',
            'cloture_par',
            'mois_libelle',
            'periode_complete',
            'nb_ecritures',
            'peut_etre_cloturee',
            'jours_restants'
        ]
        read_only_fields = ['numero', 'date_cloture', 'cloture_par']

    def get_mois_libelle(self, obj):
        """Retourne le nom du mois en français basé sur la date"""
        mois_noms = {
            1: 'Janvier', 2: 'Février', 3: 'Mars', 4: 'Avril',
            5: 'Mai', 6: 'Juin', 7: 'Juillet', 8: 'Août',
            9: 'Septembre', 10: 'Octobre', 11: 'Novembre', 12: 'Décembre'
        }
        return mois_noms.get(obj.date_debut.month, '')

    def get_periode_complete(self, obj):
        """Retourne le libellé complet de la période"""
        return f"{self.get_mois_libelle(obj)} {obj.date_debut.year}"

    def get_nb_ecritures(self, obj):
        """Nombre d'écritures dans cette période"""
        if hasattr(obj, 'ecritures'):
            return obj.ecritures.count()
        return 0

    def get_peut_etre_cloturee(self, obj):
        """Vérifie si la période peut être clôturée"""
        if obj.statut == 'CLOTUREE':
            return False

        # Une période peut être clôturée si on est après sa date de fin
        return timezone.now().date() > obj.date_fin

    def get_jours_restants(self, obj):
        """Nombre de jours avant la fin de la période"""
        if obj.statut == 'CLOTUREE':
            return 0

        delta = obj.date_fin - timezone.now().date()
        return max(0, delta.days)

    def validate(self, attrs):
        """Validations métier"""
        exercice = attrs.get('exercice', self.instance.exercice if self.instance else None)
        date_debut = attrs.get('date_debut', self.instance.date_debut if self.instance else None)
        date_fin = attrs.get('date_fin', self.instance.date_fin if self.instance else None)

        if exercice and date_debut and date_fin:
            # Vérifier que les dates sont dans l'exercice
            if date_debut < exercice.date_debut or date_fin > exercice.date_fin:
                raise serializers.ValidationError({
                    'date_debut': "Les dates doivent être comprises dans l'exercice"
                })

            # Vérifier la cohérence des dates
            if date_debut >= date_fin:
                raise serializers.ValidationError({
                    'date_fin': "La date de fin doit être postérieure à la date de début"
                })

        return attrs


class PeriodeComptableMinimalSerializer(serializers.ModelSerializer):
    """Serializer minimal pour les listes déroulantes"""

    periode_complete = serializers.SerializerMethodField()

    class Meta:
        model = PeriodeComptable
        fields = ['id', 'numero', 'date_debut', 'date_fin', 'periode_complete', 'statut']

    def get_periode_complete(self, obj):
        mois_noms = {
            1: 'Janvier', 2: 'Février', 3: 'Mars', 4: 'Avril',
            5: 'Mai', 6: 'Juin', 7: 'Juillet', 8: 'Août',
            9: 'Septembre', 10: 'Octobre', 11: 'Novembre', 12: 'Décembre'
        }
        mois = obj.date_debut.month
        annee = obj.date_debut.year
        return f"{mois_noms.get(mois, '')} {annee}"


class ExerciceComptableSerializer(serializers.ModelSerializer):
    """
    Serializer complet pour les exercices comptables

    Fonctionnalités :
    - Validation des dates et statuts
    - Génération automatique des périodes
    - Statistiques d'utilisation
    - Gestion de la clôture
    """

    # Relations
    periodes = PeriodeComptableMinimalSerializer(many=True, read_only=True)

    # Champs calculés
    duree_jours = serializers.SerializerMethodField()
    duree_mois = serializers.SerializerMethodField()
    progression_pourcent = serializers.SerializerMethodField()
    nb_periodes_cloturees = serializers.SerializerMethodField()
    nb_ecritures_total = serializers.SerializerMethodField()
    peut_etre_cloture = serializers.SerializerMethodField()
    statut_display = serializers.SerializerMethodField()

    class Meta:
        model = ExerciceComptable
        fields = [
            'id',
            'code',
            'libelle',
            'date_debut',
            'date_fin',
            'statut',
            'date_cloture_provisoire',
            'date_cloture_definitive',
            'is_premier_exercice',
            'report_a_nouveau_genere',
            'periodes',
            'duree_jours',
            'duree_mois',
            'progression_pourcent',
            'nb_periodes_cloturees',
            'nb_ecritures_total',
            'peut_etre_cloture',
            'statut_display',
            'created_at',
            'updated_at',
            'created_by'
        ]
        read_only_fields = [
            'date_cloture_provisoire',
            'date_cloture_definitive',
            'report_a_nouveau_genere',
            'created_at',
            'updated_at'
        ]

    def get_duree_jours(self, obj):
        """Durée de l'exercice en jours"""
        return (obj.date_fin - obj.date_debut).days + 1

    def get_duree_mois(self, obj):
        """Durée approximative en mois"""
        return round(self.get_duree_jours(obj) / 30.44)

    def get_progression_pourcent(self, obj):
        """Pourcentage de progression de l'exercice"""
        if obj.statut == 'CLOTURE':
            return 100

        today = timezone.now().date()
        if today < obj.date_debut:
            return 0
        elif today > obj.date_fin:
            return 100

        jours_ecoules = (today - obj.date_debut).days
        jours_total = self.get_duree_jours(obj)

        return round((jours_ecoules / jours_total) * 100, 1)

    def get_nb_periodes_cloturees(self, obj):
        """Nombre de périodes clôturées"""
        return obj.periodes.filter(statut='CLOTUREE').count()

    def get_nb_ecritures_total(self, obj):
        """Nombre total d'écritures dans l'exercice"""
        if hasattr(obj, 'ecritures'):
            return obj.ecritures.count()
        return 0

    def get_peut_etre_cloture(self, obj):
        """Vérifie si l'exercice peut être clôturé"""
        if obj.statut == 'CLOTURE':
            return False

        # Vérifier que toutes les périodes sont clôturées
        periodes_ouvertes = obj.periodes.exclude(statut='CLOTUREE').count()
        if periodes_ouvertes > 0:
            return False

        # Vérifier qu'on est après la date de fin
        return timezone.now().date() > obj.date_fin

    def get_statut_display(self, obj):
        """Statut formaté avec icônes"""
        statuts = {
            'OUVERT': '🟢 Ouvert',
            'CLOTURE': '🔴 Clôturé'
        }
        return statuts.get(obj.statut, obj.statut)

    def validate_libelle(self, value):
        """Validation du libellé"""
        if not value or len(value.strip()) < 4:
            raise serializers.ValidationError(
                "Le libellé doit contenir au moins 4 caractères"
            )
        return value.strip()

    def validate_date_debut(self, value):
        """Validation de la date de début"""
        # Pour un nouvel exercice, vérifier qu'il n'y a pas de chevauchement DE DATES
        if not self.instance:  # Création
            # Vérifier uniquement le chevauchement de dates, pas le statut
            exercices_chevauchants = ExerciceComptable.objects.filter(
                date_debut__lte=value,
                date_fin__gte=value
            )

            if exercices_chevauchants.exists():
                exercice = exercices_chevauchants.first()
                raise serializers.ValidationError(
                    f"La date chevauche avec l'exercice {exercice.libelle} "
                    f"({exercice.date_debut} - {exercice.date_fin})"
                )

        return value

    def validate(self, attrs):
        """Validations croisées"""
        date_debut = attrs.get('date_debut',
                               self.instance.date_debut if self.instance else None)
        date_fin = attrs.get('date_fin',
                             self.instance.date_fin if self.instance else None)

        if date_debut and date_fin:
            # Vérifier la cohérence des dates
            if date_debut >= date_fin:
                raise serializers.ValidationError({
                    'date_fin': "La date de fin doit être postérieure à la date de début"
                })

            # Vérifier la durée (généralement 12 mois, max 18 selon OHADA)
            duree_jours = (date_fin - date_debut).days + 1
            if duree_jours > 548:  # ~18 mois
                raise serializers.ValidationError({
                    'date_fin': "La durée de l'exercice ne peut excéder 18 mois (OHADA)"
                })

            # Vérifier le chevauchement complet (date début ET fin)
            if not self.instance:  # Création uniquement
                exercices_chevauchants = ExerciceComptable.objects.filter(
                    Q(date_debut__lte=date_fin, date_fin__gte=date_debut)
                )
                if exercices_chevauchants.exists():
                    exercice = exercices_chevauchants.first()
                    raise serializers.ValidationError({
                        'date_fin': f"Les dates chevauchent avec l'exercice {exercice.libelle}"
                    })

        # Validation du statut - Maximum 2 exercices ouverts
        statut = attrs.get('statut', self.instance.statut if self.instance else 'OUVERT')
        if statut == 'OUVERT':
            nb_ouverts = ExerciceComptable.objects.filter(statut='OUVERT')
            if self.instance:
                nb_ouverts = nb_ouverts.exclude(pk=self.instance.pk)

            if nb_ouverts.count() >= 2:
                raise serializers.ValidationError({
                    'statut': "Maximum 2 exercices peuvent être ouverts simultanément"
                })

        return attrs

    def create(self, validated_data):
        """Création avec génération automatique des périodes"""
        exercice = super().create(validated_data)

        # Générer les périodes mensuelles
        exercice.generer_periodes()

        return exercice


class ExerciceComptableMinimalSerializer(serializers.ModelSerializer):
    """Serializer minimal pour les listes déroulantes"""

    exercice_complet = serializers.SerializerMethodField()

    class Meta:
        model = ExerciceComptable
        fields = ['id', 'libelle', 'date_debut', 'date_fin', 'statut', 'exercice_complet']

    def get_exercice_complet(self, obj):
        return f"{obj.libelle} ({obj.date_debut.strftime('%d/%m/%Y')} - {obj.date_fin.strftime('%d/%m/%Y')})"


class ExerciceComptableStatsSerializer(serializers.ModelSerializer):
    """Serializer avec statistiques détaillées"""

    nb_periodes_total = serializers.SerializerMethodField()
    nb_periodes_ouvertes = serializers.SerializerMethodField()
    nb_periodes_cloturees = serializers.SerializerMethodField()
    nb_ecritures_brouillon = serializers.SerializerMethodField()
    nb_ecritures_validees = serializers.SerializerMethodField()
    montant_total_debits = serializers.SerializerMethodField()
    montant_total_credits = serializers.SerializerMethodField()
    ecart_debit_credit = serializers.SerializerMethodField()
    periodes_details = PeriodeComptableSerializer(source='periodes', many=True, read_only=True)

    class Meta:
        model = ExerciceComptable
        fields = [
            'id',
            'libelle',
            'date_debut',
            'date_fin',
            'statut',
            'nb_periodes_total',
            'nb_periodes_ouvertes',
            'nb_periodes_cloturees',
            'nb_ecritures_brouillon',
            'nb_ecritures_validees',
            'montant_total_debits',
            'montant_total_credits',
            'ecart_debit_credit',
            'periodes_details'
        ]

    def get_nb_periodes_total(self, obj):
        return obj.periodes.count()

    def get_nb_periodes_ouvertes(self, obj):
        return obj.periodes.filter(statut='OUVERTE').count()

    def get_nb_periodes_cloturees(self, obj):
        return obj.periodes.filter(statut='CLOTUREE').count()

    def get_nb_ecritures_brouillon(self, obj):
        if hasattr(obj, 'ecritures'):
            return obj.ecritures.filter(statut='BROUILLON').count()
        return 0

    def get_nb_ecritures_validees(self, obj):
        if hasattr(obj, 'ecritures'):
            return obj.ecritures.filter(statut='VALIDEE').count()
        return 0

    def get_montant_total_debits(self, obj):
        """Somme totale des débits de l'exercice"""
        if hasattr(obj, 'ecritures'):
            from django.db.models import Sum
            total = obj.ecritures.aggregate(
                total=Sum('lignes__montant_debit')
            )['total']
            return float(total or 0)
        return 0

    def get_montant_total_credits(self, obj):
        """Somme totale des crédits de l'exercice"""
        if hasattr(obj, 'ecritures'):
            from django.db.models import Sum
            total = obj.ecritures.aggregate(
                total=Sum('lignes__montant_credit')
            )['total']
            return float(total or 0)
        return 0

    def get_ecart_debit_credit(self, obj):
        """Écart entre débits et crédits (doit être 0)"""
        return self.get_montant_total_debits(obj) - self.get_montant_total_credits(obj)


class ClotureExerciceSerializer(serializers.Serializer):
    """
    Serializer pour l'action de clôture d'exercice
    Utilisé pour valider et exécuter la clôture
    """

    exercice_id = serializers.IntegerField()
    date_cloture = serializers.DateField(required=False)
    generer_a_nouveaux = serializers.BooleanField(default=True)
    nouvel_exercice_libelle = serializers.CharField(required=False, allow_blank=True)

    def validate_exercice_id(self, value):
        """Vérifier que l'exercice existe et peut être clôturé"""
        try:
            exercice = ExerciceComptable.objects.get(id=value)
        except ExerciceComptable.DoesNotExist:
            raise serializers.ValidationError("Exercice introuvable")

        if exercice.statut == 'CLOTURE':
            raise serializers.ValidationError("Cet exercice est déjà clôturé")

        # Vérifier que toutes les périodes sont clôturées
        periodes_ouvertes = exercice.periodes.exclude(statut='CLOTUREE').count()
        if periodes_ouvertes > 0:
            raise serializers.ValidationError(
                f"{periodes_ouvertes} période(s) sont encore ouvertes. "
                "Veuillez les clôturer avant de clôturer l'exercice."
            )

        return value

    def validate_date_cloture(self, value):
        """Validation de la date de clôture"""
        if value and value > timezone.now().date():
            raise serializers.ValidationError(
                "La date de clôture ne peut pas être dans le futur"
            )
        return value

    def validate(self, attrs):
        """Validations croisées"""
        exercice = ExerciceComptable.objects.get(id=attrs['exercice_id'])

        # Si pas de date fournie, utiliser la date du jour
        if 'date_cloture' not in attrs:
            attrs['date_cloture'] = timezone.now().date()

        # Vérifier que la date de clôture est après la fin de l'exercice
        if attrs['date_cloture'] < exercice.date_fin:
            raise serializers.ValidationError({
                'date_cloture': "La date de clôture doit être après la fin de l'exercice"
            })

        # Si génération des à-nouveaux, proposer un libellé pour le nouvel exercice
        if attrs['generer_a_nouveaux'] and not attrs.get('nouvel_exercice_libelle'):
            # Générer un libellé par défaut
            annee_suivante = exercice.date_fin.year + 1
            attrs['nouvel_exercice_libelle'] = str(annee_suivante)

        return attrs