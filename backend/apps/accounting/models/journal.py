from django.db import models
from django.core.validators import RegexValidator


class Journal(models.Model):
    """
    Journal comptable selon OHADA
    """
    TYPES_JOURNAL = [
        # Journaux principaux
        ('AC', 'Achats'),
        ('VT', 'Ventes'),
        ('BQ', 'Banque'),
        ('CA', 'Caisse'),

        # Journaux spécialisés
        ('PA', 'Paie et Salaires'),
        ('FI', 'Fiscal et Déclarations'),  # TVA, IS, IRPP
        ('SO', 'Social'),  # CNPS, cotisations
        ('ST', 'Stocks et Inventaires'),
        ('IM', 'Immobilisations'),
        ('PR', 'Provisions'),

        # Journaux techniques
        ('AN', 'À nouveaux'),
        ('CL', 'Clôture'),
        ('OD', 'Opérations Diverses'),
        ('EX', 'Extra-comptable'),
    ]
    
    code = models.CharField(
        max_length=10,
        unique=True,
        validators=[RegexValidator(r'^[A-Z0-9]+$', 'Le code doit contenir uniquement des lettres majuscules et chiffres')]
    )
    libelle = models.CharField(max_length=100)
    type = models.CharField(max_length=2, choices=TYPES_JOURNAL)
    
    # Compte de contrepartie par défaut (optionnel)
    compte_contrepartie = models.ForeignKey(
        'CompteOHADA',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='journaux_contrepartie'
    )
    
    # Métadonnées
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Journal"
        verbose_name_plural = "Journaux"
        ordering = ['code']
        
    def __str__(self):
        return f"{self.code} - {self.libelle}"
