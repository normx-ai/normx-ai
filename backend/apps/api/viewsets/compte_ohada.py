# apps/api/viewsets/compte_ohada.py
"""
ViewSet pour la gestion des comptes OHADA via API REST
Gère les comptes du plan comptable avec filtres et recherche
"""

from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django_filters import FilterSet, CharFilter, BooleanFilter, ChoiceFilter
from django.db.models import Q, Sum, Count, Prefetch
from rest_framework.permissions import AllowAny
from django.shortcuts import get_object_or_404
from rest_framework.pagination import PageNumberPagination

from apps.accounting.models import CompteOHADA, LigneEcriture
from apps.accounting.serializers.base import (
    CompteOHADASerializer,
    CompteOHADAMinimalSerializer,
    CompteOHADAStatsSerializer
)

class CompteOHADAPagination(PageNumberPagination):
    page_size = 100  # Afficher 100 comptes par page
    page_size_query_param = 'page_size'
    max_page_size = 2000  # Maximum 2000 comptes par page

class CompteOHADAFilter(FilterSet):
    """Filtre personnalisé pour les comptes OHADA"""

    code = CharFilter(field_name='code', lookup_expr='exact')
    code_startswith = CharFilter(field_name='code', lookup_expr='startswith')
    code_contains = CharFilter(field_name='code', lookup_expr='contains')
    libelle = CharFilter(field_name='libelle', lookup_expr='icontains')
    classe = CharFilter(field_name='classe', lookup_expr='exact')
    type = CharFilter(field_name='type', lookup_expr='exact')
    is_active = BooleanFilter(field_name='is_active')
    ref = CharFilter(field_name='ref', lookup_expr='exact')

    class Meta:
        model = CompteOHADA
        fields = ['code', 'code_startswith', 'code_contains', 'libelle',
                  'classe', 'type', 'is_active', 'ref']


class CompteOHADAViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour les comptes OHADA

    Endpoints:
    - GET /api/comptes/ - Liste des comptes
    - POST /api/comptes/ - Créer un compte
    - GET /api/comptes/{id}/ - Détail d'un compte
    - PUT /api/comptes/{id}/ - Modifier un compte
    - DELETE /api/comptes/{id}/ - Supprimer un compte

    Actions supplémentaires:
    - GET /api/comptes/actifs/ - Comptes actifs uniquement
    - GET /api/comptes/par-classe/ - Comptes groupés par classe
    - GET /api/comptes/{id}/stats/ - Statistiques d'un compte
    - GET /api/comptes/{id}/mouvements/ - Mouvements d'un compte
    - GET /api/comptes/search/ - Recherche avancée
    """

    queryset = CompteOHADA.objects.all()
    serializer_class = CompteOHADASerializer
    permission_classes = [AllowAny]  # AJOUTEZ CETTE LIGNE
    #permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = CompteOHADAFilter
    search_fields = ['code', 'libelle']
    ordering_fields = ['code', 'libelle', 'classe', 'created_at']
    ordering = ['code']
    pagination_class = CompteOHADAPagination  # AJOUTER CETTE LIGNE

    def get_serializer_class(self):
        """Retourne le serializer approprié selon l'action"""
        if self.action == 'list' and self.request.query_params.get('minimal'):
            return CompteOHADAMinimalSerializer
        elif self.action in ['stats', 'mouvements']:
            return CompteOHADAStatsSerializer
        return super().get_serializer_class()

    def get_queryset(self):
        """
        Retourne le queryset filtré selon les paramètres
        Applique automatiquement le filtre multi-tenant
        """
        queryset = super().get_queryset()

        # Filtres additionnels via query params
        params = self.request.query_params

        # Filtre par classe multiple
        classes = params.get('classes', '').split(',')
        if classes and classes[0]:
            queryset = queryset.filter(classe__in=classes)

        # Filtre par type multiple
        types = params.get('types', '').split(',')
        if types and types[0]:
            queryset = queryset.filter(type__in=types)

        # Filtre par niveau (longueur du code)
        niveau = params.get('niveau')
        if niveau:
            # Niveau 1: 2 chiffres, Niveau 2: 4 chiffres, etc.
            longueur = int(niveau) * 2
            queryset = queryset.filter(code__regex=f'^[0-9]{{{longueur}}}0*$')

        # Filtre pour exclure les comptes de niveau détail
        if params.get('principaux_seulement') == 'true':
            queryset = queryset.filter(code__regex=r'^[0-9]{2,6}0+$')

        # Préchargement pour optimisation
        if self.action in ['stats', 'mouvements']:
            queryset = queryset.prefetch_related(
                Prefetch('lignes_ecritures',
                         queryset=LigneEcriture.objects.select_related('ecriture'))
            )

        return queryset

    @action(detail=False, methods=['get'])
    def actifs(self, request):
        """Retourne uniquement les comptes actifs"""
        queryset = self.get_queryset().filter(is_active=True)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def par_classe(self, request):
        """Retourne les comptes groupés par classe"""
        comptes_par_classe = {}

        for classe in range(1, 10):
            classe_str = str(classe)
            comptes = self.get_queryset().filter(classe=classe_str)

            if comptes.exists():
                comptes_par_classe[f'classe_{classe}'] = {
                    'numero': classe,
                    'libelle': self._get_libelle_classe(classe),
                    'nb_comptes': comptes.count(),
                    'comptes': CompteOHADAMinimalSerializer(comptes[:10], many=True).data
                }

        return Response(comptes_par_classe)

    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """Retourne les statistiques d'utilisation d'un compte"""
        compte = self.get_object()
        serializer = CompteOHADAStatsSerializer(compte)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def mouvements(self, request, pk=None):
        """
        Retourne les mouvements (lignes d'écriture) d'un compte
        Avec pagination et filtres par date
        """
        compte = self.get_object()

        # Récupérer les lignes d'écriture
        lignes = compte.lignes_ecritures.select_related(
            'ecriture', 'ecriture__journal', 'tiers'
        )

        # Filtres par date
        date_debut = request.query_params.get('date_debut')
        date_fin = request.query_params.get('date_fin')

        if date_debut:
            lignes = lignes.filter(ecriture__date_ecriture__gte=date_debut)
        if date_fin:
            lignes = lignes.filter(ecriture__date_ecriture__lte=date_fin)

        # Ordre chronologique
        lignes = lignes.order_by('-ecriture__date_ecriture', '-ecriture__numero')

        # Pagination manuelle
        page_size = int(request.query_params.get('page_size', 20))
        page = int(request.query_params.get('page', 1))
        start = (page - 1) * page_size
        end = start + page_size

        # Calculer les totaux
        totaux = lignes.aggregate(
            total_debit=Sum('montant_debit'),
            total_credit=Sum('montant_credit'),
            nb_mouvements=Count('id')
        )

        # Préparer la réponse
        mouvements = []
        for ligne in lignes[start:end]:
            mouvements.append({
                'id': ligne.id,
                'date': ligne.ecriture.date_ecriture,
                'numero_ecriture': ligne.ecriture.numero,
                'journal': ligne.ecriture.journal.code,
                'libelle': ligne.libelle,
                'debit': float(ligne.montant_debit),
                'credit': float(ligne.montant_credit),
                'tiers': {
                    'code': ligne.tiers.code,
                    'nom': ligne.tiers.raison_sociale
                } if ligne.tiers else None,
                'lettrage': ligne.code_lettrage,
                'is_lettree': ligne.is_lettree
            })

        response_data = {
            'compte': {
                'code': compte.code,
                'libelle': compte.libelle
            },
            'periode': {
                'date_debut': date_debut,
                'date_fin': date_fin
            },
            'totaux': {
                'nb_mouvements': totaux['nb_mouvements'],
                'total_debit': float(totaux['total_debit'] or 0),
                'total_credit': float(totaux['total_credit'] or 0),
                'solde': float((totaux['total_debit'] or 0) - (totaux['total_credit'] or 0))
            },
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total': lignes.count()
            },
            'mouvements': mouvements
        }

        return Response(response_data)

    @action(detail=False, methods=['get'])
    def search(self, request):
        """
        Recherche avancée de comptes
        Permet de chercher par code ou libellé avec des critères multiples
        """
        query = request.query_params.get('q', '')
        if len(query) < 2:
            return Response({'error': 'La recherche doit contenir au moins 2 caractères'},
                            status=status.HTTP_400_BAD_REQUEST)

        # Recherche par code ou libellé
        queryset = self.get_queryset().filter(
            Q(code__icontains=query) |
            Q(libelle__icontains=query)
        )

        # Limiter les résultats
        queryset = queryset[:50]

        # Grouper par type de compte
        resultats = {
            'actif': [],
            'passif': [],
            'charge': [],
            'produit': []
        }

        for compte in queryset:
            data = CompteOHADAMinimalSerializer(compte).data
            resultats[compte.type].append(data)

        return Response({
            'query': query,
            'total': sum(len(v) for v in resultats.values()),
            'resultats': resultats
        })

    @action(detail=False, methods=['get'])
    def all(self, request):
        """Retourne tous les comptes sans pagination"""
        queryset = self.get_queryset().filter(is_active=True)
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'count': queryset.count(),
            'results': serializer.data
        })

    def create(self, request, *args, **kwargs):
        """Création d'un compte avec validation OHADA"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Vérifier l'unicité du code
        code = serializer.validated_data['code']
        if CompteOHADA.objects.filter(code=code).exists():
            return Response(
                {'error': f'Le compte {code} existe déjà'},
                status=status.HTTP_400_BAD_REQUEST
            )

        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        """Mise à jour d'un compte avec restrictions"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()

        # Empêcher la modification du code
        if 'code' in request.data and request.data['code'] != instance.code:
            return Response(
                {'error': 'Le code d\'un compte ne peut pas être modifié'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Vérifier si le compte est utilisé avant de le désactiver
        if 'is_active' in request.data and not request.data['is_active']:
            if instance.lignes_ecritures.exists():
                return Response(
                    {'error': 'Ce compte ne peut pas être désactivé car il est utilisé dans des écritures'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        """Suppression d'un compte (désactivation seulement)"""
        instance = self.get_object()

        # Ne pas supprimer physiquement, juste désactiver
        if instance.lignes_ecritures.exists():
            return Response(
                {'error': 'Ce compte ne peut pas être supprimé car il est utilisé dans des écritures'},
                status=status.HTTP_400_BAD_REQUEST
            )

        instance.is_active = False
        instance.save()

        return Response(
            {'message': f'Le compte {instance.code} a été désactivé'},
            status=status.HTTP_204_NO_CONTENT
        )

    def _get_libelle_classe(self, classe):
        """Retourne le libellé d'une classe de comptes"""
        libelles = {
            1: "Ressources durables",
            2: "Actif immobilisé",
            3: "Actif circulant HAO",
            4: "Tiers",
            5: "Trésorerie",
            6: "Charges des activités ordinaires",
            7: "Produits des activités ordinaires",
            8: "Autres charges et autres produits",
            9: "Comptes des engagements hors bilan"
        }
        return libelles.get(classe, f"Classe {classe}")