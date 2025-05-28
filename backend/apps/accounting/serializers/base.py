# apps/accounting/serializers/base.py
"""
Serializers de base pour les entités fondamentales OHADA
- CompteOHADA : Plan comptable
- Journal : Journaux comptables
"""

from rest_framework import serializers
from apps.accounting.models import CompteOHADA, Journal


class CompteOHADASerializer(serializers.ModelSerializer):
    """
    Serializer pour le plan comptable OHADA

    Fonctionnalités :
    - Validation du code 8 chiffres
    - Filtrage par classe et type
    - Recherche par code et libellé
    - Comptes actifs uniquement par défaut
    """

    # Champs calculés
    code_formate = serializers.SerializerMethodField()
    compte_complet = serializers.SerializerMethodField()

    class Meta:
        model = CompteOHADA
        fields = [
            'id',
            'code',
            'libelle',
            'classe',
            'type',
            'ref',
            'solde_normal',  # AJOUTER CETTE LIGNE
            'is_active',
            'code_formate',
            'compte_complet',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_code_formate(self, obj):
        """Retourne le code formaté pour l'affichage"""
        return f"{obj.code[:2]} {obj.code[2:4]} {obj.code[4:6]} {obj.code[6:8]}"

    def get_compte_complet(self, obj):
        """Retourne code + libellé pour affichage dans les listes"""
        return f"{obj.code} - {obj.libelle}"

    def validate_code(self, value):
        """Validation du code OHADA 8 chiffres"""
        if not value.isdigit():
            raise serializers.ValidationError("Le code doit contenir uniquement des chiffres")

        if len(value) != 8:
            raise serializers.ValidationError("Le code doit contenir exactement 8 chiffres")

        # Validation des classes OHADA (1-9)
        classe = value[0]
        if classe not in '123456789':
            raise serializers.ValidationError("La classe doit être comprise entre 1 et 9")

        return value

    def validate(self, attrs):
        """Validations croisées"""
        code = attrs.get('code', '')
        classe = attrs.get('classe', '')
        type_compte = attrs.get('type', '')

        # Vérifier la cohérence classe/code
        if code and classe:
            if code[0] != classe:
                raise serializers.ValidationError({
                    'classe': "La classe doit correspondre au premier chiffre du code"
                })

        # Validation type selon la classe OHADA
        validations_type = {
            '1': ['passif'],  # Capitaux propres et passifs
            '2': ['actif'],  # Immobilisations
            '3': ['actif'],  # Stocks
            '4': ['actif', 'passif'],  # Tiers (peut être débiteur ou créditeur)
            '5': ['actif'],  # Trésorerie
            '6': ['charge'],  # Charges
            '7': ['produit'],  # Produits
            '8': ['charge', 'produit'],  # Résultats
            '9': ['actif', 'passif'],  # Comptes analytiques
        }

        if classe and type_compte:
            types_autorises = validations_type.get(classe, [])
            if type_compte not in types_autorises:
                raise serializers.ValidationError({
                    'type': f"Type '{type_compte}' non autorisé pour la classe {classe}. "
                            f"Types autorisés : {', '.join(types_autorises)}"
                })

        return attrs


class CompteOHADAMinimalSerializer(serializers.ModelSerializer):
    """
    Serializer minimal pour les listes déroulantes et références
    Utilisé dans les relations avec d'autres modèles
    """

    compte_complet = serializers.SerializerMethodField()

    class Meta:
        model = CompteOHADA
        fields = ['id', 'code', 'libelle', 'compte_complet', 'type', 'classe']

    def get_compte_complet(self, obj):
        return f"{obj.code} - {obj.libelle}"


class JournalSerializer(serializers.ModelSerializer):
    """
    Serializer pour les journaux comptables OHADA

    Fonctionnalités :
    - Validation du code journal
    - Affichage du type avec libellé
    - Compte de contrepartie optionnel
    - Statistiques d'utilisation
    """

    # Relations
    compte_contrepartie_detail = CompteOHADAMinimalSerializer(
        source='compte_contrepartie',
        read_only=True
    )

    # Champs calculés
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    nb_ecritures = serializers.SerializerMethodField()
    derniere_utilisation = serializers.SerializerMethodField()

    class Meta:
        model = Journal
        fields = [
            'id',
            'code',
            'libelle',
            'type',
            'type_display',
            'compte_contrepartie',
            'compte_contrepartie_detail',
            'is_active',
            'nb_ecritures',
            'derniere_utilisation',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_nb_ecritures(self, obj):
        """Nombre d'écritures dans ce journal"""
        if hasattr(obj, 'ecritures'):
            return obj.ecritures.count()
        return 0

    def get_derniere_utilisation(self, obj):
        """Date de la dernière écriture dans ce journal"""
        if hasattr(obj, 'ecritures'):
            derniere_ecriture = obj.ecritures.order_by('-date_ecriture').first()
            if derniere_ecriture:
                return derniere_ecriture.date_ecriture
        return None

    def validate_code(self, value):
        """Validation du code journal"""
        if not value:
            raise serializers.ValidationError("Le code est obligatoire")

        # Convertir en majuscules
        value = value.upper()

        # Vérifier format alphanumérique
        if not value.replace('_', '').replace('-', '').isalnum():
            raise serializers.ValidationError(
                "Le code ne peut contenir que des lettres, chiffres, tirets et underscores"
            )

        # Longueur maximale
        if len(value) > 10:
            raise serializers.ValidationError("Le code ne peut pas dépasser 10 caractères")

        return value

    def validate_type(self, value):
        """Validation du type de journal"""
        types_autorises = [choice[0] for choice in Journal.TYPES_JOURNAL]

        if value not in types_autorises:
            raise serializers.ValidationError(
                f"Type non autorisé. Types valides : {', '.join(types_autorises)}"
            )

        return value

    def validate_compte_contrepartie(self, value):
        """Validation du compte de contrepartie"""
        if value and not value.is_active:
            raise serializers.ValidationError(
                "Le compte de contrepartie doit être actif"
            )
        return value

    def validate(self, attrs):
        """Validations métier"""
        type_journal = attrs.get('type', '')
        compte_contrepartie = attrs.get('compte_contrepartie')

        # Recommandations de comptes selon le type
        recommandations_comptes = {
            'BQ': ['5'],  # Classe 5 - Trésorerie
            'CA': ['5'],  # Classe 5 - Trésorerie
            'VT': ['7'],  # Classe 7 - Produits
            'AC': ['6'],  # Classe 6 - Charges
            'PA': ['6'],  # Classe 6 - Charges (salaires)
            'FI': ['4'],  # Classe 4 - État et fiscalité
            'SO': ['4'],  # Classe 4 - Organismes sociaux
        }

        if type_journal in recommandations_comptes and compte_contrepartie:
            classes_recommandees = recommandations_comptes[type_journal]
            if compte_contrepartie.classe not in classes_recommandees:
                # Warning plutôt qu'erreur pour plus de flexibilité
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(
                    f"Journal {type_journal}: compte contrepartie classe {compte_contrepartie.classe} "
                    f"non standard. Classes recommandées: {classes_recommandees}"
                )

        return attrs


class JournalMinimalSerializer(serializers.ModelSerializer):
    """
    Serializer minimal pour les listes déroulantes
    Utilisé dans les relations avec les écritures
    """

    type_display = serializers.CharField(source='get_type_display', read_only=True)
    journal_complet = serializers.SerializerMethodField()

    class Meta:
        model = Journal
        fields = ['id', 'code', 'libelle', 'type', 'type_display', 'journal_complet']

    def get_journal_complet(self, obj):
        return f"{obj.code} - {obj.libelle}"


# Serializers pour statistiques et rapports
class CompteOHADAStatsSerializer(serializers.ModelSerializer):
    """
    Serializer avec statistiques d'utilisation des comptes
    Pour les tableaux de bord et analyses
    """

    nb_lignes_ecritures = serializers.SerializerMethodField()
    solde_debiteur = serializers.SerializerMethodField()
    solde_crediteur = serializers.SerializerMethodField()
    solde_net = serializers.SerializerMethodField()
    derniere_utilisation = serializers.SerializerMethodField()

    class Meta:
        model = CompteOHADA
        fields = [
            'id', 'code', 'libelle', 'classe', 'type',
            'nb_lignes_ecritures', 'solde_debiteur', 'solde_crediteur',
            'solde_net', 'derniere_utilisation'
        ]

    def get_nb_lignes_ecritures(self, obj):
        """Nombre de lignes d'écriture utilisant ce compte"""
        if hasattr(obj, 'lignes_ecritures'):
            return obj.lignes_ecritures.count()
        return 0

    def get_solde_debiteur(self, obj):
        """Total des débits sur ce compte"""
        if hasattr(obj, 'lignes_ecritures'):
            from django.db.models import Sum
            total = obj.lignes_ecritures.aggregate(
                total=Sum('montant_debit')
            )['total']
            return float(total or 0)
        return 0

    def get_solde_crediteur(self, obj):
        """Total des crédits sur ce compte"""
        if hasattr(obj, 'lignes_ecritures'):
            from django.db.models import Sum
            total = obj.lignes_ecritures.aggregate(
                total=Sum('montant_credit')
            )['total']
            return float(total or 0)
        return 0

    def get_solde_net(self, obj):
        """Solde net du compte (débit - crédit)"""
        return self.get_solde_debiteur(obj) - self.get_solde_crediteur(obj)

    def get_derniere_utilisation(self, obj):
        """Date de dernière utilisation du compte"""
        if hasattr(obj, 'lignes_ecritures'):
            derniere_ligne = obj.lignes_ecritures.order_by('-created_at').first()
            if derniere_ligne:
                return derniere_ligne.ecriture.date_ecriture
        return None


class JournalStatsSerializer(serializers.ModelSerializer):
    """
    Serializer avec statistiques d'utilisation des journaux
    """

    nb_ecritures_total = serializers.SerializerMethodField()
    nb_ecritures_brouillon = serializers.SerializerMethodField()
    nb_ecritures_validees = serializers.SerializerMethodField()
    montant_total_debits = serializers.SerializerMethodField()
    montant_total_credits = serializers.SerializerMethodField()
    derniere_ecriture = serializers.SerializerMethodField()
    premiere_ecriture = serializers.SerializerMethodField()

    class Meta:
        model = Journal
        fields = [
            'id', 'code', 'libelle', 'type',
            'nb_ecritures_total', 'nb_ecritures_brouillon', 'nb_ecritures_validees',
            'montant_total_debits', 'montant_total_credits',
            'derniere_ecriture', 'premiere_ecriture'
        ]

    def get_nb_ecritures_total(self, obj):
        return obj.ecritures.count()

    def get_nb_ecritures_brouillon(self, obj):
        return obj.ecritures.filter(statut='BROUILLON').count()

    def get_nb_ecritures_validees(self, obj):
        return obj.ecritures.filter(statut='VALIDEE').count()

    def get_montant_total_debits(self, obj):
        """Somme de tous les débits du journal"""
        from django.db.models import Sum
        total = obj.ecritures.aggregate(
            total=Sum('lignes__montant_debit')
        )['total']
        return float(total or 0)

    def get_montant_total_credits(self, obj):
        """Somme de tous les crédits du journal"""
        from django.db.models import Sum
        total = obj.ecritures.aggregate(
            total=Sum('lignes__montant_credit')
        )['total']
        return float(total or 0)

    def get_derniere_ecriture(self, obj):
        derniere = obj.ecritures.order_by('-date_ecriture').first()
        if derniere:
            return {
                'numero': derniere.numero,
                'date': derniere.date_ecriture,
                'libelle': derniere.libelle
            }
        return None

    def get_premiere_ecriture(self, obj):
        premiere = obj.ecritures.order_by('date_ecriture').first()
        if premiere:
            return {
                'numero': premiere.numero,
                'date': premiere.date_ecriture,
                'libelle': premiere.libelle
            }
        return None