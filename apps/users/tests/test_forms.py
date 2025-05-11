# -*- coding: utf-8 -*-
import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from apps.users.models import UserType, CompanyProfile, AccountantProfile
from apps.users.forms import (
    LoginForm, VerificationCodeForm, MFAVerificationForm,
    PasswordResetRequestForm, PasswordResetConfirmForm,
    UserTypeSelectForm, CompanyRegistrationForm, AccountantRegistrationForm,
    UserBasicInfoForm, CompanyProfileForm, AccountantProfileForm,
    SecuritySettingsForm, CustomPasswordChangeForm, AccountingSettingsForm
)

User = get_user_model()

class LoginFormTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='loginform@example.com',
            first_name='Login',
            last_name='Form',
            phone_number='+22961234567',
            user_type=UserType.COMPANY,
            password='securepassword123'
        )
        self.user.is_active = True
        self.user.save()
    
    def test_valid_login(self):
        """Test du formulaire de connexion avec des données valides"""
        form = LoginForm(data={
            'username': 'loginform@example.com',
            'password': 'securepassword123',
            'remember_me': True
        })
        
        self.assertTrue(form.is_valid())
    
    def test_invalid_login(self):
        """Test du formulaire de connexion avec des données invalides"""
        # Email manquant
        form = LoginForm(data={
            'password': 'securepassword123'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('username', form.errors)
        
        # Mot de passe manquant
        form = LoginForm(data={
            'username': 'loginform@example.com'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('password', form.errors)
        
        # Email invalide
        form = LoginForm(data={
            'username': 'not-an-email',
            'password': 'securepassword123'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('username', form.errors)

class VerificationCodeFormTest(TestCase):
    def test_valid_code(self):
        """Test du formulaire de vérification avec un code valide"""
        form = VerificationCodeForm(data={
            'code': '123456'
        })
        
        self.assertTrue(form.is_valid())
    
    def test_invalid_code(self):
        """Test du formulaire de vérification avec un code invalide"""
        # Code trop court
        form = VerificationCodeForm(data={
            'code': '12345'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('code', form.errors)
        
        # Code trop long
        form = VerificationCodeForm(data={
            'code': '1234567'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('code', form.errors)
        
        # Code non numérique
        form = VerificationCodeForm(data={
            'code': 'abc123'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('code', form.errors)
        
        # Code manquant
        form = VerificationCodeForm(data={})
        self.assertFalse(form.is_valid())
        self.assertIn('code', form.errors)

class MFAVerificationFormTest(TestCase):
    def test_valid_code(self):
        """Test du formulaire MFA avec un code valide"""
        form = MFAVerificationForm(data={
            'code': '123456'
        })
        
        self.assertTrue(form.is_valid())
    
    def test_invalid_code(self):
        """Test du formulaire MFA avec un code invalide"""
        # Code trop court
        form = MFAVerificationForm(data={
            'code': '12345'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('code', form.errors)
        
        # Code non numérique
        form = MFAVerificationForm(data={
            'code': 'abc123'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('code', form.errors)

class UserTypeSelectFormTest(TestCase):
    def test_valid_selection(self):
        """Test du formulaire de sélection du type d'utilisateur"""
        # Type COMPANY
        form = UserTypeSelectForm(data={
            'user_type': UserType.COMPANY
        })
        self.assertTrue(form.is_valid())
        
        # Type ACCOUNTANT
        form = UserTypeSelectForm(data={
            'user_type': UserType.ACCOUNTANT
        })
        self.assertTrue(form.is_valid())
    
    def test_invalid_selection(self):
        """Test du formulaire avec un type invalide"""
        form = UserTypeSelectForm(data={
            'user_type': 'INVALID_TYPE'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('user_type', form.errors)
        
        # Type manquant
        form = UserTypeSelectForm(data={})
        self.assertFalse(form.is_valid())
        self.assertIn('user_type', form.errors)

class CompanyRegistrationFormTest(TestCase):
    def setUp(self):
        # Créer un utilisateur existant pour tester les contraintes d'unicité
        self.existing_user = User.objects.create_user(
            email='existing@example.com',
            first_name='Existing',
            last_name='User',
            phone_number='+22961234567',
            user_type=UserType.COMPANY,
            password='securepassword123'
        )
        
        # Créer un profil entreprise existant
        self.existing_profile = CompanyProfile.objects.create(
            user=self.existing_user,
            company_name='Existing Company',
            legal_form='SARL',
            tax_id='EXISTING123',
            address='123 Existing Street',
            city='Existing City',
            postal_code='12345',
            country='Bénin',
            user_position='CEO',
            accounting_system='SYSCOHADA'
        )
        
        # Données de formulaire valides
        self.valid_data = {
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
    
    def test_valid_registration(self):
        """Test du formulaire d'inscription d'entreprise avec des données valides"""
        form = CompanyRegistrationForm(data=self.valid_data)
        self.assertTrue(form.is_valid())
    
    def test_email_uniqueness(self):
        """Test de l'unicité de l'email"""
        invalid_data = self.valid_data.copy()
        invalid_data['email'] = self.existing_user.email
        
        form = CompanyRegistrationForm(data=invalid_data)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)
    
    def test_tax_id_uniqueness(self):
        """Test de l'unicité du numéro fiscal"""
        invalid_data = self.valid_data.copy()
        invalid_data['tax_id'] = self.existing_profile.tax_id
        
        form = CompanyRegistrationForm(data=invalid_data)
        self.assertFalse(form.is_valid())
        self.assertIn('tax_id', form.errors)
    
    def test_password_mismatch(self):
        """Test de la correspondance des mots de passe"""
        invalid_data = self.valid_data.copy()
        invalid_data['password2'] = 'differentpassword'
        
        form = CompanyRegistrationForm(data=invalid_data)
        self.assertFalse(form.is_valid())
        self.assertIn('password2', form.errors)
    
    def test_terms_acceptance(self):
        """Test de l'acceptation des conditions"""
        invalid_data = self.valid_data.copy()
        invalid_data['terms_accepted'] = False
        
        form = CompanyRegistrationForm(data=invalid_data)
        self.assertFalse(form.is_valid())
        self.assertIn('terms_accepted', form.errors)

class AccountantRegistrationFormTest(TestCase):
    def setUp(self):
        # Créer un utilisateur existant pour tester les contraintes d'unicité
        self.existing_user = User.objects.create_user(
            email='existing_accountant@example.com',
            first_name='Existing',
            last_name='Accountant',
            phone_number='+22961234567',
            user_type=UserType.ACCOUNTANT,
            password='securepassword123'
        )
        
        # Créer un profil expert-comptable existant
        self.existing_profile = AccountantProfile.objects.create(
            user=self.existing_user,
            firm_name='Existing Firm',
            professional_id='EXISTING-AC-123',
            address='123 Existing Street',
            city='Existing City',
            postal_code='12345',
            country='Bénin',
            syscohada_certified=True
        )
        
        # Données de formulaire valides
        self.valid_data = {
            'email': 'newaccountant@example.com',
            'password1': 'securepassword123',
            'password2': 'securepassword123',
            'first_name': 'New',
            'last_name': 'Accountant',
            'phone_number': '+22961234568',
            'firm_name': 'New Accounting Firm',
            'professional_id': 'NEW-AC-123',
            'address': '123 New Street',
            'city': 'New City',
            'postal_code': '54321',
            'country': 'Bénin',
            'syscohada_certified': True,
            'sysbenyl_certified': True,
            'minimal_certified': False,
            'terms_accepted': True
        }
    
    def test_valid_registration(self):
        """Test du formulaire d'inscription d'expert-comptable avec des données valides"""
        form = AccountantRegistrationForm(data=self.valid_data)
        self.assertTrue(form.is_valid())
    
    def test_email_uniqueness(self):
        """Test de l'unicité de l'email"""
        invalid_data = self.valid_data.copy()
        invalid_data['email'] = self.existing_user.email
        
        form = AccountantRegistrationForm(data=invalid_data)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)
    
    def test_professional_id_uniqueness(self):
        """Test de l'unicité du numéro d'agrément"""
        invalid_data = self.valid_data.copy()
        invalid_data['professional_id'] = self.existing_profile.professional_id
        
        form = AccountantRegistrationForm(data=invalid_data)
        self.assertFalse(form.is_valid())
        self.assertIn('professional_id', form.errors)

class ProfileFormsTest(TestCase):
    def setUp(self):
        # Créer un utilisateur de type COMPANY
        self.company_user = User.objects.create_user(
            email='company_profile@example.com',
            first_name='Company',
            last_name='Profile',
            phone_number='+22961234567',
            user_type=UserType.COMPANY,
            password='securepassword123'
        )
        
        # Créer un profil entreprise
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
        
        # Créer un utilisateur de type ACCOUNTANT
        self.accountant_user = User.objects.create_user(
            email='accountant_profile@example.com',
            first_name='Accountant',
            last_name='Profile',
            phone_number='+22961234567',
            user_type=UserType.ACCOUNTANT,
            password='securepassword123'
        )
        
        # Créer un profil expert-comptable
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
    
    def test_user_basic_info_form(self):
        """Test du formulaire d'informations de base"""
        # Données valides
        form = UserBasicInfoForm(instance=self.company_user, data={
            'first_name': 'Updated',
            'last_name': 'Name',
            'phone_number': '+22961234568'
        })
        self.assertTrue(form.is_valid())
        
        # Champ obligatoire manquant
        form = UserBasicInfoForm(instance=self.company_user, data={
            'first_name': '',
            'last_name': 'Name',
            'phone_number': '+22961234568'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('first_name', form.errors)
    
    def test_company_profile_form(self):
        """Test du formulaire de profil entreprise"""
        # Données valides
        form = CompanyProfileForm(instance=self.company_profile, data={
            'company_name': 'Updated Company',
            'legal_form': 'SA',
            'address': 'Updated Address',
            'city': 'Updated City',
            'postal_code': '54321',
            'country': 'Togo',
            'user_position': 'CTO'
        })
        self.assertTrue(form.is_valid())
        
        # Champ obligatoire manquant
        form = CompanyProfileForm(instance=self.company_profile, data={
            'company_name': '',
            'legal_form': 'SA',
            'address': 'Updated Address',
            'city': 'Updated City',
            'postal_code': '54321',
            'country': 'Togo',
            'user_position': 'CTO'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('company_name', form.errors)
    
    def test_accountant_profile_form(self):
        """Test du formulaire de profil expert-comptable"""
        # Données valides
        form = AccountantProfileForm(instance=self.accountant_profile, data={
            'firm_name': 'Updated Firm',
            'address': 'Updated Address',
            'city': 'Updated City',
            'postal_code': '54321',
            'country': 'Togo',
            'syscohada_certified': True,
            'sysbenyl_certified': True,
            'minimal_certified': True
        })
        self.assertTrue(form.is_valid())
        
        # Champ obligatoire manquant
        form = AccountantProfileForm(instance=self.accountant_profile, data={
            'firm_name': '',
            'address': 'Updated Address',
            'city': 'Updated City',
            'postal_code': '54321',
            'country': 'Togo',
            'syscohada_certified': True,
            'sysbenyl_certified': True,
            'minimal_certified': True
        })
        self.assertFalse(form.is_valid())
        self.assertIn('firm_name', form.errors)
    
    def test_security_settings_form(self):
        """Test du formulaire de paramètres de sécurité"""
        # Test avec une entreprise (MFA facultatif)
        form = SecuritySettingsForm(instance=self.company_user, user=self.company_user, data={
            'mfa_enabled': True
        })
        self.assertTrue(form.is_valid())
        
        # Test avec un expert-comptable (MFA obligatoire)
        form = SecuritySettingsForm(instance=self.accountant_user, user=self.accountant_user, data={
            'mfa_enabled': True
        })
        self.assertTrue(form.is_valid())
    
    def test_accounting_settings_form(self):
        """Test du formulaire de paramètres comptables"""
        # Données valides
        form = AccountingSettingsForm(instance=self.company_profile, data={
            'accounting_system': 'SYSBENYL'
        })
        self.assertTrue(form.is_valid())
        
        # Valeur invalide
        form = AccountingSettingsForm(instance=self.company_profile, data={
            'accounting_system': 'INVALID_SYSTEM'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('accounting_system', form.errors)