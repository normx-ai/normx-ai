# apps/accounting/tests/test_tiers_serializers.py
"""
Tests complets pour les serializers de tiers OHADA
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from decimal import Decimal

from apps.accounting.models import (
    CompteOHADA, Tiers, ExerciceComptable,
    PeriodeComptable, Journal, EcritureComptable, LigneEcriture
)
from apps.accounting.serializers.tiers import (
    TiersSerializer, TiersMinimalSerializer,
    TiersCreationSerializer, TiersStatsSerializer,
    TiersByTypeSerializer
)

User = get_user_model()


class TiersSerializerTestCase(TestCase):
    """Tests pour le serializer principal des tiers"""

    @classmethod
    def setUpTestData(cls):
        """Données de test communes"""
        # Créer les comptes collectifs nécessaires
        cls.compte_fournisseur = CompteOHADA.objects.create(
            code='40110000',
            libelle='Fournisseurs - Achats de biens et prestations de services',
            classe='4',
            type='passif',
            ref='OHADA'
        )

        cls.compte_client = CompteOHADA.objects.create(
            code='41110000',
            libelle='Clients',
            classe='4',
            type='actif',
            ref='OHADA'
        )

        cls.compte_employe = CompteOHADA.objects.create(
            code='42110000',
            libelle='Personnel, rémunérations dues',
            classe='4',
            type='passif',
            ref='OHADA'
        )

        # Créer un utilisateur de test
        cls.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_tiers_creation_fournisseur_local(self):
        """Test création d'un fournisseur local"""
        data = {
            'type_tiers': 'FLOC',
            'raison_sociale': 'Fournisseur Test SA',
            'sigle': 'FTS',
            'numero_contribuable': 'P123456789',
            'rccm': 'RC/BZV/2024/A/001',
            'telephone': '+242 06 123 45 67',
            'email': 'contact@fournisseur-test.cg',
            'adresse': '123 Avenue de la Paix',
            'ville': 'Brazzaville',
            'pays': 'Congo',
            'delai_paiement': 30,
            'notes': 'Fournisseur principal de matériel informatique'
        }

        serializer = TiersSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

        tiers = serializer.save(created_by=self.user)

        # Vérifications
        self.assertEqual(tiers.code[:4], 'FLOC')  # Préfixe correct
        self.assertEqual(tiers.compte_collectif, self.compte_fournisseur)
        self.assertEqual(tiers.delai_paiement, 30)
        self.assertIsNone(tiers.plafond_credit)  # Pas de plafond pour fournisseur

    def test_tiers_creation_client_groupe(self):
        """Test création d'un client groupe avec plafond crédit"""
        data = {
            'type_tiers': 'CGRP',
            'raison_sociale': 'Groupe Client International',
            'sigle': 'GCI',
            'numero_contribuable': 'G987654321',
            'telephone': '+33 1 42 86 82 00',
            'email': 'contact@gci.fr',
            'pays': 'France',
            'delai_paiement': 45,
            'plafond_credit': 50000000,  # 50 millions XAF
            'exonere_tva': True,
            'notes': 'Client export - Exonéré TVA'
        }

        serializer = TiersSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

        tiers = serializer.save(created_by=self.user)

        # Vérifications
        self.assertEqual(tiers.code[:4], 'CGRP')
        self.assertEqual(tiers.compte_collectif, self.compte_client)
        self.assertEqual(tiers.plafond_credit, Decimal('50000000'))
        self.assertTrue(tiers.exonere_tva)

    def test_tiers_creation_employe(self):
        """Test création d'un employé avec matricule obligatoire"""
        # Test sans matricule - doit échouer
        data = {
            'type_tiers': 'EMPL',
            'raison_sociale': 'NDONGO Jean-Paul',
            'telephone': '+242 05 555 12 34',
            'email': 'jp.ndongo@normxia.cg'
        }

        serializer = TiersSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('matricule', serializer.errors)

        # Test avec matricule - doit réussir
        data['matricule'] = 'EMP2024001'
        serializer = TiersSerializer(data=data)
        self.assertTrue(serializer.is_valid())

        tiers = serializer.save(created_by=self.user)

        # Vérifications
        self.assertEqual(tiers.code[:4], 'EMPL')
        self.assertEqual(tiers.compte_collectif, self.compte_employe)
        self.assertEqual(tiers.delai_paiement, 0)  # Pas de délai pour employé
        self.assertIsNone(tiers.plafond_credit)  # Pas de plafond pour employé
        self.assertFalse(tiers.exonere_tva)  # Pas d'exonération pour employé

    def test_numero_contribuable_unique(self):
        """Test unicité du numéro de contribuable"""
        # Créer un premier tiers
        Tiers.objects.create(
            type_tiers='FLOC',
            raison_sociale='Premier Fournisseur',
            numero_contribuable='UNIQUE123',
            created_by=self.user
        )

        # Tenter de créer un second avec le même numéro
        data = {
            'type_tiers': 'CLOC',
            'raison_sociale': 'Autre Société',
            'numero_contribuable': 'UNIQUE123'
        }

        serializer = TiersSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('numero_contribuable', serializer.errors)

    def test_matricule_unique_employes(self):
        """Test unicité du matricule pour les employés"""
        # Créer un premier employé
        Tiers.objects.create(
            type_tiers='EMPL',
            raison_sociale='Premier Employé',
            matricule='MAT001',
            created_by=self.user
        )

        # Tenter de créer un second avec le même matricule
        data = {
            'type_tiers': 'EMPL',
            'raison_sociale': 'Second Employé',
            'matricule': 'MAT001'
        }

        serializer = TiersSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('matricule', serializer.errors)

    def test_plafond_credit_clients_seulement(self):
        """Test que le plafond crédit est réservé aux clients"""
        # Test avec fournisseur - ne doit pas accepter de plafond
        data = {
            'type_tiers': 'FLOC',
            'raison_sociale': 'Fournisseur avec Plafond',
            'plafond_credit': 1000000
        }

        serializer = TiersSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('plafond_credit', serializer.errors)

    def test_delai_paiement_validation(self):
        """Test validation du délai de paiement (0-365 jours)"""
        # Délai négatif
        data = {
            'type_tiers': 'CLOC',
            'raison_sociale': 'Client Test',
            'delai_paiement': -1
        }

        serializer = TiersSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('delai_paiement', serializer.errors)

        # Délai trop long
        data['delai_paiement'] = 400
        serializer = TiersSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('delai_paiement', serializer.errors)

        # Délai valide
        data['delai_paiement'] = 60
        serializer = TiersSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_champs_calcules(self):
        """Test des champs calculés du serializer"""
        # Créer un tiers avec solde
        tiers = Tiers.objects.create(
            type_tiers='CLOC',
            raison_sociale='Client avec Solde',
            solde_comptable=Decimal('1500000.50'),
            is_bloque=True,
            motif_blocage='Dépassement plafond',
            created_by=self.user
        )

        serializer = TiersSerializer(tiers)
        data = serializer.data

        # Vérifier les champs calculés
        self.assertEqual(data['solde_comptable_formate'], '+1 500 000,50 XAF')
        self.assertEqual(data['tiers_complet'], f'{tiers.code} - Client avec Solde')
        self.assertIn('Bloqué', data['status_display'])
        self.assertGreaterEqual(data['age_creation'], 0)


