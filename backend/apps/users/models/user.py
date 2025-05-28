from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Modèle utilisateur personnalisé pour NORMXIA
    """
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True)

    # Pour les cabinets : peut gérer plusieurs entreprises
    can_manage_multiple_companies = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Utilisateur"
        verbose_name_plural = "Utilisateurs"