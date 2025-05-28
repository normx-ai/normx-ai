from django.db import models
import uuid


class PlanFeature(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    
    class Meta:
        verbose_name = "Fonctionnalité"
        verbose_name_plural = "Fonctionnalités"
    
    def __str__(self):
        return self.name


class PlanLimit(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    plan_type = models.CharField(max_length=30)
    max_users = models.IntegerField(default=5)
    max_enterprises = models.IntegerField(default=1)
    max_ai_calls = models.IntegerField(default=100)
    storage_gb = models.IntegerField(default=5)
    features = models.ManyToManyField(PlanFeature)

    class Meta:
        verbose_name = "Limite de plan"
        verbose_name_plural = "Limites de plan"

    def __str__(self):
        return f"{self.plan_type} - {self.max_users} users - {self.max_enterprises} enterprises"
