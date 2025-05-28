# apps/accounting/serializers/tiers.py
"""
Serializers pour les tiers (auxiliaires) OHADA
- Tiers : Fournisseurs, Clients, Employés
- Gestion de la codification automatique
- Validation des comptes collectifs
"""

from rest_framework import serializers
from apps.accounting.models import Tiers, CompteOHADA
from .base import CompteOHADAMinimalSerializer


class TiersSerializer(serializers.ModelSerializer):
    """
    Serializer complet pour les tiers OHADA

    Fonctionnalités :
    - Génération automatique du code (FLOC00001, CGRP00002, etc.)
    - Validation du type et compte collectif
    - Gestion des informations légales et commerciales
    - Calcul du solde comptable
    """

    # Relations
    compte_collectif_detail = CompteOHADAMinimalSerializer(
        source='compte_collectif',
        read_only=True
    )

    # Champs calculés
    type_display = serializers.CharField(source='get_type_tiers_display', read_only=True)
    solde_comptable_formate = serializers.SerializerMethodField()
    age_creation = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()

    # Champs de commodité pour l'affichage
    tiers_complet = serializers.SerializerMethodField()
    identite_complete = serializers.SerializerMethodField()

    class Meta:
        model = Tiers
        fields = [
            'id',
            'code',
            'type_tiers',
            'type_display',
            'compte_collectif',
            'compte_collectif_detail',

            # Identification
            'raison_sociale',
            'sigle',
            'matricule',
            'numero_contribuable',
            'rccm',

            # Contact
            'adresse',
            'ville',
            'pays',
            'telephone',
            'email',

            # Informations bancaires
            'banque',
            'numero_compte_bancaire',

            # Conditions commerciales
            'delai_paiement',
            'plafond_credit',
            'exonere_tva',

            # Contact principal
            'contact_principal',
            'fonction_contact',

            # Notes et statut
            'notes',
            'is_active',
            'is_bloque',
            'motif_blocage',

            # Champs calculés
            'solde_comptable',
            'solde_comptable_formate',
            'age_creation',
            'status_display',
            'tiers_complet',
            'identite_complete',

            # Métadonnées
            'created_at',
            'updated_at',
            'created_by'
        ]
        read_only_fields = [
            'code',  # Généré automatiquement
            'compte_collectif',  # Déterminé par le type
            'solde_comptable',
            'created_at',
            'updated_at'
        ]

    def get_solde_comptable_formate(self, obj):
        """Retourne le solde formaté avec devise"""
        solde = obj.solde_comptable
        if solde == 0:
            return "0,00 XAF"

        # Formater avec séparateurs de milliers
        solde_formate = "{:,.2f}".format(abs(solde)).replace(',', ' ')
        signe = "+" if solde > 0 else "-"

        return f"{signe}{solde_formate} XAF"

    def get_age_creation(self, obj):
        """Nombre de jours depuis la création"""
        from django.utils import timezone
        delta = timezone.now().date() - obj.created_at.date()
        return delta.days

    def get_status_display(self, obj):
        """Statut formaté avec icônes"""
        statuts = []

        if obj.is_active:
            statuts.append("✓ Actif")
        else:
            statuts.append("✗ Inactif")

        if obj.is_bloque:
            statuts.append("🔒 Bloqué")

        if obj.exonere_tva:
            statuts.append("📋 Exonéré TVA")

        return " | ".join(statuts)

    def get_tiers_complet(self, obj):
        """Code + raison sociale pour affichage"""
        return f"{obj.code} - {obj.raison_sociale}"

    def get_identite_complete(self, obj):
        """Identité complète avec sigle et matricule"""
        identite = obj.raison_sociale

        if obj.sigle:
            identite += f" ({obj.sigle})"

        if obj.type_tiers == 'EMPL' and obj.matricule:
            identite += f" - Mat: {obj.matricule}"

        if obj.numero_contribuable:
            identite += f" - N° Contrib: {obj.numero_contribuable}"

        return identite

    def validate_type_tiers(self, value):
        """Validation du type de tiers"""
        types_autorises = [choice[0] for choice in Tiers.TYPES_TIERS]

        if value not in types_autorises:
            raise serializers.ValidationError(
                f"Type non autorisé. Types valides : {', '.join(types_autorises)}"
            )

        return value

    def validate_numero_contribuable(self, value):
        """Validation du numéro de contribuable (unique)"""
        if value:
            # Vérifier l'unicité si c'est une création ou modification
            queryset = Tiers.objects.filter(numero_contribuable=value)
            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)

            if queryset.exists():
                raise serializers.ValidationError(
                    "Ce numéro de contribuable est déjà utilisé"
                )

        return value

    def validate_matricule(self, value):
        """Validation du matricule employé"""
        type_tiers = self.initial_data.get('type_tiers')

        # Matricule obligatoire pour les employés
        if type_tiers == 'EMPL' and not value:
            raise serializers.ValidationError(
                "Le matricule est obligatoire pour un employé"
            )

        # Matricule uniquement pour les employés
        if value and type_tiers != 'EMPL':
            raise serializers.ValidationError(
                "Le matricule est réservé aux employés"
            )

        # Vérifier l'unicité
        if value:
            queryset = Tiers.objects.filter(matricule=value)
            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)

            if queryset.exists():
                raise serializers.ValidationError("Ce matricule est déjà utilisé")

        return value

    def validate_plafond_credit(self, value):
        """Validation du plafond de crédit"""
        type_tiers = self.initial_data.get('type_tiers')

        # Plafond seulement pour les clients
        if value and type_tiers not in ['CLOC', 'CGRP']:
            raise serializers.ValidationError(
                "Le plafond de crédit est réservé aux clients"
            )

        if value and value <= 0:
            raise serializers.ValidationError(
                "Le plafond de crédit doit être positif"
            )

        return value

    def validate_delai_paiement(self, value):
        """Validation du délai de paiement"""
        if value is not None and (value < 0 or value > 365):
            raise serializers.ValidationError(
                "Le délai de paiement doit être entre 0 et 365 jours"
            )

        return value

    def validate(self, attrs):
        """Validations croisées"""
        type_tiers = attrs.get('type_tiers')

        # Validations spécifiques par type
        if type_tiers in ['CLOC', 'CGRP']:  # Clients
            # Les clients peuvent avoir un plafond de crédit
            pass
        elif type_tiers in ['FLOC', 'FGRP']:  # Fournisseurs
            # Pas de plafond pour les fournisseurs
            if attrs.get('plafond_credit'):
                attrs['plafond_credit'] = None
        elif type_tiers == 'EMPL':  # Employés
            # Employés : pas de conditions commerciales
            attrs['plafond_credit'] = None
            attrs['delai_paiement'] = 0
            attrs['exonere_tva'] = False

        return attrs


