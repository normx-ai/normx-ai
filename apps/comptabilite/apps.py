# -*- coding: utf-8 -*-
from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

class ComptabiliteConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.comptabilite'
    verbose_name = _('Comptabilite')