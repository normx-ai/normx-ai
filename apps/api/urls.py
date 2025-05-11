# -*- coding: utf-8 -*-
from django.urls import path, include

# Liste des patterns d'URL pour l'API centrale
urlpatterns = [
    # Inclusion des URLs d'API de chaque application
    # path('users/', include('apps.users.api.urls')),
    # path('comptabilite/', include('apps.comptabilite.api.urls')),
    # path('agents/', include('apps.agents.api.urls')),
    
    # API generiques
    # path('token/', token_obtain_view, name='token_obtain'),
    # path('token/refresh/', token_refresh_view, name='token_refresh'),
]