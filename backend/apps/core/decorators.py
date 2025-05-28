from functools import wraps
from django.core.exceptions import PermissionDenied

def check_feature(feature_code):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            tenant = request.tenant
            if tenant.plan_limit and tenant.plan_limit.features.filter(code=feature_code).exists():
                return view_func(request, *args, **kwargs)
            raise PermissionDenied("Cette fonctionnalité n'est pas disponible dans votre plan")
        return wrapper
    return decorator

def check_limit(limit_type):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            tenant = request.tenant
            if limit_type == 'users':
                current_count = tenant.users.count()
                limit = tenant.plan_limit.max_users
                if current_count >= limit:
                    raise PermissionDenied(f"Limite d'utilisateurs atteinte ({limit})")
            # Ajouter d'autres types de limites
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator