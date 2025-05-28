# apps/accounting/models/tiers.py
from django.db import models
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from django.db.models import Max
import re
from .compte import CompteOHADA  # Import ajouté


class Tiers(models.Model):
    """
    Tiers (auxiliaires) selon le plan OHADA avec codification structurée
    - FLOC : Fournisseurs locaux (4011)
    - FGRP : Fournisseurs groupe (4012)
    - CLOC : Clients locaux (4111)
    - CGRP : Clients groupe (4112)
    - EMPL : Employés (4211)
    """

    TYPES_TIERS = [
        ('FLOC', 'Fournisseur local'),
        ('FGRP', 'Fournisseur groupe'),
        ('CLOC', 'Client local'),
        ('CGRP', 'Client groupe'),
        ('EMPL', 'Employé'),
    ]

    # Mapping type -> compte collectif
    COMPTES_COLLECTIFS = {
        'FLOC': '40110000',
        'FGRP': '40120000',
        'CLOC': '41110000',
        'CGRP': '41120000',
        'EMPL': '42100000',
    }

    # Code auxiliaire (FLOC00001, CGRP00002, etc.)
    code = models.CharField(
        max_length=9,
        unique=True,
        validators=[
            RegexValidator(
                r'^(FLOC|FGRP|CLOC|CGRP|EMPL)\d{5}$',
                'Le code doit être au format : FLOC00001, CGRP00002, etc.'
            )
        ],
        help_text="Code généré automatiquement selon le type"
    )

    # Type de tiers
    type_tiers = models.CharField(
        max_length=4,
        choices=TYPES_TIERS,
        help_text="Détermine le compte collectif et le préfixe du code"
    )

    # Compte collectif (calculé automatiquement)
    compte_collectif = models.ForeignKey(
        'CompteOHADA',
        on_delete=models.PROTECT,
        related_name='tiers_rattaches',
        editable=False,
        help_text="Compte collectif déterminé par le type"
    )

    # Informations générales
    raison_sociale = models.CharField(
        max_length=200,
        help_text="Dénomination sociale ou nom complet"
    )

    sigle = models.CharField(
        max_length=50,
        blank=True,
        help_text="Sigle ou nom commercial"
    )

    # Pour les employés uniquement
    matricule = models.CharField(
        max_length=20,
        blank=True,
        unique=True,
        null=True,
        help_text="Matricule de l'employé (si type EMPL)"
    )

    # Identification légale
    numero_contribuable = models.CharField(
        max_length=50,
        blank=True,
        unique=True,
        null=True,
        help_text="Numéro d'identification fiscale"
    )

    rccm = models.CharField(
        max_length=50,
        blank=True,
        help_text="Registre du Commerce (si applicable)"
    )

    # Contact
    adresse = models.TextField(
        blank=True
    )

    ville = models.CharField(
        max_length=100,
        blank=True
    )

    pays = models.CharField(
        max_length=100,
        default='Cameroun'
    )

    telephone = models.CharField(
        max_length=20,
        blank=True
    )

    email = models.EmailField(
        blank=True
    )

    # Informations bancaires
    banque = models.CharField(
        max_length=100,
        blank=True
    )

    numero_compte_bancaire = models.CharField(
        max_length=50,
        blank=True
    )

    # Conditions commerciales (pour clients/fournisseurs)
    delai_paiement = models.PositiveIntegerField(
        default=30,
        help_text="Délai de paiement en jours"
    )

    plafond_credit = models.DecimalField(
        max_digits=15,
        decimal_places=0,
        null=True,
        blank=True,
        help_text="Plafond de crédit autorisé (clients uniquement)"
    )

    exonere_tva = models.BooleanField(
        default=False,
        help_text="Exonéré de TVA"
    )

    # Contact principal
    contact_principal = models.CharField(
        max_length=200,
        blank=True,
        help_text="Nom du contact principal"
    )

    fonction_contact = models.CharField(
        max_length=100,
        blank=True,
        help_text="Fonction du contact"
    )

    # Notes
    notes = models.TextField(
        blank=True,
        help_text="Notes internes"
    )

    # Statut
    is_active = models.BooleanField(
        default=True,
        help_text="Décocher pour désactiver"
    )

    is_bloque = models.BooleanField(
        default=False,
        help_text="Bloquer toute transaction"
    )

    motif_blocage = models.TextField(
        blank=True
    )

    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='tiers_crees'
    )

    class Meta:
        verbose_name = "Tiers"
        verbose_name_plural = "Tiers"
        ordering = ['type_tiers', 'code']
        indexes = [
            models.Index(fields=['type_tiers', 'code']),
        ]

    def __str__(self):
        return f"{self.code} - {self.raison_sociale}"

    def clean(self):
        """Validations métier"""
        # Vérifier le matricule pour les employés
        if self.type_tiers == 'EMPL' and not self.matricule:
            raise ValidationError("Le matricule est obligatoire pour un employé")

        # Vérifier que le code correspond au type
        if self.code and self.type_tiers:
            if not self.code.startswith(self.type_tiers):
                raise ValidationError(
                    f"Le code doit commencer par {self.type_tiers} pour ce type de tiers"
                )

    def save(self, *args, **kwargs):
        # Générer le code si nouveau
        if not self.pk and not self.code:
            self.code = self._generer_code()

        # Affecter le compte collectif selon le type
        if self.type_tiers and not self.compte_collectif_id:
            code_collectif = self.COMPTES_COLLECTIFS[self.type_tiers]
            try:
                self.compte_collectif = CompteOHADA.objects.get(code=code_collectif)
            except CompteOHADA.DoesNotExist:
                raise ValidationError(
                    f"Le compte collectif {code_collectif} n'existe pas. "
                    f"Veuillez d'abord créer ce compte dans le plan comptable."
                )

        self.full_clean()
        super().save(*args, **kwargs)

    def _generer_code(self):
        """Génère automatiquement le prochain code selon le type"""
        if not self.type_tiers:
            raise ValidationError("Le type de tiers doit être défini")

        # Trouver le dernier numéro utilisé pour ce type
        derniers_codes = Tiers.objects.filter(
            code__startswith=self.type_tiers
        ).values_list('code', flat=True)

        if derniers_codes:
            # Extraire les numéros et trouver le max
            numeros = []
            for code in derniers_codes:
                match = re.search(r'(\d{5})$', code)
                if match:
                    numeros.append(int(match.group(1)))

            if numeros:
                prochain_numero = max(numeros) + 1
            else:
                prochain_numero = 1
        else:
            prochain_numero = 1

        # Formater avec des zéros
        return f"{self.type_tiers}{prochain_numero:05d}"

    @property
    def est_fournisseur(self):
        """Indique si c'est un fournisseur"""
        return self.type_tiers in ['FLOC', 'FGRP']

    @property
    def est_client(self):
        """Indique si c'est un client"""
        return self.type_tiers in ['CLOC', 'CGRP']

    @property
    def est_employe(self):
        """Indique si c'est un employé"""
        return self.type_tiers == 'EMPL'

    @property
    def compte_comptable(self):
        """Retourne le compte comptable complet du tiers"""
        return self.code

    @property
    def solde_comptable(self):
        """Retourne le solde comptable du tiers"""
        # Sera implémenté avec le modèle LigneEcriture
        return 0

    def bloquer(self, motif):
        """Bloque le tiers avec un motif"""
        self.is_bloque = True
        self.motif_blocage = motif
        self.save()

    def debloquer(self):
        """Débloque le tiers"""
        self.is_bloque = False
        self.motif_blocage = ""
        self.save()