class TiersMinimalSerializerTestCase(TestCase):
    """Tests pour le serializer minimal"""

    def setUp(self):
        self.user = User.objects.create_user('test', 'test@test.com', 'pass')
        self.tiers = Tiers.objects.create(
            type_tiers='FLOC',
            raison_sociale='Fournisseur Test',
            sigle='FT',
            is_active=True,
            is_bloque=False,
            created_by=self.user
        )

    def test_minimal_fields(self):
        """Test que seuls les champs essentiels sont présents"""
        serializer = TiersMinimalSerializer(self.tiers)
        data = serializer.data

        # Champs attendus
        expected_fields = {
            'id', 'code', 'type_tiers', 'type_display',
            'raison_sociale', 'sigle', 'tiers_complet',
            'is_active', 'is_bloque'
        }

        self.assertEqual(set(data.keys()), expected_fields)
        self.assertEqual(data['tiers_complet'], f'{self.tiers.code} - Fournisseur Test')
        self.assertEqual(data['type_display'], 'Fournisseur Local')


class TiersStatsSerializerTestCase(TestCase):
    """Tests pour le serializer avec statistiques"""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user('test', 'test@test.com', 'pass')

        # Créer les données nécessaires pour les stats
        cls.compte = CompteOHADA.objects.create(
            code='60100000',
            libelle='Achats de marchandises',
            classe='6',
            type='charge'
        )

        cls.journal = Journal.objects.create(
            code='AC',
            libelle='Achats',
            type='AC'
        )

        cls.exercice = ExerciceComptable.objects.create(
            libelle='2024',
            date_debut='2024-01-01',
            date_fin='2024-12-31'
        )

        cls.periode = PeriodeComptable.objects.create(
            exercice=cls.exercice,
            mois=1,
            annee=2024,
            date_debut='2024-01-01',
            date_fin='2024-01-31'
        )

        cls.tiers = Tiers.objects.create(
            type_tiers='FLOC',
            raison_sociale='Fournisseur Stats',
            created_by=cls.user
        )

    def test_stats_sans_ecritures(self):
        """Test stats pour un tiers sans écritures"""
        serializer = TiersStatsSerializer(self.tiers)
        data = serializer.data

        self.assertEqual(data['nb_ecritures'], 0)
        self.assertEqual(data['total_debit'], 0)
        self.assertEqual(data['total_credit'], 0)
        self.assertEqual(data['solde_net'], 0)
        self.assertIsNone(data['derniere_ecriture'])
        self.assertIsNone(data['premiere_ecriture'])

    def test_stats_avec_ecritures(self):
        """Test stats avec des écritures"""
        # Créer une écriture
        ecriture = EcritureComptable.objects.create(
            journal=self.journal,
            exercice=self.exercice,
            periode=self.periode,
            date_ecriture='2024-01-15',
            libelle='Achat marchandises',
            created_by=self.user
        )

        # Créer des lignes d'écriture
        LigneEcriture.objects.create(
            ecriture=ecriture,
            compte=self.compte,
            tiers=self.tiers,
            libelle='Achat marchandises',
            montant_debit=Decimal('1000000'),
            montant_credit=Decimal('0')
        )

        LigneEcriture.objects.create(
            ecriture=ecriture,
            compte=self.compte,
            tiers=self.tiers,
            libelle='Avoir sur achat',
            montant_debit=Decimal('0'),
            montant_credit=Decimal('200000')
        )

        serializer = TiersStatsSerializer(self.tiers)
        data = serializer.data

        self.assertEqual(data['nb_ecritures'], 2)
        self.assertEqual(data['total_debit'], 1000000)
        self.assertEqual(data['total_credit'], 200000)
        self.assertEqual(data['solde_net'], 800000)
        self.assertIsNotNone(data['derniere_ecriture'])
        self.assertEqual(data['derniere_ecriture']['montant'], 200000)


