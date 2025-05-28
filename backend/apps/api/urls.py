# apps/api/urls.py
"""
Configuration des URLs pour l'API REST
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView
)

# Import des ViewSets - CORRECTION: compte_ohada au lieu de compte
from apps.api.viewsets.compte_ohada import CompteOHADAViewSet
from apps.api.viewsets.journal import JournalViewSet
from apps.api.viewsets.tiers import TiersViewSet
from apps.api.viewsets.exercice import ExerciceComptableViewSet
from apps.api.viewsets.periode import PeriodeComptableViewSet
from .viewsets.ecriture import EcritureComptableViewSet
from .viewsets.ligne_ecriture import LigneEcritureViewSet

# Configuration du router
router = DefaultRouter()

# Enregistrement des ViewSets
router.register('comptes', CompteOHADAViewSet, basename='compte')
router.register('journaux', JournalViewSet, basename='journal')
router.register('tiers', TiersViewSet, basename='tiers')
router.register('exercices', ExerciceComptableViewSet, basename='exercice')
router.register('periodes', PeriodeComptableViewSet, basename='periode')
router.register(r'ecritures', EcritureComptableViewSet, basename='ecriture')
router.register(r'lignes-ecritures', LigneEcritureViewSet, basename='ligne-ecriture')

# URLs de l'API
urlpatterns = [
    # JWT Authentication
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('token/verify/', TokenVerifyView.as_view(), name='token_verify'),

    # API ViewSets
    path('', include(router.urls)),
]