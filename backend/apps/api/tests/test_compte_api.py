# apps/api/tests/test_compte_api.py
"""
Tests pour le CompteOHADAViewSet
À exécuter avec: python manage.py test apps.api.tests.test_compte_api
"""

from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from django_tenants.utils import schema_context

from apps.accounting.models import CompteOHADA
from apps.tenants.models import Tenant

User = get_user_model()


class CompteOHADAViewSetTestCase(APITestCase):
    """Tests pour l'API des comptes OHADA"""

    @classmethod
    def setUpTestData(cls):
        """Configuration des données de test"""
        # Créer un tenant de test
        cls.tenant = Tenant.objects.get(schema_name='test_company')

    def setUp(self):
        """Configuration avant chaque test"""
        # Créer et authentifier un utilisateur
        with schema_context('test_company'):
            self.user = User.objects.create_user(
                username='testuser',
                email='test@example.com',
                password='testpass123'
            )

            # Créer quelques comptes de test
            self.compte1 = CompteOHADA.objects.create(
                code='60100000',
                libelle='Achats de marchandises',
                classe='6',
                type='charge'
            )

            self.compte2 = CompteOHADA.objects.create(
                code='70100000',
                libelle='Ventes de marchandises',
                classe='7',
                type='produit'
            )

        # Obtenir le token JWT
        response = self.client.post('/api/token/', {
            'username': 'testuser',
            'password': 'testpass123'
        })
        self.token = response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')

    def test_list_comptes(self):
        """Test de la liste des comptes"""
        with schema_context('test_company'):
            response = self.client.get('/api/comptes/')

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertIn('results', response.data)
            self.assertGreaterEqual(len(response.data['results']), 2)

    def test_retrieve_compte(self):
        """Test de récupération d'un compte"""
        with schema_context('test_company'):
            response = self.client.get(f'/api/comptes/{self.compte1.id}/')

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data['code'], '60100000')
            self.assertEqual(response.data['classe'], '6')

    def test_filter_par_classe(self):
        """Test du filtre par classe"""
        with schema_context('test_company'):
            response = self.client.get('/api/comptes/?classe=6')

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            for compte in response.data['results']:
                self.assertEqual(compte['classe'], '6')

    def test_search_comptes(self):
        """Test de la recherche"""
        with schema_context('test_company'):
            response = self.client.get('/api/comptes/?search=marchandises')

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertGreaterEqual(len(response.data['results']), 2)

    def test_comptes_actifs(self):
        """Test de l'endpoint des comptes actifs"""
        with schema_context('test_company'):
            # Désactiver un compte
            self.compte2.is_active = False
            self.compte2.save()

            response = self.client.get('/api/comptes/actifs/')

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            codes = [c['code'] for c in response.data]
            self.assertIn('60100000', codes)
            self.assertNotIn('70100000', codes)

    def test_comptes_par_classe(self):
        """Test du groupement par classe"""
        with schema_context('test_company'):
            response = self.client.get('/api/comptes/par-classe/')

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertIn('classe_6', response.data)
            self.assertIn('classe_7', response.data)
            self.assertEqual(response.data['classe_6']['numero'], 6)

    def test_compte_stats(self):
        """Test des statistiques d'un compte"""
        with schema_context('test_company'):
            response = self.client.get(f'/api/comptes/{self.compte1.id}/stats/')

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertIn('nb_lignes_ecritures', response.data)
            self.assertIn('solde_debiteur', response.data)
            self.assertIn('solde_crediteur', response.data)

    def test_compte_mouvements(self):
        """Test des mouvements d'un compte"""
        with schema_context('test_company'):
            response = self.client.get(f'/api/comptes/{self.compte1.id}/mouvements/')

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertIn('compte', response.data)
            self.assertIn('totaux', response.data)
            self.assertIn('mouvements', response.data)
            self.assertIn('pagination', response.data)

    def test_search_endpoint(self):
        """Test de la recherche avancée"""
        with schema_context('test_company'):
            response = self.client.get('/api/comptes/search/?q=achat')

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertIn('resultats', response.data)
            self.assertIn('charge', response.data['resultats'])

    def test_create_compte_invalid(self):
        """Test de création avec données invalides"""
        with schema_context('test_company'):
            data = {
                'code': '123',  # Code trop court
                'libelle': 'Test',
                'classe': '1',
                'type': 'actif'
            }

            response = self.client.post('/api/comptes/', data)

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn('code', response.data)

    def test_update_compte(self):
        """Test de mise à jour d'un compte"""
        with schema_context('test_company'):
            data = {'libelle': 'Nouveau libellé'}

            response = self.client.patch(f'/api/comptes/{self.compte1.id}/', data)

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data['libelle'], 'Nouveau libellé')

    def test_cannot_update_code(self):
        """Test qu'on ne peut pas modifier le code"""
        with schema_context('test_company'):
            data = {'code': '60200000'}

            response = self.client.patch(f'/api/comptes/{self.compte1.id}/', data)

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn('error', response.data)

    def test_unauthorized_access(self):
        """Test d'accès non autorisé"""
        self.client.credentials()  # Retirer l'authentification

        response = self.client.get('/api/comptes/')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


# Script de test manuel pour le shell
def test_api_manuel():
    """
    Script pour tester l'API manuellement
    À exécuter dans le shell Django: python manage.py shell
    """
    import requests
    from django.contrib.auth import get_user_model

    # Configuration
    base_url = 'http://testcompany.localhost:8000/api'
    User = get_user_model()

    # Créer un utilisateur si nécessaire
    user, created = User.objects.get_or_create(
        username='apitest',
        defaults={'email': 'apitest@example.com'}
    )
    if created:
        user.set_password('testpass123')
        user.save()
        print("Utilisateur créé")

    # Obtenir le token
    response = requests.post(f'{base_url}/token/', {
        'username': 'apitest',
        'password': 'testpass123'
    })

    if response.status_code == 200:
        token = response.json()['access']
        print(f"Token obtenu: {token[:20]}...")

        # Headers avec token
        headers = {'Authorization': f'Bearer {token}'}

        # Test 1: Liste des comptes
        print("\n--- Test 1: Liste des comptes ---")
        response = requests.get(f'{base_url}/comptes/', headers=headers)
        print(f"Status: {response.status_code}")
        print(f"Nombre de comptes: {response.json()['count']}")

        # Test 2: Comptes par classe
        print("\n--- Test 2: Comptes par classe ---")
        response = requests.get(f'{base_url}/comptes/par-classe/', headers=headers)
        print(f"Status: {response.status_code}")
        for classe, data in response.json().items():
            if isinstance(data, dict) and 'nb_comptes' in data:
                print(f"{classe}: {data['nb_comptes']} comptes")

        # Test 3: Recherche
        print("\n--- Test 3: Recherche 'achat' ---")
        response = requests.get(f'{base_url}/comptes/search/?q=achat', headers=headers)
        print(f"Status: {response.status_code}")
        print(f"Résultats trouvés: {response.json()['total']}")

        # Test 4: Filtre par classe
        print("\n--- Test 4: Comptes classe 6 ---")
        response = requests.get(f'{base_url}/comptes/?classe=6', headers=headers)
        print(f"Status: {response.status_code}")
        print(f"Comptes classe 6: {response.json()['count']}")

    else:
        print(f"Erreur d'authentification: {response.status_code}")
        print(response.json())


if __name__ == '__main__':
    test_api_manuel()