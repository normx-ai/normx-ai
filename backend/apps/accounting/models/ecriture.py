# apps/accounting/models/ecriture.py
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Sum, Q
from decimal import Decimal
from datetime import date


class EcritureComptable(models.Model):
    """
    En-tête d'écriture comptable selon OHADA
    Reproduit le modèle Sage avec en-tête + lignes
    """

    STATUTS = [
        ('BROUILLON', 'Brouillon'),
        ('VALIDEE', 'Validée'),
        ('CLOTUREE', 'Clôturée'),
    ]

    # Identification
    numero = models.CharField(
        max_length=20,
        unique=True,
        help_text="Numéro automatique : AC240001, VT240002, etc."
    )

    # Références journal et période
    journal = models.ForeignKey(
        'Journal',
        on_delete=models.PROTECT,
        related_name='ecritures',
        help_text="Journal comptable (AC, VT, BQ, etc.)"
    )

    exercice = models.ForeignKey(
        'ExerciceComptable',
        on_delete=models.PROTECT,
        related_name='ecritures'
    )

    periode = models.ForeignKey(
        'PeriodeComptable',
        on_delete=models.PROTECT,
        related_name='ecritures'
    )

    # Dates
    date_ecriture = models.DateField(
        default=date.today,
        help_text="Date de l'écriture comptable"
    )

    date_piece = models.DateField(
        null=True,
        blank=True,
        help_text="Date de la pièce justificative"
    )

    # Libellé général
    libelle = models.CharField(
        max_length=200,
        help_text="Libellé général de l'écriture (ex: RELEVES, FACTURE, etc.)"
    )

    # Référence externe
    reference = models.CharField(
        max_length=50,
        blank=True,
        help_text="Référence externe (numéro facture, etc.)"
    )

    # Statut et validation
    statut = models.CharField(
        max_length=10,
        choices=STATUTS,
        default='BROUILLON'
    )

    # Validation automatique
    is_equilibree = models.BooleanField(
        default=False,
        help_text="Écriture équilibrée (débit = crédit)"
    )

    montant_total = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        help_text="Montant total au débit (= crédit si équilibrée)"
    )

    # Validation
    date_validation = models.DateTimeField(
        null=True,
        blank=True
    )

    validee_par = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ecritures_validees'
    )

    # Lettrage
    is_lettree = models.BooleanField(
        default=False,
        help_text="Écriture lettrée"
    )

    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='ecritures_creees'
    )

    class Meta:
        verbose_name = "Écriture Comptable"
        verbose_name_plural = "Écritures Comptables"
        ordering = ['-date_ecriture', '-numero']
        indexes = [
            models.Index(fields=['journal', 'date_ecriture']),
            models.Index(fields=['exercice', 'periode']),
            models.Index(fields=['statut']),
        ]

    def __str__(self):
        return f"{self.numero} - {self.journal.code} - {self.libelle}"

    def clean(self):
        """Validations métier"""
        # Vérifier que la période est ouverte
        if self.periode and not self.periode.is_saisie_possible:
            raise ValidationError("Impossible de saisir sur une période fermée")

        # Vérifier que la date est dans la période
        if self.date_ecriture and self.periode:
            if not (self.periode.date_debut <= self.date_ecriture <= self.periode.date_fin):
                raise ValidationError(
                    f"La date doit être comprise entre {self.periode.date_debut} et {self.periode.date_fin}"
                )

        # Auto-déterminer la période si non définie
        if self.date_ecriture and self.exercice and not self.periode:
            try:
                self.periode = self.exercice.periodes.get(
                    date_debut__lte=self.date_ecriture,
                    date_fin__gte=self.date_ecriture
                )
            except:
                raise ValidationError("Aucune période trouvée pour cette date")

    def save(self, *args, **kwargs):
        # Générer le numéro si nouveau
        if not self.pk and not self.numero:
            self.numero = self._generer_numero()

        # Auto-déterminer l'exercice si non défini
        if self.periode and not self.exercice:
            self.exercice = self.periode.exercice

        self.full_clean()
        super().save(*args, **kwargs)

        # Recalculer l'équilibre après sauvegarde
        self._calculer_equilibre()

    def _generer_numero(self):
        """Génère automatiquement le numéro d'écriture"""
        if not self.journal:
            raise ValidationError("Le journal doit être défini")

        # Format : AC240001, VT240002, etc.
        annee = str(self.date_ecriture.year)[2:] if self.date_ecriture else str(date.today().year)[2:]

        # Trouver le dernier numéro pour ce journal cette année
        prefix = f"{self.journal.code}{annee}"

        derniere_ecriture = EcritureComptable.objects.filter(
            numero__startswith=prefix
        ).order_by('-numero').first()

        if derniere_ecriture:
            # Extraire le numéro et l'incrémenter
            try:
                dernier_num = int(derniere_ecriture.numero[len(prefix):])
                nouveau_num = dernier_num + 1
            except:
                nouveau_num = 1
        else:
            nouveau_num = 1

        return f"{prefix}{nouveau_num:04d}"

    def _calculer_equilibre(self):
        """Calcule l'équilibre de l'écriture"""
        lignes = self.lignes.all()

        total_debit = lignes.aggregate(
            total=Sum('montant_debit')
        )['total'] or Decimal('0')

        total_credit = lignes.aggregate(
            total=Sum('montant_credit')
        )['total'] or Decimal('0')

        self.montant_total = total_debit
        self.is_equilibree = (total_debit == total_credit and total_debit > 0)

        # Sauvegarder sans déclencher les signaux
        EcritureComptable.objects.filter(pk=self.pk).update(
            montant_total=self.montant_total,
            is_equilibree=self.is_equilibree
        )

    @property
    def total_debit(self):
        """Total des débits"""
        return self.lignes.aggregate(
            total=Sum('montant_debit')
        )['total'] or Decimal('0')

    @property
    def total_credit(self):
        """Total des crédits"""
        return self.lignes.aggregate(
            total=Sum('montant_credit')
        )['total'] or Decimal('0')

    @property
    def difference(self):
        """Différence débit - crédit"""
        return self.total_debit - self.total_credit

    def valider(self, user=None):
        """Valide l'écriture"""
        if not self.is_equilibree:
            raise ValidationError("L'écriture doit être équilibrée pour être validée")

        if not self.lignes.exists():
            raise ValidationError("L'écriture doit contenir au moins une ligne")

        self.statut = 'VALIDEE'
        self.date_validation = timezone.now()
        self.validee_par = user
        self.save()

    def dupliquer(self):
        """Duplique l'écriture avec un nouveau numéro"""
        lignes_originales = list(self.lignes.all())

        # Dupliquer l'en-tête
        self.pk = None
        self.numero = None  # Sera régénéré
        self.statut = 'BROUILLON'
        self.date_validation = None
        self.validee_par = None
        self.save()

        # Dupliquer les lignes
        for ligne in lignes_originales:
            ligne.pk = None
            ligne.ecriture = self
            ligne.save()

        return self


