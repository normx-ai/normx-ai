# apps/api/viewsets/exercice.py
"""
ViewSet pour la gestion des exercices comptables via API REST
"""

from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django_filters import FilterSet, CharFilter, BooleanFilter, ChoiceFilter, DateFilter
from django.db.models import Q, Sum, Count, F, Prefetch
from rest_framework.permissions import AllowAny
from django.shortcuts import get_object_or_404
from django.utils import timezone

from apps.accounting.models import ExerciceComptable, PeriodeComptable, EcritureComptable
from apps.accounting.serializers.exercices import (
    ExerciceComptableSerializer,
    ExerciceComptableMinimalSerializer,
    ExerciceComptableStatsSerializer,
    ClotureExerciceSerializer,
    PeriodeComptableSerializer
)


class ExerciceComptableFilter(FilterSet):
    """Filtre pour les exercices comptables"""

    code = CharFilter(field_name='code', lookup_expr='exact')
    libelle = CharFilter(field_name='libelle', lookup_expr='icontains')
    statut = ChoiceFilter(field_name='statut', choices=ExerciceComptable.STATUTS)
    date_debut_after = DateFilter(field_name='date_debut', lookup_expr='gte')
    date_debut_before = DateFilter(field_name='date_debut', lookup_expr='lte')
    date_fin_after = DateFilter(field_name='date_fin', lookup_expr='gte')
    date_fin_before = DateFilter(field_name='date_fin', lookup_expr='lte')
    is_premier_exercice = BooleanFilter(field_name='is_premier_exercice')
    report_a_nouveau_genere = BooleanFilter(field_name='report_a_nouveau_genere')

    class Meta:
        model = ExerciceComptable
        fields = ['code', 'libelle', 'statut', 'is_premier_exercice', 'report_a_nouveau_genere']


class ExerciceComptableViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour les exercices comptables

    Endpoints:
    - GET /api/exercices/ - Liste des exercices
    - POST /api/exercices/ - Créer un exercice
    - GET /api/exercices/{id}/ - Détail d'un exercice
    - PUT /api/exercices/{id}/ - Modifier un exercice
    - DELETE /api/exercices/{id}/ - Supprimer un exercice

    Actions supplémentaires:
    - GET /api/exercices/ouverts/ - Exercices ouverts uniquement
    - GET /api/exercices/en_cours/ - Exercice en cours (date du jour)
    - GET /api/exercices/{id}/stats/ - Statistiques détaillées
    - GET /api/exercices/{id}/periodes/ - Périodes de l'exercice
    - POST /api/exercices/{id}/ouvrir/ - Ouvrir un exercice
    - POST /api/exercices/{id}/cloturer_provisoire/ - Clôture provisoire
    - POST /api/exercices/{id}/cloturer/ - Clôture définitive
    - POST /api/exercices/{id}/generer_periodes/ - Générer les périodes
    - GET /api/exercices/{id}/balance_generale/ - Balance générale
    - GET /api/exercices/{id}/synthese/ - Synthèse de l'exercice
    """

    queryset = ExerciceComptable.objects.all()
    serializer_class = ExerciceComptableSerializer
    #permission_classes = [IsAuthenticated]
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ExerciceComptableFilter
    search_fields = ['code', 'libelle']
    ordering_fields = ['code', 'date_debut', 'date_fin', 'created_at']
    ordering = ['-date_debut']

    def get_serializer_class(self):
        """Retourne le serializer approprié selon l'action"""
        if self.action == 'list' and self.request.query_params.get('minimal'):
            return ExerciceComptableMinimalSerializer
        elif self.action in ['stats', 'balance_generale', 'synthese']:
            return ExerciceComptableStatsSerializer
        elif self.action == 'cloturer':
            return ClotureExerciceSerializer
        return super().get_serializer_class()

    def get_queryset(self):
        """Retourne le queryset avec optimisations"""
        queryset = super().get_queryset()

        # Préchargement pour optimisation
        if self.action in ['retrieve', 'list']:
            queryset = queryset.prefetch_related(
                Prefetch('periodes', queryset=PeriodeComptable.objects.order_by('numero'))
            )

        # Inclure les statistiques si demandé
        if self.request.query_params.get('with_stats'):
            queryset = queryset.annotate(
                nb_ecritures=Count('ecritures'),
                nb_ecritures_validees=Count('ecritures', filter=Q(ecritures__statut='VALIDEE')),
                nb_periodes=Count('periodes'),
                nb_periodes_cloturees=Count('periodes', filter=Q(periodes__statut='CLOTUREE'))
            )

        return queryset

    @action(detail=False, methods=['get'])
    def ouverts(self, request):
        """Retourne uniquement les exercices ouverts"""
        queryset = self.get_queryset().filter(statut='OUVERT')
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def en_cours(self, request):
        """Retourne l'exercice en cours (contenant la date du jour)"""
        today = timezone.now().date()
        queryset = self.get_queryset().filter(
            date_debut__lte=today,
            date_fin__gte=today,
            statut='OUVERT'
        )

        if queryset.exists():
            exercice = queryset.first()
            serializer = self.get_serializer(exercice)
            return Response(serializer.data)

        return Response(
            {'message': 'Aucun exercice ouvert pour la date du jour'},
            status=status.HTTP_404_NOT_FOUND
        )

    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """Retourne les statistiques détaillées de l'exercice"""
        exercice = self.get_object()
        serializer = ExerciceComptableStatsSerializer(exercice)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def periodes(self, request, pk=None):
        """Retourne les périodes de l'exercice avec leurs statistiques"""
        exercice = self.get_object()
        periodes = exercice.periodes.all().order_by('numero')

        # Ajouter des statistiques par période si demandé
        if request.query_params.get('with_stats'):
            periodes = periodes.annotate(
                nb_ecritures=Count('exercice__ecritures', filter=Q(
                    exercice__ecritures__date_ecriture__gte=F('date_debut'),
                    exercice__ecritures__date_ecriture__lte=F('date_fin')
                ))
            )

        serializer = PeriodeComptableSerializer(periodes, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def ouvrir(self, request, pk=None):
        """Ouvre un exercice en préparation"""
        exercice = self.get_object()

        try:
            exercice.ouvrir()
            serializer = self.get_serializer(exercice)
            return Response({
                'message': f"L'exercice {exercice.libelle} a été ouvert avec succès",
                'exercice': serializer.data
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def cloturer_provisoire(self, request, pk=None):
        """Effectue une clôture provisoire de l'exercice"""
        exercice = self.get_object()

        try:
            exercice.cloturer_provisoirement()
            return Response({
                'message': f"Clôture provisoire de l'exercice {exercice.libelle} effectuée",
                'date_cloture': exercice.date_cloture_provisoire
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def cloturer(self, request, pk=None):
        """Effectue la clôture définitive de l'exercice"""
        exercice = self.get_object()
        serializer = ClotureExerciceSerializer(data=request.data)

        if serializer.is_valid():
            try:
                # Clôturer l'exercice
                exercice.cloturer_definitivement()

                # Générer les à-nouveaux si demandé
                if serializer.validated_data.get('generer_a_nouveaux'):
                    # Cette partie sera implémentée avec le modèle Ecriture
                    pass

                return Response({
                    'message': f"L'exercice {exercice.libelle} a été clôturé définitivement",
                    'date_cloture': exercice.date_cloture_definitive
                })
            except Exception as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def generer_periodes(self, request, pk=None):
        """Génère ou régénère les périodes mensuelles"""
        exercice = self.get_object()

        # Vérifier qu'il n'y a pas déjà des périodes avec des écritures
        if exercice.periodes.exists():
            # Vérifier s'il y a des écritures
            has_ecritures = False
            for periode in exercice.periodes.all():
                if hasattr(periode, 'ecritures') and periode.ecritures.exists():
                    has_ecritures = True
                    break

            if has_ecritures:
                return Response(
                    {'error': 'Des écritures existent déjà dans certaines périodes'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Supprimer les périodes existantes
            exercice.periodes.all().delete()

        # Générer les nouvelles périodes
        exercice._creer_periodes_mensuelles()

        # Retourner l'exercice avec ses périodes
        serializer = self.get_serializer(exercice)
        return Response({
            'message': f"{exercice.periodes.count()} périodes générées pour l'exercice {exercice.libelle}",
            'exercice': serializer.data
        })

    @action(detail=True, methods=['get'])
    def balance_generale(self, request, pk=None):
        """Retourne la balance générale de l'exercice"""
        exercice = self.get_object()

        # Cette fonctionnalité sera complète avec le modèle LigneEcriture
        # Pour l'instant, on retourne une structure de base
        return Response({
            'exercice': {
                'id': exercice.id,
                'libelle': exercice.libelle,
                'periode': f"{exercice.date_debut} au {exercice.date_fin}"
            },
            'balance': [],
            'totaux': {
                'debit': 0,
                'credit': 0,
                'solde_debiteur': 0,
                'solde_crediteur': 0
            }
        })

    @action(detail=True, methods=['get'])
    def synthese(self, request, pk=None):
        """Retourne une synthèse complète de l'exercice"""
        exercice = self.get_object()

        # Statistiques générales
        stats = {
            'exercice': ExerciceComptableSerializer(exercice).data,
            'statistiques': {
                'nb_jours_total': (exercice.date_fin - exercice.date_debut).days + 1,
                'nb_jours_ecoules': max(0, (timezone.now().date() - exercice.date_debut).days),
                'nb_jours_restants': max(0, (exercice.date_fin - timezone.now().date()).days),
                'progression_pourcent': 0,
                'nb_periodes_total': exercice.periodes.count(),
                'nb_periodes_cloturees': exercice.periodes.filter(statut='CLOTUREE').count(),
                'peut_etre_cloture': exercice.is_cloture_possible,
                'date_limite_cloture': exercice.date_limite_cloture,
                'jours_restants_cloture': exercice.jours_restants_cloture
            },
            'ecritures': {
                'nb_total': 0,
                'nb_brouillon': 0,
                'nb_validees': 0
            },
            'mouvements': {
                'total_debit': 0,
                'total_credit': 0,
                'equilibre': True
            }
        }

        # Calculer la progression
        if stats['statistiques']['nb_jours_total'] > 0:
            stats['statistiques']['progression_pourcent'] = round(
                (stats['statistiques']['nb_jours_ecoules'] / stats['statistiques']['nb_jours_total']) * 100,
                1
            )

        return Response(stats)

    def create(self, request, *args, **kwargs):
        """Création d'un exercice avec validation"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Assigner l'utilisateur créateur
        exercice = serializer.save(created_by=request.user)

        # Si l'exercice est créé avec le statut OUVERT, générer les périodes
        if exercice.statut == 'OUVERT':
            exercice._creer_periodes_mensuelles()

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        """Mise à jour d'un exercice avec restrictions"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()

        # Restrictions selon le statut
        if instance.statut in ['CLOTURE', 'ARCHIVE']:
            return Response(
                {'error': 'Un exercice clôturé ne peut pas être modifié'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Empêcher la modification des dates si des écritures existent
        if 'date_debut' in request.data or 'date_fin' in request.data:
            if hasattr(instance, 'ecritures') and instance.ecritures.exists():
                return Response(
                    {'error': 'Les dates ne peuvent pas être modifiées car des écritures existent'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        """Suppression d'un exercice (uniquement en préparation)"""
        instance = self.get_object()

        # Vérifier le statut
        if instance.statut != 'PREPARATION':
            return Response(
                {'error': 'Seul un exercice en préparation peut être supprimé'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Vérifier qu'il n'y a pas d'écritures
        if hasattr(instance, 'ecritures') and instance.ecritures.exists():
            return Response(
                {'error': 'Cet exercice contient des écritures et ne peut pas être supprimé'},
                status=status.HTTP_400_BAD_REQUEST
            )

        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)