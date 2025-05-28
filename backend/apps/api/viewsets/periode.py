# apps/api/viewsets/periode.py
"""
ViewSet pour la gestion des périodes comptables via API REST
"""

from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django_filters import FilterSet, NumberFilter, ChoiceFilter, DateFilter
from django.db.models import Q, Sum, Count, F
from django.shortcuts import get_object_or_404
from django.utils import timezone

from apps.accounting.models import PeriodeComptable, ExerciceComptable
from apps.accounting.serializers.exercices import (
    PeriodeComptableSerializer,
    PeriodeComptableMinimalSerializer
)


class PeriodeComptableFilter(FilterSet):
    """Filtre pour les périodes comptables"""

    exercice = NumberFilter(field_name='exercice__id')
    exercice_code = NumberFilter(field_name='exercice__code')
    numero = NumberFilter(field_name='numero')
    statut = ChoiceFilter(field_name='statut', choices=PeriodeComptable.STATUTS)
    date_debut_after = DateFilter(field_name='date_debut', lookup_expr='gte')
    date_debut_before = DateFilter(field_name='date_debut', lookup_expr='lte')
    date_fin_after = DateFilter(field_name='date_fin', lookup_expr='gte')
    date_fin_before = DateFilter(field_name='date_fin', lookup_expr='lte')

    class Meta:
        model = PeriodeComptable
        fields = ['exercice', 'numero', 'statut']


class PeriodeComptableViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour les périodes comptables

    Endpoints:
    - GET /api/periodes/ - Liste des périodes
    - POST /api/periodes/ - Créer une période
    - GET /api/periodes/{id}/ - Détail d'une période
    - PUT /api/periodes/{id}/ - Modifier une période
    - DELETE /api/periodes/{id}/ - Supprimer une période

    Actions supplémentaires:
    - GET /api/periodes/ouvertes/ - Périodes ouvertes uniquement
    - GET /api/periodes/en_cours/ - Période en cours (date du jour)
    - GET /api/periodes/{id}/stats/ - Statistiques de la période
    - GET /api/periodes/{id}/ecritures/ - Écritures de la période
    - POST /api/periodes/{id}/cloturer/ - Clôturer une période
    - POST /api/periodes/{id}/rouvrir/ - Rouvrir une période
    - POST /api/periodes/{id}/verrouiller/ - Verrouiller une période
    - GET /api/periodes/par_exercice/{exercice_id}/ - Périodes d'un exercice
    """

    queryset = PeriodeComptable.objects.all()
    serializer_class = PeriodeComptableSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = PeriodeComptableFilter
    ordering_fields = ['exercice', 'numero', 'date_debut']
    ordering = ['exercice', 'numero']

    def get_serializer_class(self):
        """Retourne le serializer approprié selon l'action"""
        if self.action == 'list' and self.request.query_params.get('minimal'):
            return PeriodeComptableMinimalSerializer
        return super().get_serializer_class()

    def get_queryset(self):
        """Retourne le queryset avec optimisations"""
        queryset = super().get_queryset()

        # Préchargement pour optimisation
        queryset = queryset.select_related('exercice', 'cloture_par')

        # Filtrer par exercice si spécifié dans l'URL
        exercice_id = self.kwargs.get('exercice_id')
        if exercice_id:
            queryset = queryset.filter(exercice_id=exercice_id)

        # Inclure les statistiques si demandé
        if self.request.query_params.get('with_stats'):
            # Les statistiques d'écritures seront ajoutées avec le modèle EcritureComptable
            pass

        return queryset

    @action(detail=False, methods=['get'])
    def ouvertes(self, request):
        """Retourne uniquement les périodes ouvertes"""
        queryset = self.get_queryset().filter(statut='OUVERTE')

        # Filtrer par exercice si spécifié
        exercice_id = request.query_params.get('exercice')
        if exercice_id:
            queryset = queryset.filter(exercice_id=exercice_id)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def en_cours(self, request):
        """Retourne la période en cours (contenant la date du jour)"""
        today = timezone.now().date()

        # D'abord trouver l'exercice en cours
        exercice = ExerciceComptable.objects.filter(
            date_debut__lte=today,
            date_fin__gte=today,
            statut='OUVERT'
        ).first()

        if not exercice:
            return Response(
                {'message': 'Aucun exercice ouvert pour la date du jour'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Puis trouver la période correspondante
        periode = self.get_queryset().filter(
            exercice=exercice,
            date_debut__lte=today,
            date_fin__gte=today
        ).first()

        if periode:
            serializer = self.get_serializer(periode)
            return Response(serializer.data)

        return Response(
            {'message': 'Aucune période trouvée pour la date du jour'},
            status=status.HTTP_404_NOT_FOUND
        )

    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """Retourne les statistiques de la période"""
        periode = self.get_object()

        # Statistiques de base
        stats = {
            'periode': {
                'id': periode.id,
                'libelle': str(periode),
                'statut': periode.statut,
                'date_debut': periode.date_debut,
                'date_fin': periode.date_fin
            },
            'indicateurs': {
                'nb_jours': (periode.date_fin - periode.date_debut).days + 1,
                'peut_etre_cloturee': periode.is_saisie_possible,
                'jours_restants': max(0, (periode.date_fin - timezone.now().date()).days)
            },
            'ecritures': {
                'nb_total': 0,
                'nb_brouillon': 0,
                'nb_validees': 0
            },
            'mouvements': {
                'total_debit': 0,
                'total_credit': 0
            }
        }

        # Les statistiques d'écritures seront ajoutées avec le modèle EcritureComptable

        return Response(stats)

    @action(detail=True, methods=['get'])
    def ecritures(self, request, pk=None):
        """Retourne les écritures de la période"""
        periode = self.get_object()

        # Cette fonctionnalité sera implémentée avec le modèle EcritureComptable
        return Response({
            'periode': {
                'id': periode.id,
                'libelle': str(periode)
            },
            'ecritures': [],
            'totaux': {
                'nb_ecritures': 0,
                'total_debit': 0,
                'total_credit': 0
            }
        })

    @action(detail=True, methods=['post'])
    def cloturer(self, request, pk=None):
        """Clôture une période"""
        periode = self.get_object()

        try:
            # Vérifier que l'exercice est ouvert
            if periode.exercice.statut != 'OUVERT':
                return Response(
                    {'error': "L'exercice doit être ouvert pour clôturer une période"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Clôturer la période
            periode.cloturer(user=request.user)

            serializer = self.get_serializer(periode)
            return Response({
                'message': f"La période {periode} a été clôturée",
                'periode': serializer.data
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def rouvrir(self, request, pk=None):
        """Rouvre une période clôturée"""
        periode = self.get_object()

        # Vérifier les permissions (admin seulement)
        if not request.user.is_staff:
            return Response(
                {'error': 'Seul un administrateur peut rouvrir une période'},
                status=status.HTTP_403_FORBIDDEN
            )

        if periode.statut == 'VERROUILLEE':
            return Response(
                {'error': 'Une période verrouillée ne peut pas être rouverte'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if periode.statut == 'OUVERTE':
            return Response(
                {'error': 'Cette période est déjà ouverte'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Rouvrir la période
        periode.statut = 'OUVERTE'
        periode.date_cloture = None
        periode.cloture_par = None
        periode.save()

        serializer = self.get_serializer(periode)
        return Response({
            'message': f"La période {periode} a été rouverte",
            'periode': serializer.data
        })

    @action(detail=True, methods=['post'])
    def verrouiller(self, request, pk=None):
        """Verrouille définitivement une période"""
        periode = self.get_object()

        # Vérifier les permissions (admin seulement)
        if not request.user.is_staff:
            return Response(
                {'error': 'Seul un administrateur peut verrouiller une période'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            periode.verrouiller()

            serializer = self.get_serializer(periode)
            return Response({
                'message': f"La période {periode} a été verrouillée définitivement",
                'periode': serializer.data
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['get'], url_path='par_exercice/(?P<exercice_id>[^/.]+)')
    def par_exercice(self, request, exercice_id=None):
        """Retourne toutes les périodes d'un exercice"""
        try:
            exercice = ExerciceComptable.objects.get(id=exercice_id)
        except ExerciceComptable.DoesNotExist:
            return Response(
                {'error': 'Exercice introuvable'},
                status=status.HTTP_404_NOT_FOUND
            )

        periodes = self.get_queryset().filter(exercice=exercice).order_by('numero')
        serializer = self.get_serializer(periodes, many=True)

        return Response({
            'exercice': {
                'id': exercice.id,
                'libelle': exercice.libelle,
                'statut': exercice.statut
            },
            'periodes': serializer.data,
            'statistiques': {
                'nb_total': periodes.count(),
                'nb_ouvertes': periodes.filter(statut='OUVERTE').count(),
                'nb_cloturees': periodes.filter(statut='CLOTUREE').count(),
                'nb_verrouillees': periodes.filter(statut='VERROUILLEE').count()
            }
        })

    def create(self, request, *args, **kwargs):
        """Création d'une période (rarement utilisé, généralement auto-généré)"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Vérifier que l'exercice n'est pas clôturé
        exercice = serializer.validated_data['exercice']
        if exercice.statut in ['CLOTURE', 'ARCHIVE']:
            return Response(
                {'error': "Impossible d'ajouter une période à un exercice clôturé"},
                status=status.HTTP_400_BAD_REQUEST
            )

        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        """Mise à jour d'une période (limitée)"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()

        # Vérifier le statut
        if instance.statut in ['CLOTUREE', 'VERROUILLEE']:
            return Response(
                {'error': 'Une période clôturée ne peut pas être modifiée'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Empêcher la modification de certains champs
        fields_readonly = ['exercice', 'numero']
        for field in fields_readonly:
            if field in request.data:
                return Response(
                    {'error': f"Le champ '{field}' ne peut pas être modifié"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        """Suppression d'une période (très restreint)"""
        instance = self.get_object()

        # Vérifier le statut
        if instance.statut != 'OUVERTE':
            return Response(
                {'error': 'Seule une période ouverte peut être supprimée'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Vérifier qu'il n'y a pas d'écritures
        # Cette vérification sera ajoutée avec le modèle EcritureComptable

        # Vérifier que c'est la dernière période de l'exercice
        derniere_periode = PeriodeComptable.objects.filter(
            exercice=instance.exercice
        ).order_by('-numero').first()

        if instance.id != derniere_periode.id:
            return Response(
                {'error': 'Seule la dernière période peut être supprimée'},
                status=status.HTTP_400_BAD_REQUEST
            )

        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)