class TiersCreationSerializerTestCase(TestCase):
    """Tests pour le serializer de création"""

    def setUp(self):
        self.user = User.objects.create_user('test', 'test@test.com', 'pass')

    def test_creation_champs_essentiels(self):
        """Test création avec champs essentiels seulement"""
        data = {
            'type_tiers': 'CLOC',
            'raison_sociale': 'Client Simple',
            'telephone': '+242 06 111 22 33'
        }

        serializer = TiersCreationSerializer(data=data)
        self.assertTrue(serializer.is_valid())

        tiers = serializer.save(created_by=self.user)

        # Vérifier que le code et compte sont auto-générés
        self.assertIsNotNone(tiers.code)
        self.assertIsNotNone(tiers.compte_collectif)
        self.assertTrue(tiers.code.startswith('CLOC'))

    def test_readonly_fields(self):
        """Test que code et compte_collectif sont en lecture seule"""
        data = {
            'type_tiers': 'FLOC',
            'raison_sociale': 'Fournisseur Test',
            'code': 'CUSTOM001',  # Ne doit pas être pris en compte
            'compte_collectif': 999  # Ne doit pas être pris en compte
        }

        serializer = TiersCreationSerializer(data=data)
        self.assertTrue(serializer.is_valid())

        tiers = serializer.save(created_by=self.user)

        # Le code doit être auto-généré, pas 'CUSTOM001'
        self.assertNotEqual(tiers.code, 'CUSTOM001')
        self.assertTrue(tiers.code.startswith('FLOC'))


class TiersByTypeSerializerTestCase(TestCase):
    """Tests pour le serializer de regroupement par type"""

    def test_serialization_by_type(self):
        """Test sérialisation des données groupées par type"""
        data = {
            'type_tiers': 'FLOC',
            'type_display': 'Fournisseur Local',
            'count': 25,
            'tiers_actifs': 20,
            'tiers_bloques': 2,
            'total_solde': Decimal('5500000.00'),
            'total_general': 100  # Pour calcul pourcentage
        }

        serializer = TiersByTypeSerializer(data)
        result = serializer.data

        self.assertEqual(result['count'], 25)
        self.assertEqual(result['pourcentage'], 25.0)  # 25/100 * 100
        self.assertEqual(float(result['total_solde']), 5500000.00)


# Tests d'intégration avec l'API
class TiersAPIIntegrationTestCase(APITestCase):
    """Tests d'intégration pour vérifier le comportement avec l'API"""

    def setUp(self):
        self.user = User.objects.create_user('test', 'test@test.com', 'pass')
        self.client.force_authenticate(user=self.user)

    def test_creation_via_api(self):
        """Test création complète via l'API"""
        data = {
            'type_tiers': 'CGRP',
            'raison_sociale': 'Groupe International SA',
            'sigle': 'GISA',
            'numero_contribuable': 'GI123456789',
            'telephone': '+33 1 42 00 00 00',
            'email': 'contact@gisa.com',
            'delai_paiement': 60,
            'plafond_credit': 100000000,
            'exonere_tva': True
        }

        # Simuler un appel API (nécessite les vues/viewsets configurés)
        # response = self.client.post('/api/tiers/', data, format='json')
        # self.assertEqual(response.status_code, 201)

        # Pour l'instant, tester directement le serializer
        serializer = TiersSerializer(data=data)
        self.assertTrue(serializer.is_valid())