# -*- coding: utf-8 -*-
from django import forms
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.forms import AuthenticationForm, PasswordResetForm, SetPasswordForm
from django.contrib.auth.password_validation import validate_password

from ..models import User, UserType, AccountingSystem, CompanyProfile, AccountantProfile

class LoginForm(AuthenticationForm):
    """Formulaire de connexion"""
    username = forms.EmailField(
        label=_("Email"),
        widget=forms.EmailInput(attrs={'autofocus': True, 'placeholder': _('Email')}),
    )
    password = forms.CharField(
        label=_("Mot de passe"),
        strip=False,
        widget=forms.PasswordInput(attrs={'placeholder': _('Mot de passe')}),
    )
    remember_me = forms.BooleanField(
        label=_("Se souvenir de moi"),
        required=False,
        initial=False
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Personnalisation des erreurs
        self.error_messages.update({
            'invalid_login': _("Email ou mot de passe incorrect."),
            'inactive': _("Ce compte n'est pas activé. Veuillez vérifier votre email.")
        })

class VerificationCodeForm(forms.Form):
    """Formulaire de saisie du code de vérification"""
    code = forms.CharField(
        label=_("Code de vérification"),
        min_length=6,
        max_length=6,
        widget=forms.TextInput(attrs={
            'placeholder': _('Code à 6 chiffres'),
            'autofocus': True,
            'inputmode': 'numeric',
            'pattern': '[0-9]*'
        }),
        help_text=_("Saisissez le code à 6 chiffres envoyé à votre adresse email")
    )
    
    def clean_code(self):
        code = self.cleaned_data.get('code')
        if not code.isdigit():
            raise forms.ValidationError(_("Le code doit contenir uniquement des chiffres"))
        return code

class MFAVerificationForm(forms.Form):
    """Formulaire de saisie du code d'authentification à deux facteurs"""
    code = forms.CharField(
        label=_("Code d'authentification"),
        min_length=6,
        max_length=6,
        widget=forms.TextInput(attrs={
            'placeholder': _('Code à 6 chiffres'),
            'autofocus': True,
            'inputmode': 'numeric',
            'pattern': '[0-9]*'
        }),
        help_text=_("Saisissez le code à 6 chiffres généré par votre application d'authentification")
    )
    
    def clean_code(self):
        code = self.cleaned_data.get('code')
        if not code.isdigit():
            raise forms.ValidationError(_("Le code doit contenir uniquement des chiffres"))
        return code

class PasswordResetRequestForm(PasswordResetForm):
    """Formulaire de demande de réinitialisation de mot de passe"""
    email = forms.EmailField(
        label=_("Email"),
        max_length=254,
        widget=forms.EmailInput(attrs={'placeholder': _('Email')}),
        help_text=_("Saisissez l'adresse email associée à votre compte.")
    )

class PasswordResetConfirmForm(SetPasswordForm):
    """Formulaire de définition du nouveau mot de passe"""
    new_password1 = forms.CharField(
        label=_("Nouveau mot de passe"),
        widget=forms.PasswordInput(attrs={'placeholder': _('Nouveau mot de passe')}),
        strip=False,
        help_text=_("Le mot de passe doit comporter au moins 8 caractères et inclure des lettres, chiffres et caractères spéciaux.")
    )
    new_password2 = forms.CharField(
        label=_("Confirmation du mot de passe"),
        strip=False,
        widget=forms.PasswordInput(attrs={'placeholder': _('Confirmez le mot de passe')}),
    )

class UserTypeSelectForm(forms.Form):
    """Formulaire de sélection du type d'utilisateur lors de l'inscription"""
    user_type = forms.ChoiceField(
        label=_("Type de compte"),
        choices=UserType.choices,
        widget=forms.RadioSelect(),
        initial=UserType.COMPANY,
        help_text=_("Sélectionnez le type de compte que vous souhaitez créer")
    )

    def __str__(self):
        return f"UserTypeSelectForm(choices={UserType.choices})"

class CompanyRegistrationForm(forms.ModelForm):
    """Formulaire d'inscription pour les entreprises"""
    # Informations d'authentification
    email = forms.EmailField(
        label=_("Email"),
        widget=forms.EmailInput(attrs={'placeholder': _('Email')}),
        help_text=_("Cet email sera utilisé comme identifiant de connexion")
    )
    password1 = forms.CharField(
        label=_("Mot de passe"),
        strip=False,
        widget=forms.PasswordInput(attrs={'placeholder': _('Mot de passe')}),
        help_text=_("Le mot de passe doit comporter au moins 8 caractères et inclure des lettres, chiffres et caractères spéciaux.")
    )
    password2 = forms.CharField(
        label=_("Confirmation du mot de passe"),
        widget=forms.PasswordInput(attrs={'placeholder': _('Confirmez le mot de passe')}),
        strip=False,
    )
    
    # Informations personnelles
    first_name = forms.CharField(
        label=_("Prénom"),
        max_length=30,
        widget=forms.TextInput(attrs={'placeholder': _('Prénom')}),
    )
    last_name = forms.CharField(
        label=_("Nom"),
        max_length=150,
        widget=forms.TextInput(attrs={'placeholder': _('Nom')}),
    )
    phone_number = forms.CharField(
        label=_("Numéro de téléphone"),
        max_length=15,
        widget=forms.TextInput(attrs={'placeholder': _('Ex: +22961234567')}),
    )
    user_position = forms.CharField(
        label=_("Fonction dans l'entreprise"),
        max_length=100,
        widget=forms.TextInput(attrs={'placeholder': _('Ex: Directeur financier')}),
    )
    
    # Consentement
    terms_accepted = forms.BooleanField(
        label=_("J'accepte les conditions d'utilisation et la politique de confidentialité"),
        required=True,
    )
    
    class Meta:
        model = CompanyProfile
        fields = [
            'company_name', 'legal_form', 'tax_id', 
            'address', 'city', 'postal_code', 'country',
            'accounting_system'
        ]
        widgets = {
            'company_name': forms.TextInput(attrs={'placeholder': _('Nom de l\'entreprise')}),
            'legal_form': forms.TextInput(attrs={'placeholder': _('Ex: SARL, SA, EI')}),
            'tax_id': forms.TextInput(attrs={'placeholder': _('Numéro d\'identification fiscale')}),
            'address': forms.TextInput(attrs={'placeholder': _('Adresse')}),
            'city': forms.TextInput(attrs={'placeholder': _('Ville')}),
            'postal_code': forms.TextInput(attrs={'placeholder': _('Code postal')}),
            'country': forms.TextInput(attrs={'placeholder': _('Pays'), 'value': 'Bénin'}),
        }
    
    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError(_("Les mots de passe ne correspondent pas."))
        
        # Valider la complexité du mot de passe
        validate_password(password2)
        return password2
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError(_("Cette adresse email est déjà utilisée."))
        return email
    
    def clean_tax_id(self):
        tax_id = self.cleaned_data.get('tax_id')
        if CompanyProfile.objects.filter(tax_id=tax_id).exists():
            raise forms.ValidationError(_("Ce numéro d'identification fiscale est déjà enregistré."))
        return tax_id
    
    def save(self, commit=True):
        # Cette méthode ne crée pas réellement l'utilisateur,
        # elle prépare juste les données pour RegistrationService
        return self.cleaned_data

class AccountantRegistrationForm(forms.ModelForm):
    """Formulaire d'inscription pour les experts-comptables"""
    # Informations d'authentification
    email = forms.EmailField(
        label=_("Email"),
        widget=forms.EmailInput(attrs={'placeholder': _('Email')}),
        help_text=_("Cet email sera utilisé comme identifiant de connexion")
    )
    password1 = forms.CharField(
        label=_("Mot de passe"),
        strip=False,
        widget=forms.PasswordInput(attrs={'placeholder': _('Mot de passe')}),
        help_text=_("Le mot de passe doit comporter au moins 8 caractères et inclure des lettres, chiffres et caractères spéciaux.")
    )
    password2 = forms.CharField(
        label=_("Confirmation du mot de passe"),
        widget=forms.PasswordInput(attrs={'placeholder': _('Confirmez le mot de passe')}),
        strip=False,
    )
    
    # Informations personnelles
    first_name = forms.CharField(
        label=_("Prénom"),
        max_length=30,
        widget=forms.TextInput(attrs={'placeholder': _('Prénom')}),
    )
    last_name = forms.CharField(
        label=_("Nom"),
        max_length=150,
        widget=forms.TextInput(attrs={'placeholder': _('Nom')}),
    )
    phone_number = forms.CharField(
        label=_("Numéro de téléphone"),
        max_length=15,
        widget=forms.TextInput(attrs={'placeholder': _('Ex: +22961234567')}),
    )
    
    # Certifications
    syscohada_certified = forms.BooleanField(
        label=_("Je suis certifié SYSCOHADA"),
        required=False,
        initial=True
    )
    sysbenyl_certified = forms.BooleanField(
        label=_("Je suis certifié SYSBENYL"),
        required=False
    )
    minimal_certified = forms.BooleanField(
        label=_("Je suis certifié Système minimal"),
        required=False
    )
    
    # Consentement
    terms_accepted = forms.BooleanField(
        label=_("J'accepte les conditions d'utilisation et la politique de confidentialité"),
        required=True,
    )
    
    class Meta:
        model = AccountantProfile
        fields = [
            'firm_name', 'professional_id', 
            'address', 'city', 'postal_code', 'country',
        ]
        widgets = {
            'firm_name': forms.TextInput(attrs={'placeholder': _('Nom du cabinet')}),
            'professional_id': forms.TextInput(attrs={'placeholder': _('Numéro d\'agrément professionnel')}),
            'address': forms.TextInput(attrs={'placeholder': _('Adresse')}),
            'city': forms.TextInput(attrs={'placeholder': _('Ville')}),
            'postal_code': forms.TextInput(attrs={'placeholder': _('Code postal')}),
            'country': forms.TextInput(attrs={'placeholder': _('Pays'), 'value': 'Bénin'}),
        }
    
    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError(_("Les mots de passe ne correspondent pas."))
        
        # Valider la complexité du mot de passe
        validate_password(password2)
        return password2
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError(_("Cette adresse email est déjà utilisée."))
        return email
    
    def clean_professional_id(self):
        professional_id = self.cleaned_data.get('professional_id')
        if AccountantProfile.objects.filter(professional_id=professional_id).exists():
            raise forms.ValidationError(_("Ce numéro d'agrément professionnel est déjà enregistré."))
        return professional_id
    
    def save(self, commit=True):
        # Cette méthode ne crée pas réellement l'utilisateur,
        # elle prépare juste les données pour RegistrationService
        return self.cleaned_data