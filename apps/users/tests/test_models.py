# -*- coding: utf-8 -*-
import pytest
from django.utils import timezone
from datetime import timedelta
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model

from apps.users.models import User, UserType, CompanyProfile, AccountantProfile, Role, UserRole, AuditLog

User = get_user_model()

class UserModelTest(TestCase):
    def setUp(self):
        self.user_data = {
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User',
            'phone_number': '+22961234567',
            'user_type': UserType.COMPANY,
            'password': 'securepassword123'
        }
        self.user = User.objects.create_user(**self.user_data)

    def test_user_creation(self):
        """Test de la création d'un utilisateur"""
        self.assertEqual(self.user.email, self.user_data['email'])
        self.assertEqual(self.user.first_name, self.user_data['first_name'])
        self.assertEqual(self.user.last_name, self.user_data['last_name'])
        self.assertEqual(self.user.user_type, self.user_data['user_type'])
        self.assertFalse(self.user.is_active)  # Par défaut, l'utilisateur n'est pas actif

    def test_get_full_name(self):
        """Test de la méthode get_full_name"""
        expected_name = f"{self.user_data['first_name']} {self.user_data['last_name']}"
        self.assertEqual(self.user.get_full_name(), expected_name)

    def test_get_short_name(self):
        """Test de la méthode get_short_name"""
        self.assertEqual(self.user.get_short_name(), self.user_data['first_name'])

    def test_account_locking(self):
        """Test des méthodes de verrouillage de compte"""
        # Vérifier que le compte n'est pas verrouillé par défaut
        self.assertFalse(self.user.is_locked())
        
        # Verrouiller le compte
        self.user.lock_account(duration_minutes=10)
        self.assertTrue(self.user.is_locked())
        
        # Vérifier que le compte est bien verrouillé pour 10 minutes
        self.assertIsNotNone(self.user.locked_until)
        self.assertTrue(self.user.locked_until > timezone.now())
        self.assertTrue(self.user.locked_until < timezone.now() + timedelta(minutes=11))
        
        # Déverrouiller le compte
        self.user.unlock_account()
        self.assertFalse(self.user.is_locked())
        self.assertIsNone(self.user.locked_until)
        self.assertEqual(self.user.failed_login_attempts, 0)

    def test_record_login_attempt_success(self):
        """Test de l'enregistrement d'une tentative de connexion réussie"""
        ip = '192.168.1.1'
        device_info = {'user_agent': 'test_browser', 'os': 'test_os'}
        
        self.user.record_login_attempt(success=True, ip_address=ip, device_info=device_info)
        
        # Vérifier que la tentative est enregistrée correctement
        self.assertEqual(self.user.failed_login_attempts, 0)
        self.assertEqual(self.user.last_login_ip, ip)
        self.assertIn(device_info, self.user.known_devices)
        self.assertEqual(len(self.user.login_history), 1)
        self.assertTrue(self.user.login_history[0]['success'])
        self.assertEqual(self.user.login_history[0]['ip_address'], ip)

    def test_record_login_attempt_failure(self):
        """Test de l'enregistrement d'une tentative de connexion échouée"""
        # Première tentative échouée
        self.user.record_login_attempt(success=False)
        self.assertEqual(self.user.failed_login_attempts, 1)
        
        # Deuxième tentative échouée
        self.user.record_login_attempt(success=False)
        self.assertEqual(self.user.failed_login_attempts, 2)
        
        # Troisième tentative échouée
        self.user.record_login_attempt(success=False)
        self.assertEqual(self.user.failed_login_attempts, 3)
        
        # Quatrième tentative échouée
        self.user.record_login_attempt(success=False)
        self.assertEqual(self.user.failed_login_attempts, 4)
        
        # Cinquième tentative échouée, le compte devrait être verrouillé
        self.user.record_login_attempt(success=False)
        self.assertEqual(self.user.failed_login_attempts, 5)
        self.assertTrue(self.user.is_locked())

class CompanyProfileTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='company@example.com',
            first_name='Company',
            last_name='Test',
            phone_number='+22961234567',
            user_type=UserType.COMPANY,
            password='securepassword123'
        )
        
        self.profile_data = {
            'user': self.user,
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
        
        self.profile = CompanyProfile.objects.create(**self.profile_data)

    def test_company_profile_creation(self):
        """Test de la création d'un profil entreprise"""
        self.assertEqual(self.profile.user, self.user)
        self.assertEqual(self.profile.company_name, self.profile_data['company_name'])
        self.assertEqual(self.profile.legal_form, self.profile_data['legal_form'])
        self.assertEqual(self.profile.tax_id, self.profile_data['tax_id'])
        self.assertEqual(self.profile.user_position, self.profile_data['user_position'])
        
    def test_company_profile_str(self):
        """Test de la méthode __str__"""
        self.assertEqual(str(self.profile), self.profile_data['company_name'])

class AccountantProfileTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='accountant@example.com',
            first_name='Accountant',
            last_name='Test',
            phone_number='+22961234567',
            user_type=UserType.ACCOUNTANT,
            password='securepassword123'
        )
        
        self.profile_data = {
            'user': self.user,
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
        
        self.profile = AccountantProfile.objects.create(**self.profile_data)

    def test_accountant_profile_creation(self):
        """Test de la création d'un profil expert-comptable"""
        self.assertEqual(self.profile.user, self.user)
        self.assertEqual(self.profile.firm_name, self.profile_data['firm_name'])
        self.assertEqual(self.profile.professional_id, self.profile_data['professional_id'])
        self.assertTrue(self.profile.syscohada_certified)
        self.assertFalse(self.profile.sysbenyl_certified)
        self.assertTrue(self.profile.minimal_certified)
        
    def test_accountant_profile_str(self):
        """Test de la méthode __str__"""
        self.assertEqual(str(self.profile), self.profile_data['firm_name'])

class RoleAndPermissionsTest(TestCase):
    def setUp(self):
        # Créer un utilisateur
        self.user = User.objects.create_user(
            email='role_test@example.com',
            first_name='Role',
            last_name='Test',
            phone_number='+22961234567',
            user_type=UserType.COMPANY,
            password='securepassword123'
        )
        
        # Créer une hiérarchie de rôles
        self.parent_role = Role.objects.create(
            name='Admin',
            description='Administrateur',
            is_system=True
        )
        
        self.child_role = Role.objects.create(
            name='Manager',
            description='Gestionnaire',
            parent=self.parent_role
        )
        
    def test_role_creation(self):
        """Test de la création d'un rôle"""
        self.assertEqual(self.parent_role.name, 'Admin')
        self.assertEqual(self.parent_role.description, 'Administrateur')
        self.assertTrue(self.parent_role.is_system)
        
        self.assertEqual(self.child_role.name, 'Manager')
        self.assertEqual(self.child_role.parent, self.parent_role)
    
    def test_user_role_assignment(self):
        """Test de l'assignation d'un rôle à un utilisateur"""
        user_role = UserRole.objects.create(
            user=self.user,
            role=self.child_role,
            scope='company:1'
        )
        
        self.assertEqual(user_role.user, self.user)
        self.assertEqual(user_role.role, self.child_role)
        self.assertEqual(user_role.scope, 'company:1')

class AuditLogTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='audit_test@example.com',
            first_name='Audit',
            last_name='Test',
            phone_number='+22961234567',
            user_type=UserType.COMPANY,
            password='securepassword123'
        )
        
    def test_audit_log_creation(self):
        """Test de la création d'une entrée de journal d'audit"""
        log = AuditLog.objects.create(
            user=self.user,
            action_type=AuditLog.ActionType.LOGIN,
            object_type='User',
            object_id=str(self.user.id),
            description='User login',
            ip_address='192.168.1.1',
            user_agent='test_browser'
        )
        
        self.assertEqual(log.user, self.user)
        self.assertEqual(log.action_type, AuditLog.ActionType.LOGIN)
        self.assertEqual(log.object_type, 'User')
        self.assertEqual(log.object_id, str(self.user.id))
        self.assertEqual(log.description, 'User login')
        self.assertEqual(log.ip_address, '192.168.1.1')
        self.assertEqual(log.user_agent, 'test_browser')