class LigneEcriture(models.Model):
    """
    Ligne d'écriture comptable
    Reproduit les lignes du style Sage
    """

    # Lien avec l'en-tête
    ecriture = models.ForeignKey(
        EcritureComptable,
        on_delete=models.CASCADE,
        related_name='lignes'
    )

    # Numéro de ligne (pour l'ordre)
    numero_ligne = models.PositiveSmallIntegerField(
        default=1,
        help_text="Ordre de la ligne dans l'écriture"
    )

    # Date de la ligne (jour dans le mois)
    date_ligne = models.DateField(
        null=True,
        blank=True,
        help_text="Date spécifique de la ligne (si différente de l'écriture)"
    )

    # Compte comptable
    compte = models.ForeignKey(
        'CompteOHADA',
        on_delete=models.PROTECT,
        related_name='lignes_ecritures',
        help_text="Compte du plan OHADA"
    )

    # Tiers (optionnel pour comptes auxiliaires)
    tiers = models.ForeignKey(
        'Tiers',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='lignes_ecritures',
        help_text="Tiers pour les comptes auxiliaires"
    )

    # Pièce justificative
    piece = models.CharField(
        max_length=50,
        blank=True,
        help_text="Référence pièce (EDF, LOYER, etc.)"
    )

    # Libellé de la ligne
    libelle = models.CharField(
        max_length=200,
        help_text="Libellé de la ligne comptable"
    )

    # Montants - exactement comme Sage
    montant_debit = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        help_text="Montant au débit"
    )

    montant_credit = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        help_text="Montant au crédit"
    )

    # Devise (pour le multi-devises)
    devise = models.CharField(
        max_length=3,
        default='XAF',
        help_text="Code devise ISO"
    )

    # Lettrage
    code_lettrage = models.CharField(
        max_length=10,
        blank=True,
        help_text="Code de lettrage pour rapprochement"
    )

    is_lettree = models.BooleanField(
        default=False
    )

    # Échéance (pour les tiers)
    date_echeance = models.DateField(
        null=True,
        blank=True,
        help_text="Date d'échéance pour les tiers"
    )

    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Ligne d'Écriture"
        verbose_name_plural = "Lignes d'Écriture"
        ordering = ['ecriture', 'numero_ligne']
        indexes = [
            models.Index(fields=['compte', 'ecriture']),
            models.Index(fields=['tiers']),
            models.Index(fields=['code_lettrage']),
        ]

    def __str__(self):
        sens = "D" if self.montant_debit > 0 else "C"
        montant = self.montant_debit if self.montant_debit > 0 else self.montant_credit
        return f"{self.compte.code} - {self.libelle} - {montant} {sens}"

    def clean(self):
        """Validations métier"""
        # Un seul montant doit être renseigné (débit OU crédit)
        if self.montant_debit > 0 and self.montant_credit > 0:
            raise ValidationError("Une ligne ne peut pas avoir à la fois un débit et un crédit")

        if self.montant_debit == 0 and self.montant_credit == 0:
            raise ValidationError("Une ligne doit avoir soit un débit soit un crédit")

        # Vérifier que le tiers correspond au compte
        if self.tiers and self.compte:
            # Les comptes auxiliaires (classe 4) doivent avoir un tiers
            if self.compte.classe == '4' and not self.tiers:
                raise ValidationError("Un tiers est obligatoire pour les comptes de classe 4")

            # Vérifier la cohérence tiers/compte
            if self.tiers and self.compte.classe == '4':
                if not self.compte.code.startswith(self.tiers.compte_collectif.code[:4]):
                    raise ValidationError(
                        f"Le compte {self.compte.code} ne correspond pas au tiers {self.tiers.code}"
                    )

    def save(self, *args, **kwargs):
        # Auto-numérotation des lignes
        if not self.numero_ligne:
            max_num = self.ecriture.lignes.aggregate(
                max_num=models.Max('numero_ligne')
            )['max_num'] or 0
            self.numero_ligne = max_num + 1

        # Auto-remplir le libellé si vide
        if not self.libelle and self.ecriture:
            self.libelle = self.ecriture.libelle

        # Calculer l'échéance automatique pour les tiers
        if self.tiers and not self.date_echeance and self.ecriture:
            from datetime import timedelta
            self.date_echeance = self.ecriture.date_ecriture + timedelta(
                days=self.tiers.delai_paiement
            )

        self.full_clean()
        super().save(*args, **kwargs)

        # Recalculer l'équilibre de l'écriture parent
        if self.ecriture_id:
            self.ecriture._calculer_equilibre()

    def delete(self, *args, **kwargs):
        ecriture = self.ecriture
        super().delete(*args, **kwargs)
        # Recalculer l'équilibre après suppression
        if ecriture:
            ecriture._calculer_equilibre()

    @property
    def sens(self):
        """Retourne D pour débit, C pour crédit"""
        return "D" if self.montant_debit > 0 else "C"

    @property
    def montant(self):
        """Retourne le montant de la ligne (débit ou crédit)"""
        return self.montant_debit if self.montant_debit > 0 else self.montant_credit

    def lettrer_avec(self, autres_lignes):
        """Lettre cette ligne avec d'autres lignes"""
        # Générer un code de lettrage unique
        from django.utils.crypto import get_random_string
        code = get_random_string(6, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')

        # Appliquer le lettrage
        self.code_lettrage = code
        self.is_lettree = True
        self.save()

        for ligne in autres_lignes:
            ligne.code_lettrage = code
            ligne.is_lettree = True
            ligne.save()

    def delettrer(self):
        """Supprime le lettrage de cette ligne"""
        self.code_lettrage = ""
        self.is_lettree = False
        self.save()