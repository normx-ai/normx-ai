# -*- coding: utf-8 -*-
import pytest
from unittest.mock import patch, MagicMock
from django.test import TestCase, Client, RequestFactory
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.utils import timezone

from apps.users.models import UserType, CompanyProfile, AccountantProfile
from apps.users.forms import (
    LoginForm, VerificationCodeForm, MFAVerificationForm,
    PasswordResetRequestForm, PasswordResetConfirmForm,
    UserTypeSelectForm, CompanyRegistrationForm, AccountantRegistrationForm
)
from apps.users.services.auth_service import VerificationService
from apps.users.services.token_service import PasswordResetService

User = get_user_model()

class AuthViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        
        # Créer un utilisateur actif
        self.active_user = User.objects.create_user(
            email='active@example.com',
            first_name='Active',
            last_name='User',
            phone_number='+22961234567',
            user_type=UserType.COMPANY,
            password='securepassword123'
        )
        self.active_user.is_active = True
        self.active_user.save()
        
        # Créer un utilisateur inactif
        self.inactive_user = User.objects.create_user(
            email='inactive@example.com',
            first_name='Inactive',
            last_name='User',
            phone_number='+22961234567',
            user_type=UserType.COMPANY,
            password='securepassword123'
        )
        
        # Créer un utilisateur avec MFA activé
        self.mfa_user = User.objects.create_user(
            email='mfa@example.com',
            first_name='MFA',
            last_name='User',
            phone_number='+22961234567',
            user_type=UserType.COMPANY,
            password='securepassword123'
        )
        self.mfa_user.is_active = True
        self.mfa_user.mfa_enabled = True
        self.mfa_user.save()
        
        # URL de connexion
        self.login_url = reverse('login')
        
        # URL de déconnexion
        self.logout_url = reverse('logout')
        
        # URL d'inscription
        self.register_url = reverse('register')
        self.register_company_url = reverse('register_company')
        self.register_accountant_url = reverse('register_accountant')
        
        # URL de vérification d'email
        self.verify_email_url = reverse('verify_email')
        self.resend_code_url = reverse('resend_verification_code')
        
        # URL de réinitialisation de mot de passe
        self.password_reset_url = reverse('password_reset_request')
    
    def test_login_view_get(self):
        """Test de l'affichage de la page de connexion"""
        response = self.client.get(self.login_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/auth/login.html')
        self.assertIsInstance(response.context['form'], LoginForm)
    
    def test_login_view_post_success(self):
        """Test de la connexion réussie"""
        response = self.client.post(self.login_url, {
            'username': self.active_user.email,
            'password': 'securepassword123',
            'remember_me': False
        })
        
        # Vérifier la redirection vers le tableau de bord
        self.assertRedirects(response, reverse('dashboard'))
        
        # Vérifier que l'utilisateur est bien connecté
        self.assertTrue(response.wsgi_request.user.is_authenticated)
        self.assertEqual(response.wsgi_request.user.id, self.active_user.id)
    
    def test_login_view_post_with_mfa(self):
        """Test de la connexion avec MFA activé"""
        response = self.client.post(self.login_url, {
            'username': self.mfa_user.email,
            'password': 'securepassword123',
            'remember_me': False
        })
        
        # Vérifier la redirection vers la page de vérification MFA
        self.assertRedirects(response, reverse('mfa_verification'))
        
        # Vérifier que les données sont bien stockées en session
        self.assertIn('mfa_user_id', self.client.session)
        self.assertEqual(str(self.mfa_user.id), self.client.session['mfa_user_id'])
    
    def test_login_view_post_inactive_user(self):
        """Test de la connexion avec un utilisateur inactif"""
        response = self.client.post(self.login_url, {
            'username': self.inactive_user.email,
            'password': 'securepassword123',
            'remember_me': False
        })
        
        # Vérifier que la connexion a échoué
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/auth/login.html')
        
        # Vérifier que l'utilisateur n'est pas connecté
        self.assertFalse(response.wsgi_request.user.is_authenticated)
        
        # Vérifier qu'un message d'erreur est affiché
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('activ' in str(message).lower() for message in messages))
    
    def test_login_view_post_wrong_password(self):
        """Test de la connexion avec un mot de passe incorrect"""
        response = self.client.post(self.login_url, {
            'username': self.active_user.email,
            'password': 'wrongpassword',
            'remember_me': False
        })
        
        # Vérifier que la connexion a échoué
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/auth/login.html')
        
        # Vérifier que l'utilisateur n'est pas connecté
        self.assertFalse(response.wsgi_request.user.is_authenticated)
    
    def test_logout_view(self):
        """Test de la déconnexion"""
        # Connecter l'utilisateur
        self.client.login(username=self.active_user.email, password='securepassword123')
        
        # Vérifier que l'utilisateur est bien connecté
        self.assertTrue(self.client.session.get('_auth_user_id'))
        
        # Déconnecter l'utilisateur
        response = self.client.get(self.logout_url)
        
        # Vérifier la redirection vers la page de connexion
        self.assertRedirects(response, self.login_url)
        
        # Vérifier que l'utilisateur est bien déconnecté
        self.assertFalse(self.client.session.get('_auth_user_id'))
    
    def test_register_select_type_view(self):
        """Test de la page de sélection du type d'utilisateur"""
        response = self.client.get(self.register_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/auth/register_select_type.html')
        
        # Tester le POST
        response = self.client.post(self.register_url, {
            'user_type': UserType.COMPANY
        })
        
        # Vérifier la redirection vers la page d'inscription d'entreprise
        self.assertRedirects(response, self.register_company_url)
        
        # Vérifier que le type d'utilisateur est bien stocké en session
        self.assertIn('registration_user_type', self.client.session)
        self.assertEqual(UserType.COMPANY, self.client.session['registration_user_type'])
    
    @patch('apps.users.views.auth_views.RegistrationService.register_company')
    @patch('apps.users.views.auth_views.VerificationService.generate_verification_code')
    @patch('apps.users.views.auth_views.VerificationCodeService.send_verification_code')
    def test_register_company_view(self, mock_send_code, mock_generate_code, mock_register):
        """Test de la page d'inscription d'entreprise"""
        # Configurer les mocks
        mock_generate_code.return_value = '123456'
        mock_send_code.return_value = True
        
        # Créer un utilisateur fictif pour le retour de register_company
        mock_user = MagicMock()
        mock_user.id = '12345'
        mock_user.email = 'test@example.com'
        mock_register.return_value = (mock_user, None)
        
        # Définir le type d'utilisateur en session
        session = self.client.session
        session['registration_user_type'] = UserType.COMPANY
        session.save()
        
        # Tester le GET
        response = self.client.get(self.register_company_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/auth/register.html')
        self.assertIsInstance(response.context['form'], CompanyRegistrationForm)
        
        # Tester le POST
        company_data = {
            'email': 'newcompany@example.com',
            'password1': 'securepassword123',
            'password2': 'securepassword123',
            'first_name': 'New',
            'last_name': 'Company',
            'phone_number': '+22961234568',
            'company_name': 'New Company',
            'legal_form': 'SA',
            'tax_id': 'NEW123',
            'address': '123 New Street',
            'city': 'New City',
            'postal_code': '54321',
            'country': 'Bénin',
            'user_position': 'CFO',
            'accounting_system': 'SYSCOHADA',
            'terms_accepted': True
        }
        
        response = self.client.post(self.register_company_url, company_data)
        
        # Vérifier que les services ont été appelés
        mock_register.assert_called_once()
        mock_generate_code.assert_called_once()
        mock_send_code.assert_called_once()
        
        # Vérifier la redirection vers la page de vérification
        self.assertRedirects(response, self.verify_email_url)
        
        # Vérifier que les données sont bien stockées en session
        self.assertIn('verification_user_id', self.client.session)
        self.assertIn('verification_code', self.client.session)
        self.assertIn('verification_timestamp', self.client.session)
    
    @patch('apps.users.views.auth_views.VerificationService.activate_user')
    def test_verify_email_view(self, mock_activate):
        """Test de la page de vérification d'email"""
        # Configurer les mocks
        mock_activate.return_value = (True, "Compte activé avec succès")
        
        # Définir les données de vérification en session
        user_id = str(self.inactive_user.id)
        code = '123456'
        timestamp = timezone.now().isoformat()
        
        session = self.client.session
        session['verification_user_id'] = user_id
        session['verification_code'] = code
        session['verification_timestamp'] = timestamp
        session.save()
        
        # Tester le GET
        response = self.client.get(self.verify_email_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/auth/verify_email.html')
        self.assertIsInstance(response.context['form'], VerificationCodeForm)
        
        # Tester le POST
        response = self.client.post(self.verify_email_url, {
            'code': code
        })
        
        # Vérifier que le service a été appelé
        mock_activate.assert_called_once_with(
            self.inactive_user, code, code, timezone.datetime.fromisoformat(timestamp)
        )
        
        # Vérifier la redirection vers la page de connexion
        self.assertRedirects(response, self.login_url)
        
        # Vérifier que les données de session ont été nettoyées
        self.assertNotIn('verification_user_id', self.client.session)
        self.assertNotIn('verification_code', self.client.session)
        self.assertNotIn('verification_timestamp', self.client.session)
    
    @patch('apps.users.views.auth_views.PasswordResetService.send_password_reset_link')
    def test_password_reset_request_view(self, mock_send_link):
        """Test de la page de demande de réinitialisation de mot de passe"""
        # Configurer les mocks
        mock_send_link.return_value = True
        
        # Tester le GET
        response = self.client.get(self.password_reset_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/auth/password_reset_request.html')
        self.assertIsInstance(response.context['form'], PasswordResetRequestForm)
        
        # Tester le POST avec un email existant
        response = self.client.post(self.password_reset_url, {
            'email': self.active_user.email
        })
        
        # Vérifier que le service a été appelé
        mock_send_link.assert_called_once()
        
        # Vérifier la redirection vers la page de connexion
        self.assertRedirects(response, self.login_url)
        
        # Vérifier qu'un message de succès est affiché
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('envoyé' in str(message).lower() for message in messages))
        
        # Reset le mock pour le test suivant
        mock_send_link.reset_mock()
        
        # Tester le POST avec un email inexistant
        response = self.client.post(self.password_reset_url, {
            'email': 'nonexistent@example.com'
        })
        
        # Vérifier que le service n'a pas été appelé
        mock_send_link.assert_not_called()
        
        # Vérifier la redirection vers la page de connexion
        self.assertRedirects(response, self.login_url)
        
        # Vérifier qu'un message est affiché (même pour un email inexistant pour des raisons de sécurité)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(len(messages) > 0)

class DashboardViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        
        # Créer un utilisateur COMPANY
        self.company_user = User.objects.create_user(
            email='company@example.com',
            first_name='Company',
            last_name='User',
            phone_number='+22961234567',
            user_type=UserType.COMPANY,
            password='securepassword123'
        )
        self.company_user.is_active = True
        self.company_user.save()
        
        # Créer un profil COMPANY
        self.company_profile = CompanyProfile.objects.create(
            user=self.company_user,
            company_name='Test Company',
            legal_form='SARL',
            tax_id='TX123456789',
            address='123 Test Street',
            city='Test City',
            postal_code='12345',
            country='Bénin',
            user_position='CEO',
            accounting_system='SYSCOHADA'
        )
        
        # Créer un utilisateur ACCOUNTANT
        self.accountant_user = User.objects.create_user(
            email='accountant@example.com',
            first_name='Accountant',
            last_name='User',
            phone_number='+22961234567',
            user_type=UserType.ACCOUNTANT,
            password='securepassword123'
        )
        self.accountant_user.is_active = True
        self.accountant_user.save()
        
        # Créer un profil ACCOUNTANT
        self.accountant_profile = AccountantProfile.objects.create(
            user=self.accountant_user,
            firm_name='Test Accounting Firm',
            professional_id='AC123456789',
            address='123 Accounting Street',
            city='Test City',
            postal_code='12345',
            country='Bénin',
            syscohada_certified=True
        )
        
        # Marquer les profils comme ayant terminé l'onboarding
        self.company_profile.onboarding_completed = True
        self.company_profile.save()
        
        self.accountant_profile.onboarding_completed = True
        self.accountant_profile.save()
        
        # URL du tableau de bord
        self.dashboard_url = reverse('dashboard')
    
    def test_dashboard_redirect_when_not_logged_in(self):
        """Test de la redirection vers la page de connexion quand l'utilisateur n'est pas connecté"""
        response = self.client.get(self.dashboard_url)
        
        # Vérifier la redirection vers la page de connexion avec next parameter
        self.assertRedirects(response, f"{reverse('login')}?next={self.dashboard_url}")
    
    def test_dashboard_view_for_company(self):
        """Test de l'affichage du tableau de bord pour une entreprise"""
        # Connecter l'utilisateur
        self.client.login(username=self.company_user.email, password='securepassword123')
        
        response = self.client.get(self.dashboard_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/dashboard/company_dashboard.html')
    
    def test_dashboard_view_for_accountant(self):
        """Test de l'affichage du tableau de bord pour un expert-comptable"""
        # Connecter l'utilisateur
        self.client.login(username=self.accountant_user.email, password='securepassword123')
        
        response = self.client.get(self.dashboard_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/dashboard/accountant_dashboard.html')
    
    def test_dashboard_redirect_to_onboarding_when_not_completed(self):
        """Test de la redirection vers l'onboarding quand l'utilisateur ne l'a pas terminé"""
        # Marquer le profil comme n'ayant pas terminé l'onboarding
        self.company_profile.onboarding_completed = False
        self.company_profile.save()
        
        # Connecter l'utilisateur
        self.client.login(username=self.company_user.email, password='securepassword123')
        
        response = self.client.get(self.dashboard_url)
        
        # Vérifier la redirection vers la page d'onboarding
        self.assertRedirects(response, reverse('company_onboarding'))

class ProfileViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        
        # Créer un utilisateur
        self.user = User.objects.create_user(
            email='profile@example.com',
            first_name='Profile',
            last_name='Test',
            phone_number='+22961234567',
            user_type=UserType.COMPANY,
            password='securepassword123'
        )
        self.user.is_active = True
        self.user.save()
        
        # Créer un profil entreprise
        self.profile = CompanyProfile.objects.create(
            user=self.user,
            company_name='Test Company',
            legal_form='SARL',
            tax_id='TX123456789',
            address='123 Test Street',
            city='Test City',
            postal_code='12345',
            country='Bénin',
            user_position='CEO',
            accounting_system='SYSCOHADA'
        )
        
        # URL du profil
        self.profile_url = reverse('profile')
        self.edit_basic_info_url = reverse('edit_basic_info')
        self.edit_company_profile_url = reverse('edit_company_profile')
        self.security_settings_url = reverse('security_settings')
        self.change_password_url = reverse('change_password')
        self.accounting_settings_url = reverse('accounting_settings')
    
    def test_profile_view(self):
        """Test de l'affichage du profil"""
        # Connecter l'utilisateur
        self.client.login(username=self.user.email, password='securepassword123')
        
        response = self.client.get(self.profile_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/profile/company_detail.html')
        self.assertEqual(response.context['user'], self.user)
        self.assertEqual(response.context['profile'], self.profile)
    
    def test_edit_basic_info_view(self):
        """Test de la modification des informations de base"""
        # Connecter l'utilisateur
        self.client.login(username=self.user.email, password='securepassword123')
        
        # Tester le GET
        response = self.client.get(self.edit_basic_info_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/profile/edit_basic_info.html')
        self.assertIsInstance(response.context['form'], UserBasicInfoForm)
        
        # Tester le POST
        new_data = {
            'first_name': 'Updated',
            'last_name': 'Name',
            'phone_number': '+22961234568'
        }
        
        response = self.client.post(self.edit_basic_info_url, new_data)
        
        # Vérifier la redirection vers le profil
        self.assertRedirects(response, self.profile_url)
        
        # Recharger l'utilisateur depuis la base de données
        self.user.refresh_from_db()
        
        # Vérifier que les données ont bien été mises à jour
        self.assertEqual(self.user.first_name, new_data['first_name'])
        self.assertEqual(self.user.last_name, new_data['last_name'])
        self.assertEqual(self.user.phone_number, new_data['phone_number'])
    
    def test_edit_company_profile_view(self):
        """Test de la modification du profil entreprise"""
        # Connecter l'utilisateur
        self.client.login(username=self.user.email, password='securepassword123')
        
        # Tester le GET
        response = self.client.get(self.edit_company_profile_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/profile/edit_company.html')
        self.assertIsInstance(response.context['form'], CompanyProfileForm)
        
        # Tester le POST
        new_data = {
            'company_name': 'Updated Company',
            'legal_form': 'SA',
            'address': 'Updated Address',
            'city': 'Updated City',
            'postal_code': '54321',
            'country': 'Togo',
            'user_position': 'CTO'
        }
        
        response = self.client.post(self.edit_company_profile_url, new_data)
        
        # Vérifier la redirection vers le profil
        self.assertRedirects(response, self.profile_url)
        
        # Recharger le profil depuis la base de données
        self.profile.refresh_from_db()
        
        # Vérifier que les données ont bien été mises à jour
        self.assertEqual(self.profile.company_name, new_data['company_name'])
        self.assertEqual(self.profile.legal_form, new_data['legal_form'])
        self.assertEqual(self.profile.address, new_data['address'])
        self.assertEqual(self.profile.city, new_data['city'])
        self.assertEqual(self.profile.postal_code, new_data['postal_code'])
        self.assertEqual(self.profile.country, new_data['country'])
        self.assertEqual(self.profile.user_position, new_data['user_position'])
    
    def test_security_settings_view(self):
        """Test de la modification des paramètres de sécurité"""
        # Connecter l'utilisateur
        self.client.login(username=self.user.email, password='securepassword123')
        
        # Tester le GET
        response = self.client.get(self.security_settings_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/profile/security_settings.html')
        self.assertIsInstance(response.context['form'], SecuritySettingsForm)
        
        # Tester le POST
        response = self.client.post(self.security_settings_url, {
            'mfa_enabled': True
        })
        
        # Vérifier la redirection vers le profil
        self.assertRedirects(response, self.profile_url)
        
        # Recharger l'utilisateur depuis la base de données
        self.user.refresh_from_db()
        
        # Vérifier que les données ont bien été mises à jour
        self.assertTrue(self.user.mfa_enabled)
    
    def test_accounting_settings_view(self):
        """Test de la modification des paramètres comptables"""
        # Connecter l'utilisateur
        self.client.login(username=self.user.email, password='securepassword123')
        
        # Tester le GET
        response = self.client.get(self.accounting_settings_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/profile/accounting_settings.html')
        self.assertIsInstance(response.context['form'], AccountingSettingsForm)
        
        # Tester le POST
        response = self.client.post(self.accounting_settings_url, {
            'accounting_system': 'SYSBENYL'
        })
        
        # Vérifier la redirection vers le profil
        self.assertRedirects(response, self.profile_url)
        
        # Recharger le profil depuis la base de données
        self.profile.refresh_from_db()
        
        # Vérifier que les données ont bien été mises à jour
        self.assertEqual(self.profile.accounting_system, 'SYSBENYL')