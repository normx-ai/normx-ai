# Administration Comptabilité

Ce répertoire contiendra les fichiers d'administration pour l'application de comptabilité.

## Structure proposée

Quand les modèles de comptabilité seront implémentés, vous devrez créer les fichiers admin suivants :

1. `company_admin.py` - Administration des entreprises et leurs données comptables
2. `department_admin.py` - Administration des départements et sections comptables
3. `relationship_admin.py` - Administration des relations entre entités comptables

## Implémentation

Pour chaque modèle, créez une classe d'administration qui hérite de `admin.ModelAdmin`, par exemple :

```python
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from ..models import CompanyModel

@admin.register(CompanyModel)
class CompanyModelAdmin(admin.ModelAdmin):
    list_display = ('name', 'tax_id', 'created_at')
    list_filter = ('active', 'created_at')
    search_fields = ('name', 'tax_id')
    
    fieldsets = (
        (None, {'fields': ('name', 'tax_id')}),
        (_('Détails'), {
            'fields': ('description', 'active'),
        }),
        (_('Dates'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    readonly_fields = ('created_at', 'updated_at')
```

Puis, importez et enregistrez tous les admin dans le fichier `__init__.py`.