# -*- coding: utf-8 -*-
import pytest
from unittest.mock import patch, MagicMock
from django.test import TestCase, RequestFactory
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.contrib.sessions.middleware import SessionMiddleware

from apps.users.models import UserType, CompanyProfile, AccountantProfile
from apps.users.services.auth_service import AuthenticationService, RegistrationService, VerificationService
from apps.users.services.token_service import TokenService, VerificationCodeService, PasswordResetService

User = get_user_model()

class VerificationServiceTest(TestCase):
    def test_generate_verification_code(self):
        """Test de la génération d'un code de vérification"""
        code = VerificationService.generate_verification_code()
        
        # Vérifier que le code a la bonne longueur
        self.assertEqual(len(code), VerificationService.CODE_LENGTH)
        
        # Vérifier que le code ne contient que des chiffres
        self.assertTrue(code.isdigit())
    
    def test_is_code_valid(self):
        """Test de la validation d'un code"""
        # Code valide
        code = "123456"
        created_at = timezone.now()
        
        self.assertTrue(VerificationService.is_code_valid(code, code, created_at))
        
        # Code invalide (ne correspond pas)
        self.assertFalse(VerificationService.is_code_valid("654321", code, created_at))
        
        # Code expiré
        expired_time = timezone.now() - timedelta(minutes=VerificationService.CODE_EXPIRY_MINUTES + 5)
        self.assertFalse(VerificationService.is_code_valid(code, code, expired_time))
        
        # Pas de code ou de timestamp
        self.assertFalse(VerificationService.is_code_valid(code, None, created_at))
        self.assertFalse(VerificationService.is_code_valid(code, code, None))
    
    def test_activate_user(self):
        """Test de l'activation d'un utilisateur"""
        user = User.objects.create_user(
            email='activation@example.com',
            first_name='Activation',
            last_name='Test',
            phone_number='+22961234567',
            user_type=UserType.COMPANY,
            password='securepassword123'
        )
        
        code = "123456"
        created_at = timezone.now()
        
        # Code valide
        success, _ = VerificationService.activate_user(user, code, code, created_at)
        self.assertTrue(success)
        
        # Recharger l'utilisateur depuis la base de données
        user.refresh_from_db()
        
        # Vérifier que l'utilisateur est bien activé
        self.assertTrue(user.is_active)
        self.assertTrue(user.is_verified)
        
        # Code invalide
        success, _ = VerificationService.activate_user(user, "654321", code, created_at)
        self.assertFalse(success)

class RegistrationServiceTest(TestCase):
    def setUp(self):
        self.company_data = {
            'email': 'company_reg@example.com',
            'password': 'securepassword123',
            'first_name': 'Company',
            'last_name': 'Registration',
            'phone_number': '+22961234567',
            'company_name': 'Test Company',
            'legal_form': 'SARL',
            'tax_id': 'TX123456789',
            'address': '123 Test Street',
            'city': 'Test City',
            'postal_code': '12345',
            'country': 'Bénin',
            'user_position': 'CEO',
            'accounting_system': 'SYSCOHADA'
        }
        
        self.accountant_data = {
            'email': 'accountant_reg@example.com',
            'password': 'securepassword123',
            'first_name': 'Accountant',
            'last_name': 'Registration',
            'phone_number': '+22961234567',
            'firm_name': 'Test Accounting Firm',
            'professional_id': 'AC123456789',
            'address': '123 Accounting Street',
            'city': 'Test City',
            'postal_code': '12345',
            'country': 'Bénin',
            'syscohada_certified': True,
            'sysbenyl_certified': False,
            'minimal_certified': True
        }
    
    def test_register_company(self):
        """Test de l'inscription d'une entreprise"""
        user, error = RegistrationService.register_company(self.company_data)
        
        self.assertIsNone(error)
        self.assertIsNotNone(user)
        self.assertEqual(user.email, self.company_data['email'])
        self.assertEqual(user.user_type, UserType.COMPANY)
        
        # Vérifier que le profil a bien été créé
        self.assertTrue(hasattr(user, 'company_profile'))
        self.assertEqual(user.company_profile.company_name, self.company_data['company_name'])
        self.assertEqual(user.company_profile.tax_id, self.company_data['tax_id'])
    
    def test_register_accountant(self):
        """Test de l'inscription d'un expert-comptable"""
        user, error = RegistrationService.register_accountant(self.accountant_data)
        
        self.assertIsNone(error)
        self.assertIsNotNone(user)
        self.assertEqual(user.email, self.accountant_data['email'])
        self.assertEqual(user.user_type, UserType.ACCOUNTANT)
        
        # Vérifier que le profil a bien été créé
        self.assertTrue(hasattr(user, 'accountant_profile'))
        self.assertEqual(user.accountant_profile.firm_name, self.accountant_data['firm_name'])
        self.assertEqual(user.accountant_profile.professional_id, self.accountant_data['professional_id'])
        
        # Vérifier que MFA est activé par défaut pour les experts-comptables
        self.assertTrue(user.mfa_enabled)
    
    def test_register_duplicate_email(self):
        """Test de l'inscription avec un email déjà utilisé"""
        # Créer un premier utilisateur
        RegistrationService.register_company(self.company_data)
        
        # Tenter de créer un autre utilisateur avec le même email
        duplicate_data = self.company_data.copy()
        duplicate_data['company_name'] = 'Another Company'
        user, error = RegistrationService.register_company(duplicate_data)
        
        self.assertIsNone(user)
        self.assertIsNotNone(error)
        self.assertIn('email', error.lower())

