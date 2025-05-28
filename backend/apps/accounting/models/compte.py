from django.db import models
from django.core.validators import RegexValidator


class CompteOHADA(models.Model):
    """
    Modèle pour les comptes du plan comptable OHADA
    """
    TYPES_COMPTE = [
        ('actif', 'Actif'),
        ('passif', 'Passif'),
        ('charge', 'Charge'),
        ('produit', 'Produit'),
    ]

    code = models.CharField(
        max_length=10,
        unique=True,
        validators=[RegexValidator(r'^\d{8}$', 'Le code doit contenir exactement 8 chiffres')]
    )
    libelle = models.CharField(max_length=255)
    classe = models.CharField(max_length=1)  # 1-9
    type = models.CharField(max_length=20, choices=TYPES_COMPTE)
    ref = models.CharField(max_length=5, blank=True)  # Ex: CA, CB, etc.
    solde_normal = models.CharField(
        max_length=20,
        choices=[
            ('debiteur', 'Débiteur'),
            ('crediteur', 'Créditeur'),
            ('variable', 'Variable'),
        ],
        default='debiteur',
        help_text="Solde normal du compte selon OHADA"
    )

    note = models.TextField(
        blank=True,
        null=True,
        help_text="Notes ou précisions sur le compte"
    )

    # Métadonnées
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Compte OHADA"
        verbose_name_plural = "Comptes OHADA"
        ordering = ['code']

    def __str__(self):
        return f"{self.code} - {self.libelle}"