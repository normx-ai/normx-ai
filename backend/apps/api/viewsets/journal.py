# backend/apps/api/viewsets/journal.py

from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count, Sum, Max

from apps.accounting.models import Journal
from apps.accounting.serializers.base import (
    JournalSerializer,
    JournalMinimalSerializer,
    JournalStatsSerializer
)


class JournalViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour la gestion des journaux comptables OHADA

    Endpoints:
    - GET /api/journaux/ : Liste tous les journaux
    - GET /api/journaux/{id}/ : Détail d'un journal
    - POST /api/journaux/ : Créer un journal
    - PUT /api/journaux/{id}/ : Modifier un journal
    - DELETE /api/journaux/{id}/ : Supprimer un journal

    Actions spéciales:
    - GET /api/journaux/actifs/ : Journaux actifs uniquement
    - GET /api/journaux/par_type/ : Journaux groupés par type
    - GET /api/journaux/{id}/stats/ : Statistiques d'un journal
    """

    queryset = Journal.objects.all()
    serializer_class = JournalSerializer
    permission_classes = [AllowAny]  # Pour le développement

    # Filtrage et recherche
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['type', 'is_active']
    search_fields = ['code', 'libelle']
    ordering_fields = ['code', 'libelle', 'created_at']
    ordering = ['code']  # Tri par défaut

    def get_queryset(self):
        """
        Optimise les requêtes en préchargeant les relations
        """
        queryset = super().get_queryset()

        # Précharger le compte de contrepartie
        queryset = queryset.select_related('compte_contrepartie')

        # Ajouter le nombre d'écritures si demandé
        if self.action == 'list':
            queryset = queryset.annotate(
                nb_ecritures=Count('ecritures', distinct=True)
            )

        return queryset

    def get_serializer_class(self):
        """
        Utilise différents serializers selon l'action
        """
        if self.action == 'list' and self.request.query_params.get('minimal'):
            return JournalMinimalSerializer
        elif self.action == 'stats':
            return JournalStatsSerializer
        return super().get_serializer_class()

    @action(detail=False, methods=['get'])
    def actifs(self, request):
        """
        Retourne uniquement les journaux actifs
        """
        journaux = self.get_queryset().filter(is_active=True)
        serializer = self.get_serializer(journaux, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def par_type(self, request):
        """
        Retourne les journaux groupés par type
        """
        result = {}

        for type_code, type_label in Journal.TYPES_JOURNAL:
            journaux = self.get_queryset().filter(type=type_code, is_active=True)
            if journaux.exists():
                serializer = JournalMinimalSerializer(journaux, many=True)
                result[type_code] = {
                    'label': type_label,
                    'count': journaux.count(),
                    'journaux': serializer.data
                }

        return Response(result)

    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """
        Retourne les statistiques détaillées d'un journal
        """
        journal = self.get_object()

        # Calculer les statistiques
        stats = {
            'journal': JournalSerializer(journal).data,
            'ecritures': {
                'total': 0,
                'brouillon': 0,
                'validees': 0,
                'annulees': 0
            },
            'montants': {
                'total_debits': 0,
                'total_credits': 0,
                'solde': 0
            },
            'periodes': {
                'premiere_ecriture': None,
                'derniere_ecriture': None,
                'mois_actifs': []
            }
        }

        # Si le journal a des écritures
        if hasattr(journal, 'ecritures'):
            ecritures = journal.ecritures.all()

            # Compte des écritures
            stats['ecritures']['total'] = ecritures.count()
            stats['ecritures']['brouillon'] = ecritures.filter(statut='BROUILLON').count()
            stats['ecritures']['validees'] = ecritures.filter(statut='VALIDEE').count()
            stats['ecritures']['annulees'] = ecritures.filter(statut='ANNULEE').count()

            # Montants (nécessite le modèle LigneEcriture)
            if ecritures.exists():
                from django.db.models import Sum

                totaux = ecritures.aggregate(
                    total_debits=Sum('lignes__montant_debit'),
                    total_credits=Sum('lignes__montant_credit')
                )

                stats['montants']['total_debits'] = float(totaux['total_debits'] or 0)
                stats['montants']['total_credits'] = float(totaux['total_credits'] or 0)
                stats['montants']['solde'] = stats['montants']['total_debits'] - stats['montants']['total_credits']

                # Périodes
                dates = ecritures.aggregate(
                    premiere=Min('date_ecriture'),
                    derniere=Max('date_ecriture')
                )

                stats['periodes']['premiere_ecriture'] = dates['premiere']
                stats['periodes']['derniere_ecriture'] = dates['derniere']

        return Response(stats)

    @action(detail=False, methods=['get'])
    def types_disponibles(self, request):
        """
        Retourne la liste des types de journaux disponibles
        """
        types = [
            {
                'code': code,
                'label': label,
                'count': Journal.objects.filter(type=code).count()
            }
            for code, label in Journal.TYPES_JOURNAL
        ]
        return Response(types)

    def perform_create(self, serializer):
        """
        Actions lors de la création d'un journal
        """
        # Convertir le code en majuscules
        if 'code' in serializer.validated_data:
            serializer.validated_data['code'] = serializer.validated_data['code'].upper()

        serializer.save()

    def perform_update(self, serializer):
        """
        Actions lors de la mise à jour d'un journal
        """
        # Convertir le code en majuscules
        if 'code' in serializer.validated_data:
            serializer.validated_data['code'] = serializer.validated_data['code'].upper()

        serializer.save()