# -*- coding: utf-8 -*-
from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.users'
    verbose_name = _('Utilisateurs')
    
    def ready(self):
        # Importer les signaux au démarrage de l'application
        import apps.users.signals