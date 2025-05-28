# apps/api/viewsets/ligne_ecriture.py
"""
ViewSet pour la gestion des lignes d'écriture comptable

Fonctionnalités principales :
- Gestion des lignes débit/crédit
- Lettrage et rapprochement
- Analyse par compte et tiers
- Grand livre et balance
"""

from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Sum, Count, Q, F, Case, When, DecimalField
from django.db.models.functions import Coalesce
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import datetime, date
from decimal import Decimal
import csv
from io import StringIO

from apps.accounting.models import (
    LigneEcriture, EcritureComptable,
    CompteOHADA, Tiers, Journal,
    ExerciceComptable, PeriodeComptable
)
from apps.accounting.serializers import (
    LigneEcritureSerializer,
    LigneEcritureCreateSerializer,
    CompteOHADAMinimalSerializer,
    TiersMinimalSerializer
)


class LigneEcritureViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour la gestion des lignes d'écriture

    Endpoints :
    - GET /lignes-ecritures/ : Liste avec filtres avancés
    - GET /lignes-ecritures/{id}/ : Détail d'une ligne
    - PUT/PATCH /lignes-ecritures/{id}/ : Modifier une ligne
    - DELETE /lignes-ecritures/{id}/ : Supprimer une ligne

    Actions personnalisées :
    - lettrer/ : Lettrer des lignes
    - delettrer/ : Délettrer des lignes
    - grand_livre/ : Extrait de grand livre
    - balance/ : Balance des comptes
    - compte_tiers/ : Relevé de compte tiers
    - echeancier/ : Échéancier des tiers
    """

    queryset = LigneEcriture.objects.all()
    serializer_class = LigneEcritureSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]

    # Filtres disponibles
    filterset_fields = {
        'compte': ['exact', 'in'],
        'tiers': ['exact', 'in'],
        'ecriture__journal': ['exact'],
        'ecriture__exercice': ['exact'],
        'ecriture__periode': ['exact'],
        'ecriture__statut': ['exact'],
        'ecriture__date_ecriture': ['exact', 'gte', 'lte'],
        'is_lettree': ['exact'],
        'code_lettrage': ['exact'],
    }

    # Recherche
    search_fields = ['libelle', 'piece', 'ecriture__numero', 'ecriture__reference']

    # Tri
    ordering_fields = [
        'ecriture__date_ecriture',
        'numero_ligne',
        'montant_debit',
        'montant_credit'
    ]
    ordering = ['ecriture__date_ecriture', 'numero_ligne']

    def get_queryset(self):
        """Optimisation et filtres avancés"""
        queryset = super().get_queryset()

        # Optimisations
        queryset = queryset.select_related(
            'ecriture',
            'ecriture__journal',
            'ecriture__exercice',
            'ecriture__periode',
            'compte',
            'tiers'
        )

        # Filtres additionnels
        params = self.request.query_params

        # Filtre par classe de compte
        if params.get('classe_compte'):
            queryset = queryset.filter(compte__classe=params['classe_compte'])

        # Filtre par code compte (début)
        if params.get('compte_debut'):
            queryset = queryset.filter(compte__code__startswith=params['compte_debut'])

        # Filtre par type de tiers
        if params.get('type_tiers'):
            queryset = queryset.filter(tiers__type_tiers=params['type_tiers'])

        # Filtre par sens (débit/crédit)
        if params.get('sens') == 'D':
            queryset = queryset.filter(montant_debit__gt=0)
        elif params.get('sens') == 'C':
            queryset = queryset.filter(montant_credit__gt=0)

        # Filtre par montant
        if params.get('montant_min'):
            queryset = queryset.filter(
                Q(montant_debit__gte=params['montant_min']) |
                Q(montant_credit__gte=params['montant_min'])
            )

        # Filtre par échéance
        if params.get('echeance_depassee') == 'true':
            queryset = queryset.filter(
                date_echeance__lt=date.today(),
                is_lettree=False
            )

        # Exclure les écritures en brouillon si demandé
        if params.get('validees_only') == 'true':
            queryset = queryset.exclude(ecriture__statut='BROUILLON')

        return queryset

    def update(self, request, *args, **kwargs):
        """Mise à jour avec vérifications"""
        instance = self.get_object()

        # Vérifier que l'écriture est modifiable
        if instance.ecriture.statut != 'BROUILLON':
            return Response(
                {'error': "Impossible de modifier une ligne d'écriture validée"},
                status=status.HTTP_400_BAD_REQUEST
            )

        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """Suppression avec vérifications"""
        instance = self.get_object()

        # Vérifications
        if instance.ecriture.statut != 'BROUILLON':
            return Response(
                {'error': "Impossible de supprimer une ligne d'écriture validée"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if instance.is_lettree:
            return Response(
                {'error': "Impossible de supprimer une ligne lettrée"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Vérifier qu'il restera au moins 2 lignes
        if instance.ecriture.lignes.count() <= 2:
            return Response(
                {'error': "Une écriture doit conserver au moins 2 lignes"},
                status=status.HTTP_400_BAD_REQUEST
            )

        return super().destroy(request, *args, **kwargs)

    @action(detail=False, methods=['post'])
    @transaction.atomic
    def lettrer(self, request):
        """
        Lettrer plusieurs lignes ensemble

        POST /api/lignes-ecritures/lettrer/
        Body: {
            "ligne_ids": [1, 2, 3],
            "code_lettrage": "ABC123"  // Optionnel
        }
        """
        ligne_ids = request.data.get('ligne_ids', [])

        if len(ligne_ids) < 2:
            return Response(
                {'error': "Au moins 2 lignes sont nécessaires pour le lettrage"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            lignes = LigneEcriture.objects.filter(
                id__in=ligne_ids,
                ecriture__statut='VALIDEE'
            )

            if lignes.count() != len(ligne_ids):
                return Response(
                    {'error': "Certaines lignes sont introuvables ou non validées"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Vérifier que les lignes ne sont pas déjà lettrées
            if lignes.filter(is_lettree=True).exists():
                return Response(
                    {'error': "Certaines lignes sont déjà lettrées"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Vérifier le même compte
            comptes = lignes.values_list('compte', flat=True).distinct()
            if comptes.count() > 1:
                return Response(
                    {'error': "Toutes les lignes doivent avoir le même compte"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Vérifier l'équilibre du lettrage
            total_debit = lignes.aggregate(total=Sum('montant_debit'))['total'] or Decimal('0')
            total_credit = lignes.aggregate(total=Sum('montant_credit'))['total'] or Decimal('0')

            if abs(total_debit - total_credit) >= 0.01:
                return Response({
                    'error': f"Le lettrage n'est pas équilibré. "
                             f"Débit: {total_debit}, Crédit: {total_credit}"
                }, status=status.HTTP_400_BAD_REQUEST)

            # Générer le code de lettrage
            code_lettrage = request.data.get('code_lettrage')
            if not code_lettrage:
                from django.utils.crypto import get_random_string
                code_lettrage = get_random_string(6, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ')

            # Appliquer le lettrage
            lignes.update(
                code_lettrage=code_lettrage,
                is_lettree=True
            )

            return Response({
                'message': f"{lignes.count()} lignes lettrées avec le code {code_lettrage}",
                'code_lettrage': code_lettrage,
                'lignes': ligne_ids
            })

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['post'])
    @transaction.atomic
    def delettrer(self, request):
        """
        Délettrer des lignes

        POST /api/lignes-ecritures/delettrer/
        Body: {
            "code_lettrage": "ABC123"
        }
        """
        code_lettrage = request.data.get('code_lettrage')

        if not code_lettrage:
            return Response(
                {'error': "Le code de lettrage est obligatoire"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            lignes = LigneEcriture.objects.filter(
                code_lettrage=code_lettrage,
                is_lettree=True
            )

            if not lignes.exists():
                return Response(
                    {'error': f"Aucune ligne trouvée avec le code {code_lettrage}"},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Délettrer
            nb_lignes = lignes.count()
            lignes.update(
                code_lettrage='',
                is_lettree=False
            )

            return Response({
                'message': f"{nb_lignes} lignes délettrées",
                'code_lettrage': code_lettrage
            })

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['get'])
    def grand_livre(self, request):
        """
        Extrait du grand livre

        GET /api/lignes-ecritures/grand_livre/
        Params:
            - compte_debut: Code compte début
            - compte_fin: Code compte fin
            - date_debut: Date début
            - date_fin: Date fin
            - avec_solde_nul: Inclure comptes soldés (true/false)
        """
        # Récupérer les paramètres
        compte_debut = request.query_params.get('compte_debut', '1')
        compte_fin = request.query_params.get('compte_fin', '9')
        date_debut = request.query_params.get('date_debut')
        date_fin = request.query_params.get('date_fin')
        avec_solde_nul = request.query_params.get('avec_solde_nul', 'false') == 'true'

        # Construire la requête
        queryset = self.filter_queryset(self.get_queryset())

        # Filtrer par compte
        queryset = queryset.filter(
            compte__code__gte=compte_debut,
            compte__code__lte=compte_fin
        )

        # Filtrer par date
        if date_debut:
            queryset = queryset.filter(ecriture__date_ecriture__gte=date_debut)
        if date_fin:
            queryset = queryset.filter(ecriture__date_ecriture__lte=date_fin)

        # Exclure les brouillons
        queryset = queryset.exclude(ecriture__statut='BROUILLON')

        # Grouper par compte
        comptes_data = []

        comptes = CompteOHADA.objects.filter(
            code__gte=compte_debut,
            code__lte=compte_fin
        ).order_by('code')

        for compte in comptes:
            lignes_compte = queryset.filter(compte=compte)

            if not lignes_compte.exists() and not avec_solde_nul:
                continue

            # Calculer les totaux
            totaux = lignes_compte.aggregate(
                total_debit=Coalesce(Sum('montant_debit'), Decimal('0')),
                total_credit=Coalesce(Sum('montant_credit'), Decimal('0'))
            )

            solde = totaux['total_debit'] - totaux['total_credit']

            # Skip si solde nul et non demandé
            if abs(solde) < 0.01 and not avec_solde_nul:
                continue

            # Détail des lignes
            lignes_detail = []
            cumul_debit = Decimal('0')
            cumul_credit = Decimal('0')

            for ligne in lignes_compte.order_by('ecriture__date_ecriture', 'numero_ligne'):
                cumul_debit += ligne.montant_debit
                cumul_credit += ligne.montant_credit

                lignes_detail.append({
                    'date': ligne.ecriture.date_ecriture,
                    'numero': ligne.ecriture.numero,
                    'journal': ligne.ecriture.journal.code,
                    'libelle': ligne.libelle,
                    'piece': ligne.piece,
                    'tiers': ligne.tiers.code if ligne.tiers else '',
                    'debit': ligne.montant_debit,
                    'credit': ligne.montant_credit,
                    'solde_cumule': cumul_debit - cumul_credit,
                    'lettrage': ligne.code_lettrage
                })

            comptes_data.append({
                'compte': {
                    'code': compte.code,
                    'libelle': compte.libelle
                },
                'totaux': {
                    'debit': totaux['total_debit'],
                    'credit': totaux['total_credit'],
                    'solde': solde,
                    'solde_debiteur': solde if solde > 0 else 0,
                    'solde_crediteur': -solde if solde < 0 else 0
                },
                'nb_lignes': len(lignes_detail),
                'lignes': lignes_detail if request.query_params.get('avec_detail') == 'true' else []
            })

        # Totaux généraux
        totaux_generaux = queryset.aggregate(
            total_debit=Coalesce(Sum('montant_debit'), Decimal('0')),
            total_credit=Coalesce(Sum('montant_credit'), Decimal('0'))
        )

        return Response({
            'periode': {
                'debut': date_debut or 'Début',
                'fin': date_fin or 'Fin'
            },
            'plage_comptes': {
                'debut': compte_debut,
                'fin': compte_fin
            },
            'nombre_comptes': len(comptes_data),
            'comptes': comptes_data,
            'totaux_generaux': {
                'debit': totaux_generaux['total_debit'],
                'credit': totaux_generaux['total_credit'],
                'equilibre': abs(totaux_generaux['total_debit'] - totaux_generaux['total_credit']) < 0.01
            }
        })

    @action(detail=False, methods=['get'])
    def balance(self, request):
        """
        Balance générale des comptes

        GET /api/lignes-ecritures/balance/
        Params:
            - niveau: Niveau de regroupement (1-6)
            - date_debut, date_fin
            - type_solde: tous, debiteur, crediteur
        """
        niveau = int(request.query_params.get('niveau', '3'))
        date_debut = request.query_params.get('date_debut')
        date_fin = request.query_params.get('date_fin')
        type_solde = request.query_params.get('type_solde', 'tous')

        # Base query
        queryset = self.filter_queryset(self.get_queryset())
        queryset = queryset.exclude(ecriture__statut='BROUILLON')

        # Filtres dates
        if date_debut:
            queryset = queryset.filter(ecriture__date_ecriture__gte=date_debut)
        if date_fin:
            queryset = queryset.filter(ecriture__date_ecriture__lte=date_fin)

        # Regroupement selon le niveau
        if niveau == 1:
            # Par classe
            queryset = queryset.annotate(
                groupe=F('compte__classe')
            )
        else:
            # Par sous-compte
            queryset = queryset.annotate(
                groupe=Case(
                    When(compte__code__regex=r'^\d{' + str(niveau) + '}',
                         then=F('compte__code')[:niveau]),
                    default=F('compte__code')
                )
            )

        # Agrégation
        balance_data = queryset.values('groupe').annotate(
            total_debit=Coalesce(Sum('montant_debit'), Decimal('0')),
            total_credit=Coalesce(Sum('montant_credit'), Decimal('0')),
            nb_ecritures=Count('id', distinct=True)
        ).order_by('groupe')

        # Calculer les soldes et filtrer
        balance_finale = []
        totaux = {
            'debit': Decimal('0'),
            'credit': Decimal('0'),
            'solde_debiteur': Decimal('0'),
            'solde_crediteur': Decimal('0')
        }

        for ligne in balance_data:
            solde = ligne['total_debit'] - ligne['total_credit']

            # Filtrer par type de solde
            if type_solde == 'debiteur' and solde <= 0:
                continue
            elif type_solde == 'crediteur' and solde >= 0:
                continue

            # Trouver le libellé
            if niveau == 1:
                libelle = f"Classe {ligne['groupe']}"
            else:
                try:
                    compte = CompteOHADA.objects.filter(
                        code__startswith=ligne['groupe']
                    ).first()
                    libelle = compte.libelle if compte else f"Compte {ligne['groupe']}"
                except:
                    libelle = f"Compte {ligne['groupe']}"

            balance_finale.append({
                'code': ligne['groupe'],
                'libelle': libelle,
                'debit': ligne['total_debit'],
                'credit': ligne['total_credit'],
                'solde': abs(solde),
                'solde_debiteur': solde if solde > 0 else 0,
                'solde_crediteur': -solde if solde < 0 else 0,
                'nb_ecritures': ligne['nb_ecritures']
            })

            # Mise à jour des totaux
            totaux['debit'] += ligne['total_debit']
            totaux['credit'] += ligne['total_credit']
            if solde > 0:
                totaux['solde_debiteur'] += solde
            else:
                totaux['solde_crediteur'] += -solde

        return Response({
            'parametres': {
                'niveau': niveau,
                'periode': {
                    'debut': date_debut or 'Début',
                    'fin': date_fin or 'Fin'
                },
                'type_solde': type_solde
            },
            'nombre_lignes': len(balance_finale),
            'lignes': balance_finale,
            'totaux': totaux,
            'controle': {
                'equilibre_mouvements': abs(totaux['debit'] - totaux['credit']) < 0.01,
                'equilibre_soldes': abs(totaux['solde_debiteur'] - totaux['solde_crediteur']) < 0.01
            }
        })

    @action(detail=False, methods=['get'])
    def compte_tiers(self, request):
        """
        Relevé de compte pour un tiers

        GET /api/lignes-ecritures/compte_tiers/
        Params:
            - tiers_id: ID du tiers
            - date_debut, date_fin
            - lettrees_only: Seulement les lettrées
            - non_lettrees_only: Seulement les non lettrées
        """
        tiers_id = request.query_params.get('tiers_id')

        if not tiers_id:
            return Response(
                {'error': "L'ID du tiers est obligatoire"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            tiers = Tiers.objects.get(id=tiers_id)
        except Tiers.DoesNotExist:
            return Response(
                {'error': "Tiers introuvable"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Construire la requête
        queryset = self.filter_queryset(self.get_queryset())
        queryset = queryset.filter(tiers=tiers)
        queryset = queryset.exclude(ecriture__statut='BROUILLON')

        # Filtres
        date_debut = request.query_params.get('date_debut')
        date_fin = request.query_params.get('date_fin')

        if date_debut:
            queryset = queryset.filter(ecriture__date_ecriture__gte=date_debut)
        if date_fin:
            queryset = queryset.filter(ecriture__date_ecriture__lte=date_fin)

        if request.query_params.get('lettrees_only') == 'true':
            queryset = queryset.filter(is_lettree=True)
        elif request.query_params.get('non_lettrees_only') == 'true':
            queryset = queryset.filter(is_lettree=False)

        # Calculer le solde d'ouverture si date_debut
        solde_ouverture = Decimal('0')
        if date_debut:
            lignes_anterieures = LigneEcriture.objects.filter(
                tiers=tiers,
                ecriture__date_ecriture__lt=date_debut,
                ecriture__statut__in=['VALIDEE', 'CLOTUREE']
            )

            totaux_ant = lignes_anterieures.aggregate(
                debit=Coalesce(Sum('montant_debit'), Decimal('0')),
                credit=Coalesce(Sum('montant_credit'), Decimal('0'))
            )

            solde_ouverture = totaux_ant['debit'] - totaux_ant['credit']

        # Construire le relevé
        lignes_releve = []
        solde_cumule = solde_ouverture

        for ligne in queryset.order_by('ecriture__date_ecriture', 'numero_ligne'):
            if ligne.montant_debit > 0:
                solde_cumule += ligne.montant_debit
            else:
                solde_cumule -= ligne.montant_credit

            lignes_releve.append({
                'date': ligne.ecriture.date_ecriture,
                'numero': ligne.ecriture.numero,
                'libelle': ligne.libelle,
                'piece': ligne.piece,
                'debit': ligne.montant_debit,
                'credit': ligne.montant_credit,
                'solde': solde_cumule,
                'lettrage': ligne.code_lettrage,
                'echeance': ligne.date_echeance,
                'jours_retard': (
                            date.today() - ligne.date_echeance).days if ligne.date_echeance and not ligne.is_lettree else None
            })

        # Totaux
        totaux = queryset.aggregate(
            total_debit=Coalesce(Sum('montant_debit'), Decimal('0')),
            total_credit=Coalesce(Sum('montant_credit'), Decimal('0'))
        )

        solde_final = solde_ouverture + totaux['total_debit'] - totaux['total_credit']

        # Analyse par échéance (pour les non lettrées)
        if tiers.type_tiers in ['CLIENT', 'FOURNISSEUR']:
            echeances = queryset.filter(
                is_lettree=False,
                date_echeance__isnull=False
            ).values('date_echeance').annotate(
                montant=Sum(
                    Case(
                        When(montant_debit__gt=0, then='montant_debit'),
                        When(montant_credit__gt=0, then=F('montant_credit') * -1),
                        default=0,
                        output_field=DecimalField()
                    )
                )
            ).order_by('date_echeance')

            # Regroupement par période
            analyse_echeances = {
                'echu': Decimal('0'),
                'a_30_jours': Decimal('0'),
                'a_60_jours': Decimal('0'),
                'a_90_jours': Decimal('0'),
                'plus_90_jours': Decimal('0')
            }

            for ech in echeances:
                jours = (ech['date_echeance'] - date.today()).days
                montant = ech['montant']

                if jours < 0:
                    analyse_echeances['echu'] += montant
                elif jours <= 30:
                    analyse_echeances['a_30_jours'] += montant
                elif jours <= 60:
                    analyse_echeances['a_60_jours'] += montant
                elif jours <= 90:
                    analyse_echeances['a_90_jours'] += montant
                else:
                    analyse_echeances['plus_90_jours'] += montant
        else:
            analyse_echeances = None

        return Response({
            'tiers': {
                'code': tiers.code,
                'raison_sociale': tiers.raison_sociale,
                'type': tiers.type_tiers,
                'telephone': tiers.telephone,
                'email': tiers.email
            },
            'periode': {
                'debut': date_debut or 'Début',
                'fin': date_fin or 'Fin'
            },
            'solde_ouverture': solde_ouverture,
            'mouvements': {
                'nombre': len(lignes_releve),
                'total_debit': totaux['total_debit'],
                'total_credit': totaux['total_credit']
            },
            'solde_final': solde_final,
            'sens_solde': 'Débiteur' if solde_final > 0 else 'Créditeur' if solde_final < 0 else 'Soldé',
            'lignes': lignes_releve,
            'analyse_echeances': analyse_echeances
        })

    @action(detail=False, methods=['get'])
    def echeancier(self, request):
        """
        Échéancier général des tiers

        GET /api/lignes-ecritures/echeancier/
        Params:
            - type_tiers: CLIENT, FOURNISSEUR
            - date_reference: Date de référence (défaut: aujourd'hui)
            - inclure_lettrees: Inclure les lettrées (false par défaut)
        """
        type_tiers = request.query_params.get('type_tiers')
        date_reference = request.query_params.get('date_reference', date.today())
        inclure_lettrees = request.query_params.get('inclure_lettrees', 'false') == 'true'

        if isinstance(date_reference, str):
            date_reference = datetime.strptime(date_reference, '%Y-%m-%d').date()

        # Base query
        queryset = LigneEcriture.objects.filter(
            tiers__isnull=False,
            date_echeance__isnull=False,
            ecriture__statut__in=['VALIDEE', 'CLOTUREE']
        )

        if type_tiers:
            queryset = queryset.filter(tiers__type_tiers=type_tiers)

        if not inclure_lettrees:
            queryset = queryset.filter(is_lettree=False)

        # Calcul des soldes par tiers et échéance
        echeancier_data = []

        # Grouper par tiers
        tiers_ids = queryset.values_list('tiers', flat=True).distinct()

        for tiers_id in tiers_ids:
            tiers = Tiers.objects.get(id=tiers_id)
            lignes_tiers = queryset.filter(tiers=tiers)

            # Calculer le solde total du tiers
            solde_tiers = lignes_tiers.aggregate(
                debit=Coalesce(Sum('montant_debit'), Decimal('0')),
                credit=Coalesce(Sum('montant_credit'), Decimal('0'))
            )

            solde = solde_tiers['debit'] - solde_tiers['credit']

            # Skip si soldé
            if abs(solde) < 0.01:
                continue

            # Détail par échéance
            echeances = lignes_tiers.values('date_echeance').annotate(
                montant=Sum(
                    Case(
                        When(montant_debit__gt=0, then='montant_debit'),
                        When(montant_credit__gt=0, then=F('montant_credit') * -1),
                        default=0,
                        output_field=DecimalField()
                    )
                ),
                nb_lignes=Count('id')
            ).order_by('date_echeance')

            # Répartition par période
            repartition = {
                'echu': {'montant': Decimal('0'), 'nombre': 0},
                '0_30': {'montant': Decimal('0'), 'nombre': 0},
                '31_60': {'montant': Decimal('0'), 'nombre': 0},
                '61_90': {'montant': Decimal('0'), 'nombre': 0},
                'plus_90': {'montant': Decimal('0'), 'nombre': 0}
            }

            echeances_detail = []

            for ech in echeances:
                jours = (ech['date_echeance'] - date_reference).days
                montant = ech['montant']

                echeances_detail.append({
                    'date': ech['date_echeance'],
                    'montant': abs(montant),
                    'jours': jours,
                    'statut': 'Échu' if jours < 0 else 'À échoir'
                })

                # Répartition
                if jours < 0:
                    repartition['echu']['montant'] += abs(montant)
                    repartition['echu']['nombre'] += ech['nb_lignes']
                elif jours <= 30:
                    repartition['0_30']['montant'] += abs(montant)
                    repartition['0_30']['nombre'] += ech['nb_lignes']
                elif jours <= 60:
                    repartition['31_60']['montant'] += abs(montant)
                    repartition['31_60']['nombre'] += ech['nb_lignes']
                elif jours <= 90:
                    repartition['61_90']['montant'] += abs(montant)
                    repartition['61_90']['nombre'] += ech['nb_lignes']
                else:
                    repartition['plus_90']['montant'] += abs(montant)
                    repartition['plus_90']['nombre'] += ech['nb_lignes']

            echeancier_data.append({
                'tiers': {
                    'id': tiers.id,
                    'code': tiers.code,
                    'raison_sociale': tiers.raison_sociale,
                    'type': tiers.type_tiers,
                    'delai_paiement': tiers.delai_paiement
                },
                'solde_total': abs(solde),
                'sens': 'Débiteur' if solde > 0 else 'Créditeur',
                'repartition': repartition,
                'echeances': echeances_detail if request.query_params.get('avec_detail') == 'true' else [],
                'retard_moyen': sum(e['jours'] for e in echeances_detail if e['jours'] < 0) / len(
                    [e for e in echeances_detail if e['jours'] < 0]) if any(
                    e['jours'] < 0 for e in echeances_detail) else 0
            })

        # Trier par montant échu décroissant
        echeancier_data.sort(key=lambda x: x['repartition']['echu']['montant'], reverse=True)

        # Totaux généraux
        totaux = {
            'echu': sum(t['repartition']['echu']['montant'] for t in echeancier_data),
            '0_30': sum(t['repartition']['0_30']['montant'] for t in echeancier_data),
            '31_60': sum(t['repartition']['31_60']['montant'] for t in echeancier_data),
            '61_90': sum(t['repartition']['61_90']['montant'] for t in echeancier_data),
            'plus_90': sum(t['repartition']['plus_90']['montant'] for t in echeancier_data)
        }
        totaux['total'] = sum(totaux.values())

        return Response({
            'date_reference': date_reference,
            'type_tiers': type_tiers or 'Tous',
            'nombre_tiers': len(echeancier_data),
            'totaux': totaux,
            'tiers': echeancier_data,
            'alertes': {
                'tiers_critiques': [
                                       t for t in echeancier_data
                                       if t['repartition']['echu']['montant'] > 10000
                                          or t['retard_moyen'] > 60
                                   ][:10]
            }
        })

    @action(detail=False, methods=['get'])
    def analyse_compte(self, request):
        """
        Analyse détaillée d'un compte

        GET /api/lignes-ecritures/analyse_compte/
        Params:
            - compte_id: ID du compte
            - exercice_id: ID de l'exercice (optionnel)
        """
        compte_id = request.query_params.get('compte_id')

        if not compte_id:
            return Response(
                {'error': "L'ID du compte est obligatoire"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            compte = CompteOHADA.objects.get(id=compte_id)
        except CompteOHADA.DoesNotExist:
            return Response(
                {'error': "Compte introuvable"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Base query
        queryset = self.filter_queryset(self.get_queryset())
        queryset = queryset.filter(compte=compte)
        queryset = queryset.exclude(ecriture__statut='BROUILLON')

        # Filtre exercice
        if request.query_params.get('exercice_id'):
            queryset = queryset.filter(ecriture__exercice_id=request.query_params['exercice_id'])

        # Statistiques générales
        stats_generales = queryset.aggregate(
            nb_ecritures=Count('ecriture', distinct=True),
            nb_lignes=Count('id'),
            total_debit=Coalesce(Sum('montant_debit'), Decimal('0')),
            total_credit=Coalesce(Sum('montant_credit'), Decimal('0')),
            montant_moyen=Coalesce(
                models.Avg(
                    Case(
                        When(montant_debit__gt=0, then='montant_debit'),
                        When(montant_credit__gt=0, then='montant_credit'),
                        output_field=DecimalField()
                    )
                ),
                Decimal('0')
            )
        )

        stats_generales['solde'] = stats_generales['total_debit'] - stats_generales['total_credit']
        stats_generales['sens_solde'] = 'Débiteur' if stats_generales['solde'] > 0 else 'Créditeur' if stats_generales[
                                                                                                           'solde'] < 0 else 'Soldé'

        # Évolution mensuelle
        evolution_mensuelle = queryset.extra(
            select={'mois': "TO_CHAR(ecriture__date_ecriture, 'YYYY-MM')"}
        ).values('mois').annotate(
            nb_lignes=Count('id'),
            debit=Coalesce(Sum('montant_debit'), Decimal('0')),
            credit=Coalesce(Sum('montant_credit'), Decimal('0'))
        ).order_by('mois')

        # Calculer le solde progressif
        solde_progressif = Decimal('0')
        for mois in evolution_mensuelle:
            solde_progressif += mois['debit'] - mois['credit']
            mois['solde_progressif'] = solde_progressif

        # Journaux utilisés
        journaux_utilises = queryset.values(
            'ecriture__journal__code',
            'ecriture__journal__libelle'
        ).annotate(
            nb_ecritures=Count('ecriture', distinct=True),
            montant_total=Sum(
                Case(
                    When(montant_debit__gt=0, then='montant_debit'),
                    When(montant_credit__gt=0, then='montant_credit'),
                    output_field=DecimalField()
                )
            )
        ).order_by('-nb_ecritures')

        # Tiers fréquents (si compte de tiers)
        tiers_frequents = None
        if compte.classe == '4':
            tiers_frequents = queryset.exclude(tiers__isnull=True).values(
                'tiers__code',
                'tiers__raison_sociale'
            ).annotate(
                nb_operations=Count('id'),
                montant_total=Sum(
                    Case(
                        When(montant_debit__gt=0, then='montant_debit'),
                        When(montant_credit__gt=0, then='montant_credit'),
                        output_field=DecimalField()
                    )
                )
            ).order_by('-montant_total')[:10]

        # Analyse du lettrage
        analyse_lettrage = {
            'total_lignes': queryset.count(),
            'lignes_lettrees': queryset.filter(is_lettree=True).count(),
            'lignes_non_lettrees': queryset.filter(is_lettree=False).count(),
            'taux_lettrage': 0
        }
        if analyse_lettrage['total_lignes'] > 0:
            analyse_lettrage['taux_lettrage'] = round(
                (analyse_lettrage['lignes_lettrees'] / analyse_lettrage['total_lignes']) * 100, 2
            )

        return Response({
            'compte': {
                'code': compte.code,
                'libelle': compte.libelle,
                'classe': compte.classe,
                'type': compte.type_compte
            },
            'statistiques': stats_generales,
            'evolution_mensuelle': list(evolution_mensuelle),
            'journaux_utilises': list(journaux_utilises),
            'tiers_frequents': list(tiers_frequents) if tiers_frequents else None,
            'analyse_lettrage': analyse_lettrage,
            'derniers_mouvements': LigneEcritureSerializer(
                queryset.order_by('-ecriture__date_ecriture')[:10],
                many=True
            ).data
        })

    @action(detail=False, methods=['get'])
    def export_grand_livre_pdf(self, request):
        """
        Export du grand livre en PDF

        GET /api/lignes-ecritures/export_grand_livre_pdf/
        Note: Nécessite une librairie PDF (reportlab, weasyprint, etc.)
        """
        # Placeholder pour l'export PDF
        # Nécessiterait l'installation de reportlab ou weasyprint

        return Response({
            'message': "Export PDF non implémenté. Installer reportlab ou weasyprint.",
            'alternative': "Utiliser l'export CSV ou l'API grand_livre pour récupérer les données"
        }, status=status.HTTP_501_NOT_IMPLEMENTED)