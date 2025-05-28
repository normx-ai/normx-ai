# apps/api/viewsets/ecriture.py
"""
ViewSet pour la gestion des écritures comptables OHADA

Fonctionnalités principales :
- Saisie d'écritures avec équilibre automatique
- Validation et clôture des écritures
- Numérotation automatique par journal
- Import/export d'écritures
- Statistiques et recherche avancée
"""

from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Sum, Count, Q, F, DecimalField
from django.db.models.functions import Coalesce
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import datetime, date, timedelta
from decimal import Decimal
import csv
import json
from io import StringIO

from apps.accounting.models import (
    EcritureComptable, LigneEcriture, Journal,
    ExerciceComptable, PeriodeComptable, CompteOHADA, Tiers
)
from apps.accounting.serializers import (
    EcritureComptableSerializer,
    EcritureComptableMinimalSerializer,
    EcritureComptableStatsSerializer,
    LigneEcritureSerializer,
    LigneEcritureCreateSerializer,
    ValidationEcritureSerializer,
    SaisieRapideSerializer
)


class EcritureComptableViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour la gestion des écritures comptables

    Endpoints :
    - GET /ecritures/ : Liste des écritures avec filtres
    - POST /ecritures/ : Créer une nouvelle écriture
    - GET /ecritures/{id}/ : Détail d'une écriture
    - PUT/PATCH /ecritures/{id}/ : Modifier une écriture brouillon
    - DELETE /ecritures/{id}/ : Supprimer une écriture brouillon

    Actions personnalisées :
    - valider/ : Valider une écriture
    - dupliquer/ : Dupliquer une écriture
    - saisie_rapide/ : Saisie simplifiée
    - stats/ : Statistiques globales
    - export_csv/ : Export CSV
    - import_csv/ : Import CSV
    """

    queryset = EcritureComptable.objects.all()
    serializer_class = EcritureComptableSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]

    # Filtres disponibles
    filterset_fields = {
        'journal': ['exact'],
        'exercice': ['exact'],
        'periode': ['exact'],
        'statut': ['exact'],
        'date_ecriture': ['exact', 'gte', 'lte'],
        'is_equilibree': ['exact'],
        'is_lettree': ['exact'],
    }

    # Recherche textuelle
    search_fields = ['numero', 'libelle', 'reference']

    # Tri
    ordering_fields = ['date_ecriture', 'numero', 'created_at', 'montant_total']
    ordering = ['-date_ecriture', '-numero']

    def get_queryset(self):
        """Optimisation des requêtes avec prefetch"""
        queryset = super().get_queryset()

        # Prefetch pour éviter les N+1
        queryset = queryset.select_related(
            'journal', 'exercice', 'periode',
            'created_by', 'validee_par'
        ).prefetch_related(
            'lignes__compte',
            'lignes__tiers'
        )

        # Annotations pour les totaux
        queryset = queryset.annotate(
            _total_debit=Coalesce(
                Sum('lignes__montant_debit'),
                Decimal('0'),
                output_field=DecimalField()
            ),
            _total_credit=Coalesce(
                Sum('lignes__montant_credit'),
                Decimal('0'),
                output_field=DecimalField()
            ),
            _nb_lignes=Count('lignes')
        )

        # Filtres additionnels depuis les query params
        params = self.request.query_params

        # Filtre par mois/année
        if params.get('annee'):
            queryset = queryset.filter(date_ecriture__year=params['annee'])

        if params.get('mois'):
            queryset = queryset.filter(date_ecriture__month=params['mois'])

        # Filtre par compte utilisé
        if params.get('compte'):
            queryset = queryset.filter(lignes__compte__code__startswith=params['compte'])

        # Filtre par tiers
        if params.get('tiers'):
            queryset = queryset.filter(lignes__tiers=params['tiers'])

        # Filtre par montant
        if params.get('montant_min'):
            queryset = queryset.filter(montant_total__gte=params['montant_min'])

        if params.get('montant_max'):
            queryset = queryset.filter(montant_total__lte=params['montant_max'])

        # Filtre par équilibre
        if params.get('desequilibrees_only') == 'true':
            queryset = queryset.exclude(is_equilibree=True)

        return queryset.distinct()

    def get_serializer_class(self):
        """Serializer selon l'action"""
        if self.action == 'list':
            return EcritureComptableMinimalSerializer
        elif self.action == 'stats':
            return EcritureComptableStatsSerializer
        elif self.action == 'saisie_rapide':
            return SaisieRapideSerializer
        elif self.action == 'valider':
            return ValidationEcritureSerializer
        return self.serializer_class

    def perform_create(self, serializer):
        """Ajout de l'utilisateur créateur"""
        serializer.save(created_by=self.request.user)

    def destroy(self, request, *args, **kwargs):
        """Suppression avec vérifications"""
        instance = self.get_object()

        # Vérifier le statut
        if instance.statut != 'BROUILLON':
            return Response(
                {'error': f"Impossible de supprimer une écriture {instance.get_statut_display()}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Vérifier s'il y a des lettrages
        if instance.lignes.filter(is_lettree=True).exists():
            return Response(
                {'error': "Impossible de supprimer une écriture avec des lignes lettrées"},
                status=status.HTTP_400_BAD_REQUEST
            )

        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def valider(self, request, pk=None):
        """
        Valider une écriture (passer de BROUILLON à VALIDEE)

        POST /api/ecritures/{id}/valider/
        """
        ecriture = self.get_object()

        try:
            ecriture.valider(user=request.user)

            return Response({
                'message': f"Écriture {ecriture.numero} validée avec succès",
                'ecriture': EcritureComptableSerializer(ecriture).data
            })

        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def dupliquer(self, request, pk=None):
        """
        Dupliquer une écriture existante

        POST /api/ecritures/{id}/dupliquer/
        Body (optionnel):
        {
            "date_ecriture": "2024-11-30",
            "libelle": "Nouveau libellé"
        }
        """
        ecriture_originale = self.get_object()

        try:
            # Dupliquer l'écriture
            nouvelle_ecriture = ecriture_originale.dupliquer()

            # Appliquer les modifications si fournies
            if request.data.get('date_ecriture'):
                nouvelle_ecriture.date_ecriture = request.data['date_ecriture']

            if request.data.get('libelle'):
                nouvelle_ecriture.libelle = request.data['libelle']

            nouvelle_ecriture.save()

            return Response({
                'message': f"Écriture dupliquée : {nouvelle_ecriture.numero}",
                'ecriture': EcritureComptableSerializer(nouvelle_ecriture).data
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response(
                {'error': f"Erreur lors de la duplication : {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['post'])
    @transaction.atomic
    def saisie_rapide(self, request):
        """
        Saisie rapide d'écritures courantes

        POST /api/ecritures/saisie_rapide/
        Body:
        {
            "type_operation": "ACHAT",
            "date_operation": "2024-11-15",
            "montant_ttc": 1180.00,
            "taux_tva": 18.00,
            "tiers": 1,
            "libelle": "Achat fournitures",
            "reference": "FACT-001"
        }
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        type_op = data['type_operation']
        montant_ttc = data['montant_ttc']
        taux_tva = data.get('taux_tva', Decimal('18.00'))

        # Calcul HT et TVA
        montant_tva = montant_ttc * taux_tva / (100 + taux_tva)
        montant_ht = montant_ttc - montant_tva

        try:
            # Déterminer les comptes selon le type d'opération
            lignes = []

            if type_op == 'ACHAT':
                # Facture fournisseur
                journal = Journal.objects.get(code='AC')

                # Débit : Charge ou immobilisation
                compte_charge = data.get('compte_charge_produit') or CompteOHADA.objects.get(code='6041')
                lignes.append({
                    'compte': compte_charge,
                    'montant_debit': montant_ht,
                    'montant_credit': 0,
                    'libelle': f"{data['libelle']} HT"
                })

                # Débit : TVA déductible
                lignes.append({
                    'compte': CompteOHADA.objects.get(code='4451'),
                    'montant_debit': montant_tva,
                    'montant_credit': 0,
                    'libelle': f"TVA {taux_tva}%"
                })

                # Crédit : Fournisseur
                lignes.append({
                    'compte': CompteOHADA.objects.get(code='401'),
                    'tiers': data['tiers'],
                    'montant_debit': 0,
                    'montant_credit': montant_ttc,
                    'libelle': data['libelle'],
                    'date_echeance': data['date_operation'] + timedelta(days=30)
                })

            elif type_op == 'VENTE':
                # Facture client
                journal = Journal.objects.get(code='VT')

                # Débit : Client
                lignes.append({
                    'compte': CompteOHADA.objects.get(code='411'),
                    'tiers': data['tiers'],
                    'montant_debit': montant_ttc,
                    'montant_credit': 0,
                    'libelle': data['libelle'],
                    'date_echeance': data['date_operation'] + timedelta(days=30)
                })

                # Crédit : Vente
                compte_vente = data.get('compte_charge_produit') or CompteOHADA.objects.get(code='701')
                lignes.append({
                    'compte': compte_vente,
                    'montant_debit': 0,
                    'montant_credit': montant_ht,
                    'libelle': f"{data['libelle']} HT"
                })

                # Crédit : TVA collectée
                lignes.append({
                    'compte': CompteOHADA.objects.get(code='4431'),
                    'montant_debit': 0,
                    'montant_credit': montant_tva,
                    'libelle': f"TVA {taux_tva}%"
                })

            elif type_op == 'ENCAISSEMENT':
                # Encaissement client
                journal = Journal.objects.get(code='BQ')

                # Débit : Banque
                lignes.append({
                    'compte': CompteOHADA.objects.get(code='521'),
                    'montant_debit': montant_ttc,
                    'montant_credit': 0,
                    'libelle': f"Encaissement {data['libelle']}"
                })

                # Crédit : Client
                lignes.append({
                    'compte': CompteOHADA.objects.get(code='411'),
                    'tiers': data['tiers'],
                    'montant_debit': 0,
                    'montant_credit': montant_ttc,
                    'libelle': data['libelle']
                })

            elif type_op == 'DECAISSEMENT':
                # Paiement fournisseur
                journal = Journal.objects.get(code='BQ')

                # Débit : Fournisseur
                lignes.append({
                    'compte': CompteOHADA.objects.get(code='401'),
                    'tiers': data['tiers'],
                    'montant_debit': montant_ttc,
                    'montant_credit': 0,
                    'libelle': data['libelle']
                })

                # Crédit : Banque
                lignes.append({
                    'compte': CompteOHADA.objects.get(code='521'),
                    'montant_debit': 0,
                    'montant_credit': montant_ttc,
                    'libelle': f"Paiement {data['libelle']}"
                })

            # Créer l'écriture
            periode = PeriodeComptable.objects.get(
                date_debut__lte=data['date_operation'],
                date_fin__gte=data['date_operation'],
                statut='OUVERTE'
            )

            ecriture = EcritureComptable.objects.create(
                journal=journal,
                periode=periode,
                exercice=periode.exercice,
                date_ecriture=data['date_operation'],
                libelle=data['libelle'],
                reference=data.get('reference', ''),
                created_by=request.user
            )

            # Créer les lignes
            for ligne_data in lignes:
                LigneEcriture.objects.create(
                    ecriture=ecriture,
                    **ligne_data
                )

            return Response({
                'message': f"Écriture {ecriture.numero} créée avec succès",
                'ecriture': EcritureComptableSerializer(ecriture).data
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response(
                {'error': f"Erreur lors de la création : {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        Statistiques globales des écritures

        GET /api/ecritures/stats/
        """
        queryset = self.filter_queryset(self.get_queryset())

        # Stats par statut
        stats_statut = queryset.values('statut').annotate(
            nombre=Count('id'),
            montant_total=Sum('montant_total')
        ).order_by('statut')

        # Stats par journal
        stats_journal = queryset.values(
            'journal__code',
            'journal__libelle'
        ).annotate(
            nombre=Count('id'),
            montant_total=Sum('montant_total')
        ).order_by('-nombre')[:10]

        # Stats par mois
        stats_mois = queryset.extra(
            select={'mois': "TO_CHAR(date_ecriture, 'YYYY-MM')"}
        ).values('mois').annotate(
            nombre=Count('id'),
            montant_total=Sum('montant_total')
        ).order_by('-mois')[:12]

        # Écritures déséquilibrées
        desequilibrees = queryset.filter(is_equilibree=False).count()

        # Top comptes utilisés
        top_comptes = LigneEcriture.objects.filter(
            ecriture__in=queryset
        ).values(
            'compte__code',
            'compte__libelle'
        ).annotate(
            nb_utilisations=Count('id'),
            total_debit=Sum('montant_debit'),
            total_credit=Sum('montant_credit')
        ).order_by('-nb_utilisations')[:20]

        return Response({
            'periode': {
                'debut': queryset.aggregate(min_date=models.Min('date_ecriture'))['min_date'],
                'fin': queryset.aggregate(max_date=models.Max('date_ecriture'))['max_date']
            },
            'totaux': {
                'nombre_ecritures': queryset.count(),
                'montant_total': queryset.aggregate(total=Sum('montant_total'))['total'] or 0,
                'ecritures_desequilibrees': desequilibrees
            },
            'par_statut': list(stats_statut),
            'par_journal': list(stats_journal),
            'par_mois': list(stats_mois),
            'top_comptes': list(top_comptes)
        })

    @action(detail=False, methods=['get'])
    def export_csv(self, request):
        """
        Export des écritures au format CSV

        GET /api/ecritures/export_csv/
        """
        queryset = self.filter_queryset(self.get_queryset())

        # Limiter à 10000 lignes
        queryset = queryset[:10000]

        # Créer le CSV
        output = StringIO()
        writer = csv.writer(output, delimiter=';')

        # En-tête
        writer.writerow([
            'Numero', 'Date', 'Journal', 'Libelle', 'Reference',
            'Compte', 'Tiers', 'Debit', 'Credit', 'Lettrage'
        ])

        # Lignes
        for ecriture in queryset:
            for ligne in ecriture.lignes.all():
                writer.writerow([
                    ecriture.numero,
                    ecriture.date_ecriture.strftime('%d/%m/%Y'),
                    ecriture.journal.code,
                    ligne.libelle,
                    ecriture.reference or '',
                    ligne.compte.code,
                    ligne.tiers.code if ligne.tiers else '',
                    str(ligne.montant_debit).replace('.', ',') if ligne.montant_debit else '',
                    str(ligne.montant_credit).replace('.', ',') if ligne.montant_credit else '',
                    ligne.code_lettrage or ''
                ])

        # Retourner le fichier
        response = Response(
            output.getvalue(),
            content_type='text/csv'
        )
        response['Content-Disposition'] = f'attachment; filename="ecritures_{date.today()}.csv"'

        return response

    @action(detail=False, methods=['post'])
    @transaction.atomic
    def import_csv(self, request):
        """
        Import d'écritures depuis un fichier CSV

        POST /api/ecritures/import_csv/
        Body: FormData avec fichier CSV
        """
        if 'file' not in request.FILES:
            return Response(
                {'error': 'Aucun fichier fourni'},
                status=status.HTTP_400_BAD_REQUEST
            )

        file = request.FILES['file']

        try:
            # Lire le CSV
            content = file.read().decode('utf-8-sig')
            reader = csv.DictReader(StringIO(content), delimiter=';')

            ecritures_creees = []
            errors = []

            # Grouper par numéro d'écriture
            ecritures_data = {}

            for row_num, row in enumerate(reader, 2):
                try:
                    numero = row.get('Numero', '').strip()
                    if not numero:
                        continue

                    if numero not in ecritures_data:
                        # Nouvelle écriture
                        journal = Journal.objects.get(code=row['Journal'])
                        date_ecriture = datetime.strptime(row['Date'], '%d/%m/%Y').date()

                        periode = PeriodeComptable.objects.get(
                            date_debut__lte=date_ecriture,
                            date_fin__gte=date_ecriture,
                            statut='OUVERTE'
                        )

                        ecritures_data[numero] = {
                            'journal': journal,
                            'periode': periode,
                            'exercice': periode.exercice,
                            'date_ecriture': date_ecriture,
                            'libelle': row.get('Libelle', ''),
                            'reference': row.get('Reference', ''),
                            'lignes': []
                        }

                    # Ajouter la ligne
                    compte = CompteOHADA.objects.get(code=row['Compte'])
                    tiers = None
                    if row.get('Tiers'):
                        tiers = Tiers.objects.get(code=row['Tiers'])

                    montant_debit = Decimal(row.get('Debit', '0').replace(',', '.'))
                    montant_credit = Decimal(row.get('Credit', '0').replace(',', '.'))

                    ecritures_data[numero]['lignes'].append({
                        'compte': compte,
                        'tiers': tiers,
                        'libelle': row.get('Libelle', ''),
                        'montant_debit': montant_debit,
                        'montant_credit': montant_credit,
                        'code_lettrage': row.get('Lettrage', '')
                    })

                except Exception as e:
                    errors.append(f"Ligne {row_num}: {str(e)}")

            # Créer les écritures
            for numero, data in ecritures_data.items():
                try:
                    # Vérifier l'équilibre
                    total_debit = sum(l['montant_debit'] for l in data['lignes'])
                    total_credit = sum(l['montant_credit'] for l in data['lignes'])

                    if abs(total_debit - total_credit) >= 0.01:
                        errors.append(
                            f"Écriture {numero} déséquilibrée: "
                            f"D={total_debit} C={total_credit}"
                        )
                        continue

                    # Créer l'écriture
                    ecriture = EcritureComptable.objects.create(
                        journal=data['journal'],
                        periode=data['periode'],
                        exercice=data['exercice'],
                        date_ecriture=data['date_ecriture'],
                        libelle=data['libelle'],
                        reference=data['reference'],
                        created_by=request.user
                    )

                    # Créer les lignes
                    for ligne_data in data['lignes']:
                        LigneEcriture.objects.create(
                            ecriture=ecriture,
                            **ligne_data
                        )

                    ecritures_creees.append(ecriture.numero)

                except Exception as e:
                    errors.append(f"Écriture {numero}: {str(e)}")

            return Response({
                'message': f"{len(ecritures_creees)} écritures importées",
                'ecritures_creees': ecritures_creees,
                'errors': errors[:50]  # Limiter à 50 erreurs
            })

        except Exception as e:
            return Response(
                {'error': f"Erreur lors de l'import : {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['get'])
    def lignes(self, request, pk=None):
        """
        Récupérer les lignes d'une écriture

        GET /api/ecritures/{id}/lignes/
        """
        ecriture = self.get_object()
        lignes = ecriture.lignes.all().order_by('numero_ligne')

        serializer = LigneEcritureSerializer(lignes, many=True)

        return Response({
            'ecriture': {
                'numero': ecriture.numero,
                'libelle': ecriture.libelle,
                'statut': ecriture.statut
            },
            'lignes': serializer.data,
            'totaux': {
                'debit': ecriture.total_debit,
                'credit': ecriture.total_credit,
                'equilibree': ecriture.is_equilibree
            }
        })

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def ajouter_ligne(self, request, pk=None):
        """
        Ajouter une ligne à une écriture existante

        POST /api/ecritures/{id}/ajouter_ligne/
        """
        ecriture = self.get_object()

        # Vérifier que l'écriture est modifiable
        if ecriture.statut != 'BROUILLON':
            return Response(
                {'error': "Seules les écritures en brouillon peuvent être modifiées"},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = LigneEcritureCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            ligne = LigneEcriture.objects.create(
                ecriture=ecriture,
                **serializer.validated_data
            )

            return Response({
                'message': "Ligne ajoutée avec succès",
                'ligne': LigneEcritureSerializer(ligne).data,
                'equilibre': {
                    'total_debit': ecriture.total_debit,
                    'total_credit': ecriture.total_credit,
                    'equilibree': ecriture.is_equilibree
                }
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['get'])
    def modeles(self, request):
        """
        Récupérer les modèles d'écritures fréquentes

        GET /api/ecritures/modeles/
        """
        modeles = [
            {
                'code': 'FACT_ACHAT',
                'libelle': 'Facture d\'achat',
                'journal': 'AC',
                'lignes': [
                    {'compte': '60xx', 'sens': 'D', 'info': 'Compte de charge HT'},
                    {'compte': '4451', 'sens': 'D', 'info': 'TVA déductible'},
                    {'compte': '401', 'sens': 'C', 'info': 'Fournisseur TTC'}
                ]
            },
            {
                'code': 'FACT_VENTE',
                'libelle': 'Facture de vente',
                'journal': 'VT',
                'lignes': [
                    {'compte': '411', 'sens': 'D', 'info': 'Client TTC'},
                    {'compte': '70xx', 'sens': 'C', 'info': 'Compte de produit HT'},
                    {'compte': '4431', 'sens': 'C', 'info': 'TVA collectée'}
                ]
            },
            {
                'code': 'ENCAISSEMENT',
                'libelle': 'Encaissement client',
                'journal': 'BQ',
                'lignes': [
                    {'compte': '521', 'sens': 'D', 'info': 'Banque'},
                    {'compte': '411', 'sens': 'C', 'info': 'Client'}
                ]
            },
            {
                'code': 'PAIEMENT',
                'libelle': 'Paiement fournisseur',
                'journal': 'BQ',
                'lignes': [
                    {'compte': '401', 'sens': 'D', 'info': 'Fournisseur'},
                    {'compte': '521', 'sens': 'C', 'info': 'Banque'}
                ]
            },
            {
                'code': 'SALAIRE',
                'libelle': 'Paiement salaire',
                'journal': 'OD',
                'lignes': [
                    {'compte': '661', 'sens': 'D', 'info': 'Salaire brut'},
                    {'compte': '431', 'sens': 'C', 'info': 'Sécurité sociale'},
                    {'compte': '447', 'sens': 'C', 'info': 'Impôts retenus'},
                    {'compte': '421', 'sens': 'C', 'info': 'Personnel - Net à payer'}
                ]
            },
            {
                'code': 'AMORTISSEMENT',
                'libelle': 'Dotation aux amortissements',
                'journal': 'OD',
                'lignes': [
                    {'compte': '681', 'sens': 'D', 'info': 'Dotation aux amortissements'},
                    {'compte': '28xx', 'sens': 'C', 'info': 'Amortissement immo'}
                ]
            }
        ]

        return Response(modeles)

    @action(detail=False, methods=['get'])
    def verifier_equilibre(self, request):
        """
        Vérifier l'équilibre d'une écriture avant validation

        GET /api/ecritures/verifier_equilibre/
        Body: {"lignes": [...]}
        """
        lignes = request.data.get('lignes', [])

        if not lignes:
            return Response(
                {'error': 'Aucune ligne fournie'},
                status=status.HTTP_400_BAD_REQUEST
            )

        total_debit = sum(Decimal(str(l.get('montant_debit', 0))) for l in lignes)
        total_credit = sum(Decimal(str(l.get('montant_credit', 0))) for l in lignes)
        ecart = abs(total_debit - total_credit)

        return Response({
            'total_debit': total_debit,
            'total_credit': total_credit,
            'ecart': ecart,
            'equilibree': ecart < 0.01,
            'message': 'Écriture équilibrée' if ecart < 0.01 else f'Écart de {ecart}'
        })