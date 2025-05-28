# apps/accounting/models/exercice.py
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta


class ExerciceComptable(models.Model):
    """
    Exercice comptable selon OHADA
    - Un exercice dure généralement 12 mois (du 01/01 au 31/12)
    - Peut être clôturé jusqu'au 30/06 de l'année suivante
    - Maximum 2 exercices peuvent être ouverts simultanément
    """

    STATUTS = [
        ('PREPARATION', 'En préparation'),
        ('OUVERT', 'Ouvert'),
        ('CLOTURE_PROVISOIRE', 'Clôture provisoire'),
        ('CLOTURE', 'Clôturé'),
        ('ARCHIVE', 'Archivé'),
    ]

    # Identification
    code = models.CharField(
        max_length=10,
        unique=True,
        help_text="Ex: 2025, 2024"
    )
    libelle = models.CharField(
        max_length=100,
        help_text="Ex: Exercice 2025"
    )

    # Dates de l'exercice
    date_debut = models.DateField(
        help_text="Généralement le 01/01/N"
    )
    date_fin = models.DateField(
        help_text="Généralement le 31/12/N"
    )

    # Dates de clôture
    date_cloture_provisoire = models.DateField(
        null=True,
        blank=True,
        help_text="Date de clôture provisoire (pour les écritures d'inventaire)"
    )
    date_cloture_definitive = models.DateField(
        null=True,
        blank=True,
        help_text="Date de clôture définitive (max 30/06/N+1)"
    )

    # Statut
    statut = models.CharField(
        max_length=20,
        choices=STATUTS,
        default='PREPARATION'
    )

    # Indicateurs
    is_premier_exercice = models.BooleanField(
        default=False,
        help_text="Premier exercice de la société"
    )

    # Report à nouveau
    report_a_nouveau_genere = models.BooleanField(
        default=False,
        help_text="Indique si les À Nouveaux ont été générés"
    )
    date_generation_an = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date de génération des À Nouveaux"
    )

    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='exercices_crees'
    )

    class Meta:
        verbose_name = "Exercice Comptable"
        verbose_name_plural = "Exercices Comptables"
        ordering = ['-date_debut']

    def __str__(self):
        return f"{self.libelle} ({self.get_statut_display()})"

    def clean(self):
        """Validations métier"""
        # Vérifier que date_fin > date_debut
        if self.date_debut and self.date_fin:
            if self.date_fin <= self.date_debut:
                raise ValidationError("La date de fin doit être après la date de début")

            # Vérifier la durée (max 18 mois pour un exercice exceptionnel)
            duree = (self.date_fin - self.date_debut).days
            if duree > 548:  # 18 mois
                raise ValidationError("Un exercice ne peut pas durer plus de 18 mois")

        # Vérifier qu'au maximum 2 exercices sont ouverts
        if self.statut == 'OUVERT':
            exercices_ouverts = ExerciceComptable.objects.filter(
                statut='OUVERT'
            ).exclude(pk=self.pk)
            if exercices_ouverts.count() >= 2:
                raise ValidationError("Maximum 2 exercices peuvent être ouverts simultanément")

        # Vérifier la date de clôture définitive (max 6 mois après la fin)
        if self.date_cloture_definitive and self.date_fin:
            date_limite = self.date_fin + relativedelta(months=6)
            if self.date_cloture_definitive > date_limite:
                raise ValidationError(
                    f"La clôture définitive doit être effectuée avant le {date_limite.strftime('%d/%m/%Y')}"
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def is_cloture_possible(self):
        """Vérifie si l'exercice peut être clôturé"""
        if self.statut != 'OUVERT':
            return False
        return date.today() > self.date_fin

    @property
    def date_limite_cloture(self):
        """Retourne la date limite de clôture (30/06/N+1)"""
        if not self.date_fin:
            return None
        return self.date_fin + relativedelta(months=6)

    @property
    def jours_restants_cloture(self):
        """Nombre de jours restants pour clôturer"""
        if self.statut in ['CLOTURE', 'ARCHIVE']:
            return 0
        if not self.date_limite_cloture:
            return None
        delta = self.date_limite_cloture - date.today()
        return max(0, delta.days)

    def ouvrir(self):
        """Ouvre l'exercice et crée automatiquement les périodes mensuelles"""
        if self.statut != 'PREPARATION':
            raise ValidationError("Seul un exercice en préparation peut être ouvert")

        # Vérifier qu'on n'a pas déjà 2 exercices ouverts
        exercices_ouverts = ExerciceComptable.objects.filter(statut='OUVERT').count()
        if exercices_ouverts >= 2:
            raise ValidationError(
                "Maximum 2 exercices peuvent être ouverts simultanément. Veuillez clôturer un exercice avant d'en ouvrir un nouveau.")

        # Vérifier la cohérence des dates si un autre exercice est ouvert
        if exercices_ouverts == 1:
            autre_exercice = ExerciceComptable.objects.filter(statut='OUVERT').first()
            # L'exercice à ouvrir doit être consécutif
            if self.date_debut <= autre_exercice.date_debut:
                raise ValidationError(f"Le nouvel exercice doit commencer après l'exercice {autre_exercice.code}")

        # Ouvrir l'exercice
        self.statut = 'OUVERT'
        self.save()

        # Créer automatiquement les périodes si elles n'existent pas
        if not self.periodes.exists():
            self._creer_periodes_mensuelles()

    def _creer_periodes_mensuelles(self):
        """Crée les 12 périodes mensuelles pour l'exercice"""
        from calendar import monthrange

        # Déterminer l'année de l'exercice
        annee = self.date_debut.year

        for mois in range(1, 13):
            # Calculer le premier et dernier jour du mois
            date_debut = date(annee, mois, 1)
            dernier_jour = monthrange(annee, mois)[1]
            date_fin = date(annee, mois, dernier_jour)

            # Ajuster si le mois dépasse la date de fin de l'exercice
            if date_debut > self.date_fin:
                break
            if date_fin > self.date_fin:
                date_fin = self.date_fin

            # Créer la période
            PeriodeComptable.objects.create(
                exercice=self,
                numero=mois,
                date_debut=date_debut,
                date_fin=date_fin,
                statut='OUVERTE'
            )

            # Si on a atteint la fin de l'exercice
            if date_fin >= self.date_fin:
                break

    def cloturer_provisoirement(self):
        """Clôture provisoire pour les écritures d'inventaire"""
        if self.statut != 'OUVERT':
            raise ValidationError("Seul un exercice ouvert peut être clôturé provisoirement")

        self.statut = 'CLOTURE_PROVISOIRE'
        self.date_cloture_provisoire = timezone.now().date()
        self.save()

    def cloturer_definitivement(self):
        """Clôture définitive de l'exercice"""
        if self.statut not in ['OUVERT', 'CLOTURE_PROVISOIRE']:
            raise ValidationError("L'exercice doit être ouvert ou en clôture provisoire")

        if date.today() > self.date_limite_cloture:
            raise ValidationError(
                f"La date limite de clôture ({self.date_limite_cloture.strftime('%d/%m/%Y')}) est dépassée"
            )

        self.statut = 'CLOTURE'
        self.date_cloture_definitive = timezone.now().date()
        self.save()

    def generer_a_nouveaux(self):
        """Génère les écritures d'À Nouveaux pour l'exercice suivant"""
        if self.statut != 'CLOTURE':
            raise ValidationError("L'exercice doit être clôturé pour générer les À Nouveaux")

        if self.report_a_nouveau_genere:
            raise ValidationError("Les À Nouveaux ont déjà été générés")

        # La logique de génération sera implémentée avec le modèle Ecriture
        self.report_a_nouveau_genere = True
        self.date_generation_an = timezone.now()
        self.save()


class PeriodeComptable(models.Model):
    """
    Période comptable mensuelle au sein d'un exercice
    Permet de gérer les clôtures mensuelles
    """

    STATUTS = [
        ('OUVERTE', 'Ouverte'),
        ('CLOTUREE', 'Clôturée'),
        ('VERROUILLEE', 'Verrouillée'),
    ]

    exercice = models.ForeignKey(
        ExerciceComptable,
        on_delete=models.CASCADE,
        related_name='periodes'
    )

    numero = models.PositiveSmallIntegerField(
        help_text="Numéro du mois (1-12)"
    )

    date_debut = models.DateField()
    date_fin = models.DateField()

    statut = models.CharField(
        max_length=20,
        choices=STATUTS,
        default='OUVERTE'
    )

    # Clôture mensuelle
    date_cloture = models.DateTimeField(
        null=True,
        blank=True
    )
    cloture_par = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='periodes_cloturees'
    )

    class Meta:
        verbose_name = "Période Comptable"
        verbose_name_plural = "Périodes Comptables"
        ordering = ['exercice', 'numero']
        unique_together = [['exercice', 'numero']]

    def __str__(self):
        mois = [
            'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
            'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre'
        ]
        return f"{mois[self.numero - 1]} {self.exercice.code}"

    def cloturer(self, user=None):
        """Clôture la période"""
        if self.statut != 'OUVERTE':
            raise ValidationError("Seule une période ouverte peut être clôturée")

        # Vérifier que les périodes précédentes sont clôturées
        periodes_precedentes = PeriodeComptable.objects.filter(
            exercice=self.exercice,
            numero__lt=self.numero,
            statut='OUVERTE'
        )
        if periodes_precedentes.exists():
            raise ValidationError("Les périodes précédentes doivent être clôturées")

        self.statut = 'CLOTUREE'
        self.date_cloture = timezone.now()
        self.cloture_par = user
        self.save()

    def verrouiller(self):
        """Verrouille définitivement la période"""
        if self.statut != 'CLOTUREE':
            raise ValidationError("Seule une période clôturée peut être verrouillée")

        self.statut = 'VERROUILLEE'
        self.save()

    @property
    def is_saisie_possible(self):
        """Indique si on peut saisir des écritures sur cette période"""
        return self.statut == 'OUVERTE' and self.exercice.statut in ['OUVERT', 'CLOTURE_PROVISOIRE']