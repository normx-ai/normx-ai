from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError(_('L\'adresse email est obligatoire'))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))
        return self.create_user(email, password, **extra_fields)

class UserType(models.TextChoices):
    COMPANY = 'COMPANY', _('Entreprise ou organisation')
    ACCOUNTANT = 'ACCOUNTANT', _('Expert-comptable')

class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(_('adresse email'), unique=True)
    first_name = models.CharField(_('prénom'), max_length=30)
    last_name = models.CharField(_('nom'), max_length=150)
    phone_number = models.CharField(
        _('numéro de téléphone'), 
        max_length=15,
        validators=[RegexValidator(regex=r'^\+?1?\d{9,15}$', message=_("Le numéro de téléphone doit être au format: '+999999999'."))]
    )
    user_type = models.CharField(
        _('type d\'utilisateur'),
        max_length=20,
        choices=UserType.choices,
        default=UserType.COMPANY,
    )
    
    # Champs statut et sécurité
    is_active = models.BooleanField(_('actif'), default=False)
    is_verified = models.BooleanField(_('vérifié'), default=False)
    is_staff = models.BooleanField(_('membre du staff'), default=False)
    date_joined = models.DateTimeField(_('date d\'inscription'), default=timezone.now)
    last_login = models.DateTimeField(_('dernière connexion'), null=True, blank=True)
    failed_login_attempts = models.PositiveSmallIntegerField(_('tentatives de connexion échouées'), default=0)
    locked_until = models.DateTimeField(_('verrouillé jusqu\'à'), null=True, blank=True)
    mfa_enabled = models.BooleanField(_('authentification à deux facteurs activée'), default=False)
    
    # Traçage
    last_login_ip = models.GenericIPAddressField(_('IP de dernière connexion'), null=True, blank=True)
    known_devices = models.JSONField(_('appareils connus'), default=list, blank=True)
    login_history = models.JSONField(_('historique de connexion'), default=list, blank=True)
    
    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'phone_number', 'user_type']

    class Meta:
        verbose_name = _('utilisateur')
        verbose_name_plural = _('utilisateurs')

    def __str__(self):
        return self.email

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def get_short_name(self):
        return self.first_name
    
    def lock_account(self, duration_minutes=60):
        self.locked_until = timezone.now() + timezone.timedelta(minutes=duration_minutes)
        self.save(update_fields=['locked_until'])
    
    def unlock_account(self):
        self.locked_until = None
        self.failed_login_attempts = 0
        self.save(update_fields=['locked_until', 'failed_login_attempts'])
    
    def is_locked(self):
        if self.locked_until and self.locked_until > timezone.now():
            return True
        return False
    
    def record_login_attempt(self, success, ip_address=None, device_info=None):
        timestamp = timezone.now()
        
        if not success:
            self.failed_login_attempts += 1
            
            # Après 5 tentatives, on verrouille le compte pour 1 heure
            if self.failed_login_attempts >= 5:
                self.lock_account(60)
            
            self.save(update_fields=['failed_login_attempts', 'locked_until'])
        else:
            # Réinitialiser les tentatives échouées lors d'une connexion réussie
            self.failed_login_attempts = 0
            self.last_login = timestamp
            self.last_login_ip = ip_address
            
            # Ajouter l'appareil aux appareils connus si ce n'est pas déjà fait
            if device_info and device_info not in self.known_devices:
                self.known_devices.append(device_info)
            
            # Enregistrer l'historique de connexion
            login_entry = {
                'timestamp': timestamp.isoformat(),
                'ip_address': ip_address,
                'device_info': device_info,
                'success': True
            }
            
            # Limiter l'historique à 10 entrées
            self.login_history = [login_entry] + self.login_history[:9]
            
            self.save(update_fields=[
                'failed_login_attempts', 'last_login', 
                'last_login_ip', 'known_devices', 'login_history'
            ])