class AuthenticationServiceTest(TestCase):
    def setUp(self):
        # Créer un utilisateur actif
        self.user = User.objects.create_user(
            email='auth_test@example.com',
            first_name='Auth',
            last_name='Test',
            phone_number='+22961234567',
            user_type=UserType.COMPANY,
            password='securepassword123'
        )
        self.user.is_active = True
        self.user.save()
        
        # Créer un utilisateur inactif
        self.inactive_user = User.objects.create_user(
            email='inactive@example.com',
            first_name='Inactive',
            last_name='User',
            phone_number='+22961234567',
            user_type=UserType.COMPANY,
            password='securepassword123'
        )
        
        # Créer un utilisateur verrouillé
        self.locked_user = User.objects.create_user(
            email='locked@example.com',
            first_name='Locked',
            last_name='User',
            phone_number='+22961234567',
            user_type=UserType.COMPANY,
            password='securepassword123'
        )
        self.locked_user.is_active = True
        self.locked_user.lock_account(duration_minutes=60)
        self.locked_user.save()
        
        # Créer une factory de requêtes
        self.factory = RequestFactory()
    
    def _get_request(self):
        """Crée une requête HTTP avec une session"""
        request = self.factory.post('/login/')
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(request)
        request.session.save()
        
        # Ajouter des informations sur la requête
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        request.META['HTTP_USER_AGENT'] = 'test_browser'
        
        return request
    
    def test_login_success(self):
        """Test d'une connexion réussie"""
        request = self._get_request()
        user, error = AuthenticationService.login(
            request=request,
            email=self.user.email,
            password='securepassword123',
            remember=False
        )
        
        self.assertIsNone(error)
        self.assertIsNotNone(user)
        self.assertEqual(user.id, self.user.id)
        
        # Recharger l'utilisateur depuis la base de données
        self.user.refresh_from_db()
        
        # Vérifier que la tentative est bien enregistrée
        self.assertEqual(self.user.failed_login_attempts, 0)
        self.assertEqual(self.user.last_login_ip, '192.168.1.1')
        self.assertGreater(len(self.user.known_devices), 0)
        self.assertGreater(len(self.user.login_history), 0)
    
    def test_login_wrong_password(self):
        """Test d'une connexion avec un mot de passe incorrect"""
        request = self._get_request()
        user, error = AuthenticationService.login(
            request=request,
            email=self.user.email,
            password='wrongpassword',
            remember=False
        )
        
        self.assertIsNone(user)
        self.assertIsNotNone(error)
        
        # Recharger l'utilisateur depuis la base de données
        self.user.refresh_from_db()
        
        # Vérifier que la tentative est bien enregistrée
        self.assertEqual(self.user.failed_login_attempts, 1)
    
    def test_login_inactive_user(self):
        """Test d'une connexion avec un utilisateur inactif"""
        request = self._get_request()
        user, error = AuthenticationService.login(
            request=request,
            email=self.inactive_user.email,
            password='securepassword123',
            remember=False
        )
        
        self.assertIsNone(user)
        self.assertIsNotNone(error)
        self.assertIn('activ', error.lower())  # Vérifie que le message mentionne l'activation
    
    def test_login_locked_user(self):
        """Test d'une connexion avec un utilisateur verrouillé"""
        request = self._get_request()
        user, error = AuthenticationService.login(
            request=request,
            email=self.locked_user.email,
            password='securepassword123',
            remember=False
        )
        
        self.assertIsNone(user)
        self.assertIsNotNone(error)
        self.assertIn('verrouill', error.lower())  # Vérifie que le message mentionne le verrouillage
    
    def test_login_nonexistent_user(self):
        """Test d'une connexion avec un utilisateur inexistant"""
        request = self._get_request()
        user, error = AuthenticationService.login(
            request=request,
            email='nonexistent@example.com',
            password='securepassword123',
            remember=False
        )
        
        self.assertIsNone(user)
        self.assertIsNotNone(error)
    
    def test_logout(self):
        """Test de la déconnexion"""
        request = self._get_request()
        
        # Connexion
        user, _ = AuthenticationService.login(
            request=request,
            email=self.user.email,
            password='securepassword123',
            remember=False
        )
        
        # Déconnexion
        AuthenticationService.logout(request, user)
        
        # Recharger l'utilisateur depuis la base de données
        self.user.refresh_from_db()
        
        # Vérifier que la déconnexion est enregistrée dans l'historique
        self.assertGreater(len(self.user.login_history), 0)
        self.assertEqual(self.user.login_history[0]['action'], 'logout')

class TokenServiceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='token_test@example.com',
            first_name='Token',
            last_name='Test',
            phone_number='+22961234567',
            user_type=UserType.COMPANY,
            password='securepassword123'
        )
    
    def test_generate_jwt_token(self):
        """Test de la génération d'un token JWT"""
        token = TokenService.generate_jwt_token(self.user)
        
        # Vérifier que le token est bien une chaîne non vide
        self.assertIsInstance(token, str)
        self.assertTrue(len(token) > 0)
    
    def test_validate_jwt_token(self):
        """Test de la validation d'un token JWT"""
        # Générer un token
        token = TokenService.generate_jwt_token(self.user)
        
        # Valider le token
        validated_user = TokenService.validate_jwt_token(token)
        
        # Vérifier que l'utilisateur est bien récupéré
        self.assertIsNotNone(validated_user)
        self.assertEqual(validated_user.id, self.user.id)
    
    @patch('apps.users.services.token_service.send_mail')
    def test_send_verification_code(self, mock_send_mail):
        """Test de l'envoi d'un code de vérification"""
        mock_send_mail.return_value = 1  # Simuler un envoi réussi
        
        code = "123456"
        result = VerificationCodeService.send_verification_code(self.user, code)
        
        # Vérifier que l'envoi a réussi
        self.assertTrue(result)
        
        # Vérifier que send_mail a été appelé avec les bons arguments
        mock_send_mail.assert_called_once()
        call_args = mock_send_mail.call_args[1]
        self.assertEqual(call_args['recipient_list'], [self.user.email])
    
    @patch('apps.users.services.token_service.send_mail')
    def test_send_password_reset_link(self, mock_send_mail):
        """Test de l'envoi d'un lien de réinitialisation de mot de passe"""
        mock_send_mail.return_value = 1  # Simuler un envoi réussi
        
        result = PasswordResetService.send_password_reset_link(self.user)
        
        # Vérifier que l'envoi a réussi
        self.assertTrue(result)
        
        # Vérifier que send_mail a été appelé avec les bons arguments
        mock_send_mail.assert_called_once()
        call_args = mock_send_mail.call_args[1]
        self.assertEqual(call_args['recipient_list'], [self.user.email])