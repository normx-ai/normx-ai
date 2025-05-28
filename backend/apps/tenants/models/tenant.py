from django.db import models
from django_tenants.models import TenantMixin
from .plan import PlanLimit


class Tenant(TenantMixin):
    """
    Modèle Tenant pour normx-ai.com
    """
    
    # Types de tenants
    TENANT_TYPES = [
        ('ENTERPRISE', 'Entreprise'),
        ('CABINET', 'Cabinet comptable'),
    ]
    
    # Plans d'abonnement
    PLAN_CHOICES = [
        ('starter', 'Starter'),
        ('professional', 'Professional'),
        ('enterprise', 'Enterprise'),
        ('cabinet_start', 'Cabinet Start'),
        ('cabinet_pro', 'Cabinet Pro'),
        ('cabinet_unlimited', 'Cabinet Unlimited'),
    ]
    
    name = models.CharField(max_length=255, verbose_name="Nom")
    tenant_type = models.CharField(
        max_length=20,
        choices=TENANT_TYPES,
        default='ENTERPRISE'
    )
    plan = models.CharField(
        max_length=30,
        choices=PLAN_CHOICES,
        default='starter'
    )
    email = models.EmailField()
    created_on = models.DateField(auto_now_add=True)
    
    auto_create_schema = True

    plan_limit = models.ForeignKey(PlanLimit, on_delete=models.PROTECT, null=True, related_name='tenants')
    
    def __str__(self):
        return self.name
