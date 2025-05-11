import pytest
from django.utils import timezone
from django.contrib.auth import get_user_model
from apps.users.models import UserType, CompanyProfile, AccountantProfile

User = get_user_model()

@pytest.fixture
def active_company_user():
    """Crée un utilisateur entreprise actif"""
    user = User.objects.create_user(
        email='test_company@example.com',
        first_name='Test',
        last_name='Company',
        phone_number='+22961234567',
        user_type=UserType.COMPANY,
        password='securepassword123'
    )
    user.is_active = True
    user.save()
    return user

@pytest.fixture
def inactive_company_user():
    """Crée un utilisateur entreprise inactif"""
    user = User.objects.create_user(
        email='inactive_company@example.com',
        first_name='Inactive',
        last_name='Company',
        phone_number='+22961234568',
        user_type=UserType.COMPANY,
        password='securepassword123'
    )
    return user

@pytest.fixture
def active_accountant_user():
    """Crée un utilisateur expert-comptable actif"""
    user = User.objects.create_user(
        email='test_accountant@example.com',
        first_name='Test',
        last_name='Accountant',
        phone_number='+22961234569',
        user_type=UserType.ACCOUNTANT,
        password='securepassword123'
    )
    user.is_active = True
    user.save()
    return user

@pytest.fixture
def company_profile(active_company_user):
    """Crée un profil entreprise"""
    profile = CompanyProfile.objects.create(
        user=active_company_user,
        company_name='Test Company',
        legal_form='SARL',
        tax_id='TEST123456789',
        address='123 Test Street',
        city='Test City',
        postal_code='12345',
        country='Bénin',
        user_position='CEO',
        accounting_system='SYSCOHADA'
    )
    return profile

@pytest.fixture
def accountant_profile(active_accountant_user):
    """Crée un profil expert-comptable"""
    profile = AccountantProfile.objects.create(
        user=active_accountant_user,
        firm_name='Test Accounting Firm',
        professional_id='TEST-AC-123',
        address='123 Accounting Street',
        city='Test City',
        postal_code='12345',
        country='Bénin',
        syscohada_certified=True,
        sysbenyl_certified=False,
        minimal_certified=True
    )
    return profile

@pytest.fixture
def locked_user():
    """Crée un utilisateur verrouillé"""
    user = User.objects.create_user(
        email='locked@example.com',
        first_name='Locked',
        last_name='User',
        phone_number='+22961234570',
        user_type=UserType.COMPANY,
        password='securepassword123'
    )
    user.is_active = True
    user.lock_account(duration_minutes=60)
    user.save()
    return user

@pytest.fixture
def mfa_user():
    """Crée un utilisateur avec MFA activé"""
    user = User.objects.create_user(
        email='mfa@example.com',
        first_name='MFA',
        last_name='User',
        phone_number='+22961234571',
        user_type=UserType.COMPANY,
        password='securepassword123'
    )
    user.is_active = True
    user.mfa_enabled = True
    user.save()
    return user

@pytest.fixture
def verification_code():
    """Retourne un code de vérification valide"""
    return '123456'

@pytest.fixture
def verification_timestamp():
    """Retourne un timestamp de vérification récent"""
    return timezone.now()