class TiersMinimalSerializer(serializers.ModelSerializer):
    """
    Serializer minimal pour les listes déroulantes et références
    Utilisé dans les relations avec les écritures
    """

    type_display = serializers.CharField(source='get_type_tiers_display', read_only=True)
    tiers_complet = serializers.SerializerMethodField()

    class Meta:
        model = Tiers
        fields = [
            'id',
            'code',
            'type_tiers',
            'type_display',
            'raison_sociale',
            'sigle',
            'tiers_complet',
            'is_active',
            'is_bloque'
        ]

    def get_tiers_complet(self, obj):
        return f"{obj.code} - {obj.raison_sociale}"


class TiersCreationSerializer(serializers.ModelSerializer):
    """Serializer pour la création de tiers"""

    # Le code est généré automatiquement
    code = serializers.CharField(read_only=True)

    # Le compte collectif est assigné automatiquement
    compte_collectif_detail = CompteOHADAMinimalSerializer(
        source='compte_collectif',
        read_only=True
    )

    # created_by est assigné automatiquement dans le ViewSet
    created_by = serializers.HiddenField(
        default=serializers.CurrentUserDefault()
    )

    class Meta:
        model = Tiers
        fields = [
            'id', 'code', 'type_tiers', 'compte_collectif', 'compte_collectif_detail',
            'raison_sociale', 'sigle', 'matricule',
            'numero_contribuable', 'rccm', 'adresse', 'ville', 'pays',
            'telephone', 'email', 'banque', 'numero_compte_bancaire',
            'delai_paiement', 'plafond_credit', 'exonere_tva',
            'contact_principal', 'fonction_contact', 'notes',
            'is_active', 'is_bloque', 'created_by', 'created_at'
        ]
        read_only_fields = ['code', 'compte_collectif', 'compte_collectif_detail', 'created_at', 'created_by']

    def validate(self, attrs):
        """Validation des données"""
        type_tiers = attrs.get('type_tiers')

        # Validation du matricule pour les employés
        if type_tiers == 'EMPL' and not attrs.get('matricule'):
            raise serializers.ValidationError({
                'matricule': 'Le matricule est obligatoire pour un employé'
            })

        return attrs

    def to_representation(self, instance):
        """Personnaliser la représentation pour inclure les détails du compte"""
        data = super().to_representation(instance)
        # S'assurer que compte_collectif_detail est bien inclus
        if 'compte_collectif_detail' in data and data['compte_collectif_detail']:
            # Utiliser compte_collectif_detail au lieu de compte_collectif simple
            data['compte_collectif'] = data['compte_collectif_detail']
        return data


