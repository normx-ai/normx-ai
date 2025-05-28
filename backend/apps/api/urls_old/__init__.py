# apps/api/urls/__init__.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView
)

from apps.api.viewsets.compte_ohada import CompteOHADAViewSet

# Créer le router
router = DefaultRouter()

# Enregistrer les ViewSets
router.register(r'comptes', CompteOHADAViewSet, basename='compte')

# URLs de l'application
app_name = 'api'

urlpatterns = [
    # JWT Authentication
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('token/verify/', TokenVerifyView.as_view(), name='token_verify'),

    # API Routes
    path('', include(router.urls)),
