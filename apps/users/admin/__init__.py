from .user_admin import UserAdmin
from .profile_admin import CompanyProfileAdmin, AccountantProfileAdmin
from .permission_admin import RoleAdmin, UserRoleAdmin, AuditLogAdmin

# Avec Django autodiscover_modules(), ce fichier sera importé automatiquement
# et les modèles seront enregistrés dans l'admin