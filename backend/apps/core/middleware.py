# apps/core/middleware.py
from django.db import connection
from django_tenants.utils import get_tenant_model, schema_context
from django.conf import settings


class TenantDebugMiddleware:
    """
    Middleware pour gérer le tenant en développement
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Debug info
        print(f"[TENANT DEBUG] Request host: {request.get_host()}")
        print(f"[TENANT DEBUG] Current schema: {connection.schema_name}")

        # En développement, si on est sur localhost et qu'on accède à l'API
        if settings.DEBUG and request.path.startswith('/api/'):
            # Vérifier d'abord si un header X-Tenant est présent
            tenant_header = request.headers.get('X-Tenant')

            if tenant_header:
                print(f"[TENANT DEBUG] Header X-Tenant trouvé: {tenant_header}")
                # Utiliser le tenant spécifié dans le header
                try:
                    TenantModel = get_tenant_model()
                    tenant = TenantModel.objects.get(schema_name=tenant_header)
                    connection.set_tenant(tenant)
                    print(f"[TENANT DEBUG] Tenant défini via header: {tenant.schema_name}")
                except TenantModel.DoesNotExist:
                    print(f"[TENANT DEBUG] Tenant '{tenant_header}' non trouvé!")

            # Si pas de header et qu'on est sur localhost, forcer testcompany
            elif 'localhost' in request.get_host() or '127.0.0.1' in request.get_host():
                try:
                    TenantModel = get_tenant_model()
                    tenant = TenantModel.objects.get(schema_name='testcompany')
                    connection.set_tenant(tenant)
                    print(f"[TENANT DEBUG] Tenant forcé en dev: testcompany")
                except TenantModel.DoesNotExist:
                    print(f"[TENANT DEBUG] Tenant 'testcompany' non trouvé!")

        print(f"[TENANT DEBUG] Schema final: {connection.schema_name}")

        response = self.get_response(request)
        return response