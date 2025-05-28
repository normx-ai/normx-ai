# config/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from apps.accounting.views.test_serializers import test_serializers, test_serializers_minimal

urlpatterns = [
    path('admin/', admin.site.urls),

    # API avec namespace (IMPORTANT: utilisez cette syntaxe)
    path('api/', include(('apps.api.urls', 'api'), namespace='api')),

    # URLs de test temporaires
    path('test-serializers/', test_serializers, name='test_serializers'),
    path('test-serializers-minimal/', test_serializers_minimal, name='test_serializers_minimal'),
]

# Servir les fichiers media en développement
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)