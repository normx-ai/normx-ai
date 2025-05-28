from django.contrib import admin
from .models import CompteOHADA


@admin.register(CompteOHADA)
class CompteOHADAAdmin(admin.ModelAdmin):
    list_display = ['code', 'libelle', 'classe', 'type', 'ref', 'is_active']
    list_filter = ['classe', 'type', 'is_active']
    search_fields = ['code', 'libelle']
    ordering = ['code']
    list_per_page = 50

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Grouper par classe pour une meilleure lisibilité
        return qs.order_by('classe', 'code')