class TiersStatsSerializer(serializers.ModelSerializer):
    """
    Serializer avec statistiques d'utilisation des tiers
    Pour les tableaux de bord et analyses
    """

    nb_ecritures = serializers.SerializerMethodField()
    total_debit = serializers.SerializerMethodField()
    total_credit = serializers.SerializerMethodField()
    solde_net = serializers.SerializerMethodField()
    derniere_ecriture = serializers.SerializerMethodField()
    premiere_ecriture = serializers.SerializerMethodField()
    nb_factures_impayees = serializers.SerializerMethodField()

    class Meta:
        model = Tiers
        fields = [
            'id',
            'code',
            'raison_sociale',
            'type_tiers',
            'nb_ecritures',
            'total_debit',
            'total_credit',
            'solde_net',
            'derniere_ecriture',
            'premiere_ecriture',
            'nb_factures_impayees',
            'delai_paiement',
            'plafond_credit',
            'is_active',
            'is_bloque'
        ]

    def get_nb_ecritures(self, obj):
        """Nombre de lignes d'écriture pour ce tiers"""
        if hasattr(obj, 'lignes_ecritures'):
            return obj.lignes_ecritures.count()
        return 0

    def get_total_debit(self, obj):
        """Total des débits"""
        if hasattr(obj, 'lignes_ecritures'):
            from django.db.models import Sum
            total = obj.lignes_ecritures.aggregate(
                total=Sum('montant_debit')
            )['total']
            return float(total or 0)
        return 0

    def get_total_credit(self, obj):
        """Total des crédits"""
        if hasattr(obj, 'lignes_ecritures'):
            from django.db.models import Sum
            total = obj.lignes_ecritures.aggregate(
                total=Sum('montant_credit')
            )['total']
            return float(total or 0)
        return 0

    def get_solde_net(self, obj):
        """Solde net (débit - crédit)"""
        return self.get_total_debit(obj) - self.get_total_credit(obj)

    def get_derniere_ecriture(self, obj):
        """Informations sur la dernière écriture"""
        if hasattr(obj, 'lignes_ecritures'):
            derniere_ligne = obj.lignes_ecritures.order_by('-created_at').first()
            if derniere_ligne:
                return {
                    'date': derniere_ligne.ecriture.date_ecriture,
                    'numero': derniere_ligne.ecriture.numero,
                    'libelle': derniere_ligne.libelle,
                    'montant': float(derniere_ligne.montant)
                }
        return None

    def get_premiere_ecriture(self, obj):
        """Informations sur la première écriture"""
        if hasattr(obj, 'lignes_ecritures'):
            premiere_ligne = obj.lignes_ecritures.order_by('created_at').first()
            if premiere_ligne:
                return {
                    'date': premiere_ligne.ecriture.date_ecriture,
                    'numero': premiere_ligne.ecriture.numero,
                    'libelle': premiere_ligne.libelle
                }
        return None

    def get_nb_factures_impayees(self, obj):
        """Nombre de factures impayées (échéance dépassée)"""
        if hasattr(obj, 'lignes_ecritures'):
            from django.utils import timezone
            return obj.lignes_ecritures.filter(
                date_echeance__lt=timezone.now().date(),
                is_lettree=False
            ).count()
        return 0


class TiersByTypeSerializer(serializers.Serializer):
    """
    Serializer pour regrouper les tiers par type
    Utile pour les statistiques et rapports
    """

    type_tiers = serializers.CharField()
    type_display = serializers.CharField()
    count = serializers.IntegerField()
    tiers_actifs = serializers.IntegerField()
    tiers_bloques = serializers.IntegerField()
    total_solde = serializers.DecimalField(max_digits=15, decimal_places=2)

    def to_representation(self, instance):
        """Formatage personnalisé"""
        data = super().to_representation(instance)

        # Ajouter des métadonnées
        data['pourcentage'] = round(
            (data['count'] / instance.get('total_general', 1)) * 100, 2
        ) if instance.get('total_general') else 0

        return data

class BlocageDeblocageSerializer(serializers.Serializer):
    """Serializer pour bloquer/débloquer un tiers"""

    motif = serializers.CharField(
        max_length=500,
        required=True,
        help_text="Motif du blocage"
    )

    def validate_motif(self, value):
        """Valide le motif de blocage"""
        if len(value.strip()) < 10:
            raise serializers.ValidationError(
                "Le motif doit contenir au moins 10 caractères"
            )
        return value.strip()