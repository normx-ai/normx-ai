from django import forms
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.forms import PasswordChangeForm

from ..models import User, CompanyProfile, AccountantProfile, AccountingSystem

class UserBasicInfoForm(forms.ModelForm):
    """Formulaire pour modifier les informations de base de l'utilisateur"""
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'phone_number']
        widgets = {
            'first_name': forms.TextInput(attrs={'placeholder': _('Prénom')}),
            'last_name': forms.TextInput(attrs={'placeholder': _('Nom')}),
            'phone_number': forms.TextInput(attrs={'placeholder': _('Ex: +22961234567')}),
        }

class CompanyProfileForm(forms.ModelForm):
    """Formulaire pour modifier le profil d'entreprise"""
    
    class Meta:
        model = CompanyProfile
        fields = [
            'company_name', 'legal_form', 
            'address', 'city', 'postal_code', 'country',
            'user_position'
        ]
        widgets = {
            'company_name': forms.TextInput(attrs={'placeholder': _('Nom de l\'entreprise')}),
            'legal_form': forms.TextInput(attrs={'placeholder': _('Ex: SARL, SA, EI')}),
            'address': forms.TextInput(attrs={'placeholder': _('Adresse')}),
            'city': forms.TextInput(attrs={'placeholder': _('Ville')}),
            'postal_code': forms.TextInput(attrs={'placeholder': _('Code postal')}),
            'country': forms.TextInput(attrs={'placeholder': _('Pays')}),
            'user_position': forms.TextInput(attrs={'placeholder': _('Ex: Directeur financier')}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Le numéro d'identification fiscale ne peut pas être modifié après inscription
        if self.instance and self.instance.pk:
            self.fields.pop('tax_id', None)

class AccountantProfileForm(forms.ModelForm):
    """Formulaire pour modifier le profil d'expert-comptable"""
    
    class Meta:
        model = AccountantProfile
        fields = [
            'firm_name',
            'address', 'city', 'postal_code', 'country',
            'syscohada_certified', 'sysbenyl_certified', 'minimal_certified'
        ]
        widgets = {
            'firm_name': forms.TextInput(attrs={'placeholder': _('Nom du cabinet')}),
            'address': forms.TextInput(attrs={'placeholder': _('Adresse')}),
            'city': forms.TextInput(attrs={'placeholder': _('Ville')}),
            'postal_code': forms.TextInput(attrs={'placeholder': _('Code postal')}),
            'country': forms.TextInput(attrs={'placeholder': _('Pays')}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Le numéro d'agrément professionnel ne peut pas être modifié après inscription
        if self.instance and self.instance.pk:
            self.fields.pop('professional_id', None)

class SecuritySettingsForm(forms.ModelForm):
    """Formulaire pour les paramètres de sécurité"""
    
    class Meta:
        model = User
        fields = ['mfa_enabled']
        
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # MFA obligatoire pour les experts-comptables
        if user and user.user_type == 'ACCOUNTANT':
            self.fields['mfa_enabled'].disabled = True
            self.fields['mfa_enabled'].help_text = _("L'authentification à deux facteurs est obligatoire pour les comptes experts-comptables.")

class CustomPasswordChangeForm(PasswordChangeForm):
    """Formulaire personnalisé de changement de mot de passe"""
    
    old_password = forms.CharField(
        label=_("Mot de passe actuel"),
        strip=False,
        widget=forms.PasswordInput(attrs={'autofocus': True, 'placeholder': _('Mot de passe actuel')}),
    )
    new_password1 = forms.CharField(
        label=_("Nouveau mot de passe"),
        strip=False,
        widget=forms.PasswordInput(attrs={'placeholder': _('Nouveau mot de passe')}),
        help_text=_("Le mot de passe doit comporter au moins 8 caractères et inclure des lettres, chiffres et caractères spéciaux.")
    )
    new_password2 = forms.CharField(
        label=_("Confirmation du nouveau mot de passe"),
        strip=False,
        widget=forms.PasswordInput(attrs={'placeholder': _('Confirmez le nouveau mot de passe')}),
    )

class AccountingSettingsForm(forms.ModelForm):
    """Formulaire pour les paramètres comptables"""
    
    class Meta:
        model = CompanyProfile
        fields = ['accounting_system']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['accounting_system'].help_text = _(
            "Attention : Changer de système comptable peut nécessiter une adaptation de vos données existantes."
        )