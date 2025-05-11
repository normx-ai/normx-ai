# -*- coding: utf-8 -*-
import pytest
import json
from unittest.mock import patch
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model

from apps.users.models import UserType, CompanyProfile, AccountantProfile

User = get_user_model()

class AuthAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        
        # Créer un utilisateur actif
        self.active_user = User.objects.create_user(
            email='active_api@example.com',
            first_name='Active',
            last_name='API',
            phone_number='+22961234567',
            user_type=UserType.COMPANY,
            password='securepassword123'
        )
        self.active_user.is_active = True
        self.active_user.save()
        
        # Créer un utilisateur inactif
        self.inactive_user = User.objects.create_user(
            email='inactive_api@example.com',
            first_name='Inactive',
            last_name='API',
            phone_number='+22961234567',
            user_type=UserType.COMPANY,
            password='securepassword123'
        )
        
        # Créer un profil entreprise
        self.company_profile = CompanyProfile.objects.create(
            user=self.active_user,
            company_name='API Test Company',
            legal_form='SARL',
            tax_id='API123456789',
            address='123 API Street',
            city='API City',
            postal_code='12345',
            country='Bénin',
            user_position='CEO',
            accounting_system='SYSCOHADA'
        )
        
        # URL token API (simule ce qui serait défini dans les urls.py)
        self.token_url = '/api/token/'
        self.register_url = '/api/register/'
        self.profile_url = '/api/profile/'
        
    @patch('apps.users.services.token_service.TokenService.generate_jwt_token')
    def test_token_obtain_success(self, mock_generate_token):
        """Test d'obtention d'un token JWT avec succès"""
        mock_generate_token.return_value = 'fake.jwt.token'
        
        response = self.client.post(self.token_url, {
            'email': self.active_user.email,
            'password': 'securepassword123',
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)
        self.assertEqual(response.data['token'], 'fake.jwt.token')
    
    def test_token_obtain_failure(self):
        """Test d'échec d'obtention d'un token JWT"""
        # Mot de passe incorrect
        response = self.client.post(self.token_url, {
            'email': self.active_user.email,
            'password': 'wrongpassword',
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        # Utilisateur inactif
        response = self.client.post(self.token_url, {
            'email': self.inactive_user.email,
            'password': 'securepassword123',
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        # Utilisateur inexistant
        response = self.client.post(self.token_url, {
            'email': 'nonexistent@example.com',
            'password': 'securepassword123',
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    @patch('apps.users.services.auth_service.RegistrationService.register_company')
    @patch('apps.users.services.auth_service.VerificationService.generate_verification_code')
    @patch('apps.users.services.token_service.VerificationCodeService.send_verification_code')
    def test_register_company_api(self, mock_send_code, mock_generate_code, mock_register):
        """Test de l'inscription d'une entreprise via l'API"""
        # Configurer les mocks
        mock_generate_code.return_value = '123456'
        mock_send_code.return_value = True
        
        # Créer un utilisateur fictif pour le retour de register_company
        new_user = User(
            id='12345',
            email='new_company@example.com',
            first_name='New',
            last_name='Company',
            user_type=UserType.COMPANY
        )
        mock_register.return_value = (new_user, None)
        
        # Données d'inscription
        company_data = {
            'email': 'new_company@example.com',
            'password': 'securepassword123',
            'first_name': 'New',
            'last_name': 'Company',
            'phone_number': '+22961234568',
            'user_type': UserType.COMPANY,
            'company_name': 'New API Company',
            'legal_form': 'SA',
            'tax_id': 'NEWAPI123',
            'address': '123 New API Street',
            'city': 'New API City',
            'postal_code': '54321',
            'country': 'Bénin',
            'user_position': 'CFO',
            'accounting_system': 'SYSCOHADA',
            'terms_accepted': True
        }
        
        response = self.client.post(self.register_url, company_data, format='json')
        
        # Vérifier que les services ont été appelés
        mock_register.assert_called_once()
        mock_generate_code.assert_called_once()
        mock_send_code.assert_called_once()
        
        # Vérifier la réponse
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('message', response.data)
        self.assertIn('Un code de vérification a été envoyé', response.data['message'])
    
    @patch('apps.users.services.auth_service.RegistrationService.register_accountant')
    @patch('apps.users.services.auth_service.VerificationService.generate_verification_code')
    @patch('apps.users.services.token_service.VerificationCodeService.send_verification_code')
    def test_register_accountant_api(self, mock_send_code, mock_generate_code, mock_register):
        """Test de l'inscription d'un expert-comptable via l'API"""
        # Configurer les mocks
        mock_generate_code.return_value = '123456'
        mock_send_code.return_value = True
        
        # Créer un utilisateur fictif pour le retour de register_accountant
        new_user = User(
            id='12346',
            email='new_accountant@example.com',
            first_name='New',
            last_name='Accountant',
            user_type=UserType.ACCOUNTANT
        )
        mock_register.return_value = (new_user, None)
        
        # Données d'inscription
        accountant_data = {
            'email': 'new_accountant@example.com',
            'password': 'securepassword123',
            'first_name': 'New',
            'last_name': 'Accountant',
            'phone_number': '+22961234568',
            'user_type': UserType.ACCOUNTANT,
            'firm_name': 'New API Accounting Firm',
            'professional_id': 'NEWAPI-AC-123',
            'address': '123 New API Street',
            'city': 'New API City',
            'postal_code': '54321',
            'country': 'Bénin',
            'syscohada_certified': True,
            'sysbenyl_certified': True,
            'minimal_certified': False,
            'terms_accepted': True
        }
        
        response = self.client.post(self.register_url, accountant_data, format='json')
        
        # Vérifier que les services ont été appelés
        mock_register.assert_called_once()
        mock_generate_code.assert_called_once()
        mock_send_code.assert_called_once()
        
        # Vérifier la réponse
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('message', response.data)
        self.assertIn('Un code de vérification a été envoyé', response.data['message'])
    
    def test_profile_api_unauthorized(self):
        """Test de l'accès à l'API de profil sans authentification"""
        response = self.client.get(self.profile_url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    @patch('apps.users.services.token_service.TokenService.validate_jwt_token')
    def test_profile_api_authorized(self, mock_validate_token):
        """Test de l'accès à l'API de profil avec authentification"""
        # Configurer le mock pour simuler un token valide
        mock_validate_token.return_value = self.active_user
        
        # Ajouter le token d'authentification
        self.client.credentials(HTTP_AUTHORIZATION='Bearer fake.jwt.token')
        
        response = self.client.get(self.profile_url)
        
        # Vérifier que la validation du token a été appelée
        mock_validate_token.assert_called_once_with('fake.jwt.token')
        
        # Vérifier la réponse
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('email', response.data)
        self.assertEqual(response.data['email'], self.active_user.email)
        self.assertIn('user_type', response.data)
        self.assertEqual(response.data['user_type'], self.active_user.user_type)
        
        # Vérifier que le profil est inclus
        self.assertIn('profile', response.data)
        self.assertIn('company_name', response.data['profile'])
        self.assertEqual(response.data['profile']['company_name'], self.company_profile.company_name)
        
        # Nettoyer les credentials pour les tests suivants
        self.client.credentials()
    
    @patch('apps.users.services.token_service.TokenService.validate_jwt_token')
    def test_profile_update_api(self, mock_validate_token):
        """Test de la mise à jour du profil via l'API"""
        # Configurer le mock pour simuler un token valide
        mock_validate_token.return_value = self.active_user
        
        # Ajouter le token d'authentification
        self.client.credentials(HTTP_AUTHORIZATION='Bearer fake.jwt.token')
        
        # Données de mise à jour
        update_data = {
            'first_name': 'Updated',
            'last_name': 'Name',
            'profile': {
                'company_name': 'Updated Company',
                'legal_form': 'Updated Legal Form',
                'user_position': 'Updated Position'
            }
        }
        
        response = self.client.patch(self.profile_url, update_data, format='json')
        
        # Vérifier la réponse
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Recharger l'utilisateur depuis la base de données
        self.active_user.refresh_from_db()
        self.company_profile.refresh_from_db()
        
        # Vérifier que les données ont bien été mises à jour
        self.assertEqual(self.active_user.first_name, update_data['first_name'])
        self.assertEqual(self.active_user.last_name, update_data['last_name'])
        self.assertEqual(self.company_profile.company_name, update_data['profile']['company_name'])
        self.assertEqual(self.company_profile.legal_form, update_data['profile']['legal_form'])
        self.assertEqual(self.company_profile.user_position, update_data['profile']['user_position'])
        
        # Nettoyer les credentials pour les tests suivants
        self.client.credentials()
    
    @patch('apps.users.services.token_service.TokenService.validate_jwt_token')
    def test_change_password_api(self, mock_validate_token):
        """Test de la modification du mot de passe via l'API"""
        # Configurer le mock pour simuler un token valide
        mock_validate_token.return_value = self.active_user
        
        # Ajouter le token d'authentification
        self.client.credentials(HTTP_AUTHORIZATION='Bearer fake.jwt.token')
        
        # URL de changement de mot de passe
        password_url = '/api/change-password/'
        
        # Données de changement de mot de passe
        password_data = {
            'old_password': 'securepassword123',
            'new_password': 'newsecurepassword456',
            'confirm_password': 'newsecurepassword456'
        }
        
        response = self.client.post(password_url, password_data, format='json')
        
        # Vérifier la réponse
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        self.assertIn('mot de passe a été modifié avec succès', response.data['message'])
        
        # Recharger l'utilisateur depuis la base de données
        self.active_user.refresh_from_db()
        
        # Vérifier que le mot de passe a bien été modifié
        self.assertTrue(self.active_user.check_password('newsecurepassword456'))
        
        # Nettoyer les credentials pour les tests suivants
        self.client.credentials()
    
    @patch('apps.users.services.token_service.TokenService.validate_jwt_token')
    def test_verify_email_api(self, mock_validate_token):
        """Test de la vérification d'email via l'API"""
        # Créer un nouvel utilisateur non vérifié
        unverified_user = User.objects.create_user(
            email='unverified@example.com',
            first_name='Unverified',
            last_name='User',
            phone_number='+22961234569',
            user_type=UserType.COMPANY,
            password='securepassword123'
        )
        
        # Configurer le mock pour simuler un token valide
        mock_validate_token.return_value = unverified_user
        
        # Ajouter le token d'authentification
        self.client.credentials(HTTP_AUTHORIZATION='Bearer fake.jwt.token')
        
        # URL de vérification d'email
        verify_url = '/api/verify-email/'
        
        # Simuler l'envoi d'un code de vérification
        code = VerificationService.generate_verification_code()
        
        # Stocker le code et le timestamp quelque part (simulé ici)
        unverified_user.verification_code = code
        unverified_user.verification_timestamp = timezone.now()
        unverified_user.save()
        
        # Données de vérification
        verify_data = {
            'code': code
        }
        
        response = self.client.post(verify_url, verify_data, format='json')
        
        # Vérifier la réponse
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        self.assertIn('compte a été activé avec succès', response.data['message'])
        
        # Recharger l'utilisateur depuis la base de données
        unverified_user.refresh_from_db()
        
        # Vérifier que l'utilisateur est bien activé
        self.assertTrue(unverified_user.is_active)
        self.assertTrue(unverified_user.is_verified)
        
        # Nettoyer les credentials pour les tests suivants
        self.client.credentials()