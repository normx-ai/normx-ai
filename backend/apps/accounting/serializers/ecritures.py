# apps/accounting/serializers/ecritures.py
"""
Serializers pour les écritures comptables OHADA
- EcritureComptable : En-tête des écritures
- LigneEcriture : Lignes de débit/crédit
- Validations métier OHADA
"""

from rest_framework import serializers
from django.db import transaction
from django.db.models import Sum, Q
from django.utils import timezone
from decimal import Decimal
import re

from apps.accounting.models import (
    EcritureComptable, LigneEcriture,
    Journal, ExerciceComptable, PeriodeComptable,
    CompteOHADA, Tiers
)
from .base import (
    JournalMinimalSerializer,
    CompteOHADAMinimalSerializer
)
from .tiers import TiersMinimalSerializer
from .exercices import (
    ExerciceComptableMinimalSerializer,
    PeriodeComptableMinimalSerializer
)


class LigneEcritureSerializer(serializers.ModelSerializer):
    """
    Serializer pour les lignes d'écriture comptable

    Règles OHADA :
    - Soit débit, soit crédit (jamais les deux)
    - Montant toujours positif
    - Compte et libellé obligatoires
    - Tiers optionnel selon le compte
    """

    # Relations en lecture
    compte_detail = CompteOHADAMinimalSerializer(source='compte', read_only=True)
    tiers_detail = TiersMinimalSerializer(source='tiers', read_only=True)

    # Champs calculés
    sens = serializers.SerializerMethodField()
    montant = serializers.SerializerMethodField()
    lettrage_complet = serializers.SerializerMethodField()

    class Meta:
        model = LigneEcriture
        fields = [
            'id',
            'numero_ligne',
            'compte',
            'compte_detail',
            'tiers',
            'tiers_detail',
            'libelle',
            'montant_debit',
            'montant_credit',
            'sens',
            'montant',
            'piece',
            'date_echeance',
            'code_lettrage',
            'is_lettree',
            'lettrage_complet',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['numero_ligne', 'is_lettree', 'created_at', 'updated_at']

    def get_sens(self, obj):
        """Retourne 'D' pour débit, 'C' pour crédit"""
        if obj.montant_debit > 0:
            return 'D'
        elif obj.montant_credit > 0:
            return 'C'
        return None

    def get_montant(self, obj):
        """Retourne le montant non nul"""
        return obj.montant_debit if obj.montant_debit > 0 else obj.montant_credit

    def get_lettrage_complet(self, obj):
        """Retourne le code de lettrage complet si lettré"""
        if obj.is_lettree and obj.code_lettrage:
            return f"{obj.compte.code}-{obj.code_lettrage}"
        return None

    def validate_compte(self, value):
        """Validation du compte"""
        if not value.is_active:
            raise serializers.ValidationError("Le compte doit être actif")
        return value

    def validate_tiers(self, value):
        """Validation du tiers"""
        if value and not value.is_active:
            raise serializers.ValidationError("Le tiers doit être actif")
        return value

    def validate(self, attrs):
        """Validations croisées"""
        montant_debit = attrs.get('montant_debit', Decimal('0'))
        montant_credit = attrs.get('montant_credit', Decimal('0'))
        compte = attrs.get('compte')
        tiers = attrs.get('tiers')

        # Validation : un seul montant non nul
        if montant_debit > 0 and montant_credit > 0:
            raise serializers.ValidationError({
                'montant_credit': "Une ligne ne peut avoir à la fois un débit et un crédit"
            })

        if montant_debit == 0 and montant_credit == 0:
            raise serializers.ValidationError({
                'montant_debit': "Au moins un montant doit être spécifié"
            })

        # Validation des montants négatifs
        if montant_debit < 0 or montant_credit < 0:
            raise serializers.ValidationError("Les montants doivent être positifs")

        # Validation tiers pour comptes de tiers (classes 4)
        if compte and compte.classe == '4':
            # Pour certains comptes de classe 4, le tiers est recommandé
            comptes_tiers = ['401', '411', '421']  # Fournisseurs, Clients, Personnel
            if any(compte.code.startswith(prefix) for prefix in comptes_tiers):
                if not tiers:
                    # Warning plutôt qu'erreur pour plus de flexibilité
                    pass  # On pourrait logger un warning ici

        return attrs


class LigneEcritureCreateSerializer(serializers.ModelSerializer):
    """
    Serializer simplifié pour la création de lignes
    Utilisé dans la création d'écritures complètes
    """

    class Meta:
        model = LigneEcriture
        fields = [
            'compte',
            'tiers',
            'libelle',
            'montant_debit',
            'montant_credit',
            'piece',
            'date_echeance'
        ]

    def validate(self, attrs):
        # Mêmes validations que le serializer principal
        return LigneEcritureSerializer.validate(self, attrs)


class EcritureComptableSerializer(serializers.ModelSerializer):
    """
    Serializer pour l'en-tête d'écriture comptable

    Fonctionnalités :
    - Numérotation automatique
    - Validation de l'équilibre
    - Vérification période ouverte
    - Gestion des lignes d'écriture
    """

    # Relations
    journal_detail = JournalMinimalSerializer(source='journal', read_only=True)
    exercice_detail = ExerciceComptableMinimalSerializer(source='exercice', read_only=True)
    periode_detail = PeriodeComptableMinimalSerializer(source='periode', read_only=True)
    lignes = LigneEcritureSerializer(many=True, read_only=True)

    # Champs pour création avec lignes
    lignes_data = LigneEcritureCreateSerializer(many=True, write_only=True, required=False)

    # Champs calculés
    total_debit = serializers.SerializerMethodField()
    total_credit = serializers.SerializerMethodField()
    is_equilibree = serializers.SerializerMethodField()
    ecart = serializers.SerializerMethodField()
    nb_lignes = serializers.SerializerMethodField()
    statut_display = serializers.SerializerMethodField()

    class Meta:
        model = EcritureComptable
        fields = [
            'id',
            'numero',
            'journal',
            'journal_detail',
            'exercice',
            'exercice_detail',
            'periode',
            'periode_detail',
            'date_ecriture',
            'date_piece',
            'libelle',
            'reference',
            'statut',
            'statut_display',
            'lignes',
            'lignes_data',
            'total_debit',
            'total_credit',
            'is_equilibree',
            'ecart',
            'nb_lignes',
            'created_at',
            'updated_at',
            'created_by',
            'date_validation',
            'validee_par'
        ]
        read_only_fields = [
            'numero',
            'statut',
            'date_validation',
            'validee_par',
            'created_at',
            'updated_at'
        ]

    def get_total_debit(self, obj):
        """Somme des débits"""
        if hasattr(obj, 'lignes'):
            total = obj.lignes.aggregate(total=Sum('montant_debit'))['total']
            return float(total or 0)
        return 0

    def get_total_credit(self, obj):
        """Somme des crédits"""
        if hasattr(obj, 'lignes'):
            total = obj.lignes.aggregate(total=Sum('montant_credit'))['total']
            return float(total or 0)
        return 0

    def get_is_equilibree(self, obj):
        """Vérifie si l'écriture est équilibrée"""
        return abs(self.get_total_debit(obj) - self.get_total_credit(obj)) < 0.01

    def get_ecart(self, obj):
        """Écart débit/crédit"""
        return self.get_total_debit(obj) - self.get_total_credit(obj)

    def get_nb_lignes(self, obj):
        """Nombre de lignes"""
        return obj.lignes.count() if hasattr(obj, 'lignes') else 0

    def get_statut_display(self, obj):
        """Statut avec icône"""
        statuts = {
            'BROUILLON': '📝 Brouillon',
            'VALIDEE': '✅ Validée',
            'CLOTUREE': '🔒 Clôturée'
        }
        return statuts.get(obj.statut, obj.statut)

    def validate_journal(self, value):
        """Validation du journal"""
        if not value.is_active:
            raise serializers.ValidationError("Le journal doit être actif")
        return value

    def validate_exercice(self, value):
        """Validation de l'exercice"""
        if value.statut != 'OUVERT':
            raise serializers.ValidationError("L'exercice doit être ouvert")
        return value

    def validate_periode(self, value):
        """Validation de la période"""
        if value.statut != 'OUVERTE':
            raise serializers.ValidationError("La période doit être ouverte")
        return value

    def validate_date_ecriture(self, value):
        """Validation de la date d'écriture"""
        if value > timezone.now().date():
            raise serializers.ValidationError("La date ne peut pas être dans le futur")
        return value

    def validate_lignes_data(self, value):
        """Validation des lignes à la création"""
        if not value:
            raise serializers.ValidationError("Au moins 2 lignes sont requises")

        if len(value) < 2:
            raise serializers.ValidationError("Une écriture doit avoir au moins 2 lignes")

        # Calculer l'équilibre
        total_debit = sum(ligne.get('montant_debit', 0) for ligne in value)
        total_credit = sum(ligne.get('montant_credit', 0) for ligne in value)

        if abs(total_debit - total_credit) >= 0.01:
            raise serializers.ValidationError(
                f"L'écriture n'est pas équilibrée. "
                f"Débit: {total_debit:,.2f}, Crédit: {total_credit:,.2f}, "
                f"Écart: {abs(total_debit - total_credit):,.2f}"
            )

        return value

    def validate(self, attrs):
        """Validations croisées"""
        exercice = attrs.get('exercice')
        periode = attrs.get('periode')
        date_ecriture = attrs.get('date_ecriture')

        # Vérifier la cohérence exercice/période
        if exercice and periode:
            if periode.exercice_id != exercice.id:
                raise serializers.ValidationError({
                    'periode': "La période doit appartenir à l'exercice sélectionné"
                })

        # Vérifier la cohérence date/période
        if periode and date_ecriture:
            if not (periode.date_debut <= date_ecriture <= periode.date_fin):
                raise serializers.ValidationError({
                    'date_ecriture': f"La date doit être comprise entre "
                                     f"{periode.date_debut} et {periode.date_fin}"
                })

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        """Création avec lignes en transaction"""
        lignes_data = validated_data.pop('lignes_data', [])

        # Créer l'écriture
        ecriture = super().create(validated_data)

        # Créer les lignes
        for index, ligne_data in enumerate(lignes_data, 1):
            LigneEcriture.objects.create(
                ecriture=ecriture,
                numero_ligne=index,
                **ligne_data
            )

        return ecriture

    @transaction.atomic
    def update(self, instance, validated_data):
        """Mise à jour (sans toucher aux lignes pour l'instant)"""
        # Empêcher la modification d'une écriture validée
        if instance.statut != 'BROUILLON':
            raise serializers.ValidationError(
                "Seules les écritures en brouillon peuvent être modifiées"
            )

        # Les lignes ne sont pas modifiables via ce serializer
        validated_data.pop('lignes_data', None)

        return super().update(instance, validated_data)


class EcritureComptableMinimalSerializer(serializers.ModelSerializer):
    """Serializer minimal pour les listes"""

    journal_code = serializers.CharField(source='journal.code', read_only=True)
    is_equilibree = serializers.SerializerMethodField()

    class Meta:
        model = EcritureComptable
        fields = [
            'id',
            'numero',
            'date_ecriture',
            'libelle',
            'journal_code',
            'statut',
            'is_equilibree'
        ]

    def get_is_equilibree(self, obj):
        """Vérifie l'équilibre rapidement"""
        if hasattr(obj, '_is_equilibree'):
            return obj._is_equilibree
        return True  # Par défaut on suppose équilibré


class EcritureComptableStatsSerializer(serializers.ModelSerializer):
    """Serializer avec statistiques détaillées"""

    journal_detail = JournalMinimalSerializer(source='journal', read_only=True)
    total_debit = serializers.SerializerMethodField()
    total_credit = serializers.SerializerMethodField()
    ecart = serializers.SerializerMethodField()
    nb_lignes = serializers.SerializerMethodField()
    comptes_utilises = serializers.SerializerMethodField()
    tiers_impliques = serializers.SerializerMethodField()

    class Meta:
        model = EcritureComptable
        fields = [
            'id',
            'numero',
            'date_ecriture',
            'libelle',
            'journal_detail',
            'statut',
            'total_debit',
            'total_credit',
            'ecart',
            'nb_lignes',
            'comptes_utilises',
            'tiers_impliques'
        ]

    def get_total_debit(self, obj):
        return obj.lignes.aggregate(total=Sum('montant_debit'))['total'] or 0

    def get_total_credit(self, obj):
        return obj.lignes.aggregate(total=Sum('montant_credit'))['total'] or 0

    def get_ecart(self, obj):
        return abs(self.get_total_debit(obj) - self.get_total_credit(obj))

    def get_nb_lignes(self, obj):
        return obj.lignes.count()

    def get_comptes_utilises(self, obj):
        """Liste des comptes utilisés"""
        comptes = obj.lignes.values_list('compte__code', 'compte__libelle').distinct()
        return [{'code': code, 'libelle': libelle} for code, libelle in comptes]

    def get_tiers_impliques(self, obj):
        """Liste des tiers impliqués"""
        tiers = obj.lignes.exclude(tiers__isnull=True).values_list(
            'tiers__code', 'tiers__raison_sociale'
        ).distinct()
        return [{'code': code, 'raison_sociale': rs} for code, rs in tiers]


class ValidationEcritureSerializer(serializers.Serializer):
    """
    Serializer pour valider une écriture
    Change le statut de BROUILLON à VALIDEE
    """

    ecriture_id = serializers.IntegerField()

    def validate_ecriture_id(self, value):
        """Vérifier que l'écriture peut être validée"""
        try:
            ecriture = EcritureComptable.objects.get(id=value)
        except EcritureComptable.DoesNotExist:
            raise serializers.ValidationError("Écriture introuvable")

        if ecriture.statut != 'BROUILLON':
            raise serializers.ValidationError(
                f"L'écriture est déjà {ecriture.get_statut_display()}"
            )

        # Vérifier l'équilibre
        total_debit = ecriture.lignes.aggregate(total=Sum('montant_debit'))['total'] or 0
        total_credit = ecriture.lignes.aggregate(total=Sum('montant_credit'))['total'] or 0

        if abs(total_debit - total_credit) >= 0.01:
            raise serializers.ValidationError(
                f"L'écriture n'est pas équilibrée. Écart: {abs(total_debit - total_credit):,.2f}"
            )

        # Vérifier qu'il y a au moins 2 lignes
        if ecriture.lignes.count() < 2:
            raise serializers.ValidationError(
                "Une écriture doit avoir au moins 2 lignes"
            )

        return value


class SaisieRapideSerializer(serializers.Serializer):
    """
    Serializer pour la saisie rapide d'écritures simples
    Ex: Facture fournisseur, encaissement client, etc.
    """

    TYPE_OPERATIONS = [
        ('ACHAT', 'Achat/Facture fournisseur'),
        ('VENTE', 'Vente/Facture client'),
        ('ENCAISSEMENT', 'Encaissement client'),
        ('DECAISSEMENT', 'Paiement fournisseur'),
        ('SALAIRE', 'Paiement salaire'),
        ('CHARGE', 'Charge diverse'),
        ('PRODUIT', 'Produit divers'),
    ]

    type_operation = serializers.ChoiceField(choices=TYPE_OPERATIONS)
    date_operation = serializers.DateField()
    montant_ttc = serializers.DecimalField(max_digits=15, decimal_places=2)
    taux_tva = serializers.DecimalField(
        max_digits=5, decimal_places=2,
        default=Decimal('18.00')
    )
    tiers = serializers.PrimaryKeyRelatedField(
        queryset=Tiers.objects.filter(is_active=True),
        required=False
    )
    libelle = serializers.CharField(max_length=255)
    reference = serializers.CharField(max_length=100, required=False)
    compte_charge_produit = serializers.PrimaryKeyRelatedField(
        queryset=CompteOHADA.objects.filter(is_active=True),
        required=False
    )

    def validate(self, attrs):
        """Générer les lignes d'écriture selon le type"""
        type_op = attrs['type_operation']

        # Vérifications spécifiques par type
        if type_op in ['ACHAT', 'VENTE', 'ENCAISSEMENT', 'DECAISSEMENT'] and not attrs.get('tiers'):
            raise serializers.ValidationError({
                'tiers': f"Le tiers est obligatoire pour une opération de type {type_op}"
            })

        return attrs