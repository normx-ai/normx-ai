# apps/api/viewsets/tiers.py
"""
ViewSet pour la gestion des tiers (clients, fournisseurs, employés) via API REST
"""

from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django_filters import FilterSet, CharFilter, BooleanFilter, ChoiceFilter
from django.db.models import Q, Sum, Count, F, DecimalField
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404

from apps.accounting.models import Tiers, LigneEcriture
from apps.accounting.serializers.tiers import (
    TiersSerializer,
    TiersMinimalSerializer,
    TiersCreationSerializer,
    TiersStatsSerializer,
    BlocageDeblocageSerializer
)


class TiersFilter(FilterSet):
    """Filtre pour les tiers"""

    code = CharFilter(field_name='code', lookup_expr='icontains')
    raison_sociale = CharFilter(field_name='raison_sociale', lookup_expr='icontains')
    type_tiers = ChoiceFilter(field_name='type_tiers', choices=Tiers.TYPES_TIERS)
    is_active = BooleanFilter(field_name='is_active')
    is_bloque = BooleanFilter(field_name='is_bloque')
    ville = CharFilter(field_name='ville', lookup_expr='icontains')

    # Filtres spéciaux
    categorie = CharFilter(method='filter_categorie')
    a_solde = BooleanFilter(method='filter_a_solde')

    def filter_categorie(self, queryset, name, value):
        """Filtre par catégorie (fournisseur, client, employe)"""
        if value == 'fournisseur':
            return queryset.filter(type_tiers__in=['FLOC', 'FGRP'])
        elif value == 'client':
            return queryset.filter(type_tiers__in=['CLOC', 'CGRP'])
        elif value == 'employe':
            return queryset.filter(type_tiers='EMPL')
        return queryset

    def filter_a_solde(self, queryset, name, value):
        """Filtre les tiers ayant un solde non nul"""
        # À implémenter quand les écritures seront disponibles
        return queryset

    class Meta:
        model = Tiers
        fields = ['code', 'raison_sociale', 'type_tiers', 'is_active',
                  'is_bloque', 'ville', 'categorie', 'a_solde']


class TiersViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour les tiers (clients, fournisseurs, employés)

    Endpoints:
    - GET /api/tiers/ - Liste des tiers
    - POST /api/tiers/ - Créer un tiers
    - GET /api/tiers/{id}/ - Détail d'un tiers
    - PUT /api/tiers/{id}/ - Modifier un tiers
    - DELETE /api/tiers/{id}/ - Supprimer un tiers

    Actions supplémentaires:
    - GET /api/tiers/actifs/ - Tiers actifs uniquement
    - GET /api/tiers/par_type/ - Tiers groupés par type
    - GET /api/tiers/clients/ - Liste des clients
    - GET /api/tiers/fournisseurs/ - Liste des fournisseurs
    - GET /api/tiers/employes/ - Liste des employés
    - GET /api/tiers/{id}/stats/ - Statistiques d'un tiers
    - GET /api/tiers/{id}/ecritures/ - Écritures d'un tiers
    - GET /api/tiers/{id}/balance/ - Balance d'un tiers
    - POST /api/tiers/{id}/bloquer/ - Bloquer un tiers
    - POST /api/tiers/{id}/debloquer/ - Débloquer un tiers
    - GET /api/tiers/recherche_rapide/ - Recherche rapide pour autocomplete
    """

    queryset = Tiers.objects.all()
    serializer_class = TiersSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = TiersFilter
    search_fields = ['code', 'raison_sociale', 'sigle', 'numero_contribuable', 'matricule']
    ordering_fields = ['code', 'raison_sociale', 'type_tiers', 'created_at']
    ordering = ['type_tiers', 'code']

    def get_serializer_class(self):
        """Retourne le serializer approprié selon l'action"""
        if self.action == 'create':
            return TiersCreationSerializer
        elif self.action == 'list' and self.request.query_params.get('minimal'):
            return TiersMinimalSerializer
        elif self.action in ['stats', 'balance']:
            return TiersStatsSerializer
        elif self.action in ['bloquer', 'debloquer']:
            return BlocageDeblocageSerializer
        return super().get_serializer_class()

    def get_queryset(self):
        """
        Retourne le queryset filtré
        Inclut les statistiques si demandé
        """
        queryset = super().get_queryset()

        # Préchargement pour optimisation
        queryset = queryset.select_related('compte_collectif', 'created_by')

        # Annoter avec le solde si demandé
        if self.request.query_params.get('with_solde'):
            # Calculer le solde à partir des lignes d'écriture
            queryset = queryset.annotate(
                total_debit=Coalesce(
                    Sum('lignes_ecritures__montant_debit'),
                    0,
                    output_field=DecimalField()
                ),
                total_credit=Coalesce(
                    Sum('lignes_ecritures__montant_credit'),
                    0,
                    output_field=DecimalField()
                ),
                solde_debiteur=F('total_debit') - F('total_credit')
            )

        # Annoter avec le nombre d'écritures si demandé
        if self.request.query_params.get('with_stats'):
            queryset = queryset.annotate(
                nb_ecritures=Count('lignes_ecritures__ecriture', distinct=True),
                nb_factures_impayees=Count(
                    'lignes_ecritures__ecriture',
                    filter=Q(lignes_ecritures__is_lettree=False),
                    distinct=True
                )
            )

        return queryset

    @action(detail=False, methods=['get'])
    def actifs(self, request):
        """Retourne uniquement les tiers actifs et non bloqués"""
        queryset = self.get_queryset().filter(is_active=True, is_bloque=False)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def par_type(self, request):
        """Retourne les tiers groupés par type"""
        tiers_par_type = {}

        for type_code, type_libelle in Tiers.TYPES_TIERS:
            tiers = self.get_queryset().filter(type_tiers=type_code)

            if tiers.exists():
                tiers_par_type[type_code] = {
                    'code': type_code,
                    'libelle': type_libelle,
                    'nb_tiers': tiers.count(),
                    'nb_actifs': tiers.filter(is_active=True).count(),
                    'nb_bloques': tiers.filter(is_bloque=True).count(),
                    'tiers': TiersMinimalSerializer(tiers[:10], many=True).data
                }

        return Response(tiers_par_type)

    @action(detail=False, methods=['get'])
    def clients(self, request):
        """Retourne la liste des clients"""
        queryset = self.get_queryset().filter(type_tiers__in=['CLOC', 'CGRP'])
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def fournisseurs(self, request):
        """Retourne la liste des fournisseurs"""
        queryset = self.get_queryset().filter(type_tiers__in=['FLOC', 'FGRP'])
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def employes(self, request):
        """Retourne la liste des employés"""
        queryset = self.get_queryset().filter(type_tiers='EMPL')
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """Retourne les statistiques d'un tiers"""
        tiers = self.get_object()

        # Calculer les statistiques
        from django.db.models import Value, DecimalField
        stats = LigneEcriture.objects.filter(tiers=tiers).aggregate(
            nb_ecritures=Count('ecriture', distinct=True),
            total_debit=Coalesce(Sum('montant_debit'), Value(0, output_field=DecimalField())),
            total_credit=Coalesce(Sum('montant_credit'), Value(0, output_field=DecimalField())),
            nb_lignes=Count('id')
        )

        # Calculer le solde
        solde = float(stats['total_debit'] or 0) - float(stats['total_credit'] or 0)

        # Dernières écritures
        dernieres_ecritures = LigneEcriture.objects.filter(
            tiers=tiers
        ).select_related('ecriture', 'compte').order_by('-ecriture__date_ecriture')[:5]

        ecritures_data = []
        for ligne in dernieres_ecritures:
            ecritures_data.append({
                'date': ligne.ecriture.date_ecriture,
                'numero': ligne.ecriture.numero,
                'libelle': ligne.libelle or ligne.ecriture.libelle,
                'debit': float(ligne.montant_debit or 0),
                'credit': float(ligne.montant_credit or 0),
                'compte': ligne.compte.code
            })

        response_data = {
            'tiers': {
                'id': tiers.id,
                'code': tiers.code,
                'raison_sociale': tiers.raison_sociale,
                'type': tiers.get_type_tiers_display(),
                'is_bloque': tiers.is_bloque
            },
            'statistiques': {
                'nb_ecritures': stats['nb_ecritures'],
                'nb_lignes': stats['nb_lignes'],
                'total_debit': float(stats['total_debit'] or 0),
                'total_credit': float(stats['total_credit'] or 0),
                'solde': solde,
                'sens_solde': 'Débiteur' if solde > 0 else 'Créditeur' if solde < 0 else 'Nul'
            },
            'dernieres_ecritures': ecritures_data
        }

        return Response(response_data)

    @action(detail=True, methods=['get'])
    def ecritures(self, request, pk=None):
        """
        Retourne les écritures d'un tiers
        Avec pagination et filtres par date/compte
        """
        tiers = self.get_object()

        # Récupérer les lignes d'écriture
        lignes = LigneEcriture.objects.filter(tiers=tiers).select_related(
            'ecriture', 'compte', 'ecriture__journal'
        ).order_by('-ecriture__date_ecriture', '-ecriture__numero')

        # Filtres
        date_debut = request.query_params.get('date_debut')
        date_fin = request.query_params.get('date_fin')
        compte_id = request.query_params.get('compte')
        lettrees_only = request.query_params.get('lettrees_only')

        if date_debut:
            lignes = lignes.filter(ecriture__date_ecriture__gte=date_debut)
        if date_fin:
            lignes = lignes.filter(ecriture__date_ecriture__lte=date_fin)
        if compte_id:
            lignes = lignes.filter(compte_id=compte_id)
        if lettrees_only:
            lignes = lignes.filter(is_lettree=True)

        # Pagination manuelle
        page_size = int(request.query_params.get('page_size', 20))
        page = int(request.query_params.get('page', 1))
        start = (page - 1) * page_size
        end = start + page_size

        # Calculer les totaux
        totaux = lignes.aggregate(
            nb_lignes=Count('id'),
            total_debit=Coalesce(Sum('montant_debit'), 0),
            total_credit=Coalesce(Sum('montant_credit'), 0)
        )

        # Préparer la réponse
        lignes_data = []
        for ligne in lignes[start:end]:
            lignes_data.append({
                'id': ligne.id,
                'date': ligne.ecriture.date_ecriture,
                'journal': ligne.ecriture.journal.code,
                'numero_ecriture': ligne.ecriture.numero,
                'compte': ligne.compte.code,
                'libelle': ligne.libelle or ligne.ecriture.libelle,
                'debit': float(ligne.montant_debit or 0),
                'credit': float(ligne.montant_credit or 0),
                'lettre': ligne.lettre_lettrage,
                'is_lettree': ligne.is_lettree
            })

        response_data = {
            'tiers': {
                'code': tiers.code,
                'raison_sociale': tiers.raison_sociale
            },
            'periode': {
                'date_debut': date_debut,
                'date_fin': date_fin
            },
            'totaux': {
                'nb_lignes': totaux['nb_lignes'],
                'total_debit': float(totaux['total_debit']),
                'total_credit': float(totaux['total_credit']),
                'solde': float(totaux['total_debit']) - float(totaux['total_credit'])
            },
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total': lignes.count()
            },
            'lignes': lignes_data
        }

        return Response(response_data)

    @action(detail=True, methods=['get'])
    def balance(self, request, pk=None):
        """Retourne la balance âgée d'un tiers"""
        tiers = self.get_object()

        # Logique de balance âgée à implémenter
        # Pour l'instant, on retourne un résumé simple
        balance = LigneEcriture.objects.filter(
            tiers=tiers,
            is_lettree=False
        ).aggregate(
            total_debit=Coalesce(Sum('montant_debit'), 0),
            total_credit=Coalesce(Sum('montant_credit'), 0),
            nb_factures=Count('ecriture', distinct=True)
        )

        solde = float(balance['total_debit']) - float(balance['total_credit'])

        return Response({
            'tiers': {
                'code': tiers.code,
                'raison_sociale': tiers.raison_sociale,
                'delai_paiement': tiers.delai_paiement
            },
            'balance': {
                'solde_total': solde,
                'nb_factures_impayees': balance['nb_factures'],
                'montant_echu': solde,  # À calculer selon les dates d'échéance
                'montant_a_echoir': 0,  # À calculer
                'repartition_age': {
                    '0_30_jours': 0,
                    '31_60_jours': 0,
                    '61_90_jours': 0,
                    'plus_90_jours': 0
                }
            }
        })

    @action(detail=True, methods=['post'])
    def bloquer(self, request, pk=None):
        """Bloque un tiers avec un motif"""
        tiers = self.get_object()
        serializer = BlocageDeblocageSerializer(data=request.data)

        if serializer.is_valid():
            motif = serializer.validated_data['motif']
            tiers.bloquer(motif)
            return Response({
                'message': f'Le tiers {tiers.code} a été bloqué',
                'motif': motif
            })

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def debloquer(self, request, pk=None):
        """Débloque un tiers"""
        tiers = self.get_object()
        tiers.debloquer()

        return Response({
            'message': f'Le tiers {tiers.code} a été débloqué'
        })

    @action(detail=False, methods=['get'])
    def recherche_rapide(self, request):
        """
        Recherche rapide pour autocomplete
        Retourne code, raison_sociale et type
        """
        query = request.query_params.get('q', '')
        if len(query) < 2:
            return Response([])

        tiers = self.get_queryset().filter(
            Q(code__icontains=query) |
            Q(raison_sociale__icontains=query) |
            Q(sigle__icontains=query)
        ).filter(is_active=True, is_bloque=False)[:10]

        results = []
        for t in tiers:
            results.append({
                'id': t.id,
                'code': t.code,
                'raison_sociale': t.raison_sociale,
                'type': t.get_type_tiers_display(),
                'label': f"{t.code} - {t.raison_sociale}"
            })

        return Response(results)

    def create(self, request, *args, **kwargs):
        """Création d'un tiers avec codification automatique"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Le code sera généré automatiquement par le modèle
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)

        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
            headers=headers
        )

    def perform_create(self, serializer):
        """Assigner automatiquement l'utilisateur créateur"""
        serializer.save(created_by=self.request.user)

    def update(self, request, *args, **kwargs):
        """Mise à jour d'un tiers avec restrictions"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()

        # Empêcher la modification du code et du type
        if 'code' in request.data and request.data['code'] != instance.code:
            return Response(
                {'error': 'Le code d\'un tiers ne peut pas être modifié'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if 'type_tiers' in request.data and request.data['type_tiers'] != instance.type_tiers:
            return Response(
                {'error': 'Le type d\'un tiers ne peut pas être modifié'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(serializer.data)

    def perform_update(self, serializer):
        """Mise à jour standard"""
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        """Suppression d'un tiers (désactivation seulement)"""
        instance = self.get_object()

        # Vérifier si le tiers est utilisé
        if LigneEcriture.objects.filter(tiers=instance).exists():
            return Response(
                {'error': 'Ce tiers ne peut pas être supprimé car il est utilisé dans des écritures'},
                status=status.HTTP_400_BAD_REQUEST
            )

        instance.is_active = False
        instance.save()

        return Response(
            {'message': f'Le tiers {instance.code} a été désactivé'},
            status=status.HTTP_204_NO_CONTENT
        )