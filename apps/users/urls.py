from django.urls import path

from .views import (
    # Auth views
    login_view, logout_view, mfa_verification_view,
    register_select_type_view, register_company_view, register_accountant_view,
    verify_email_view, resend_verification_code_view,
    password_reset_request_view, password_reset_confirm_view, unlock_account_view,
    
    # Profile views
    profile_view, edit_basic_info_view, edit_company_profile_view,
    edit_accountant_profile_view, security_settings_view,
    change_password_view, accounting_settings_view,
    
    # Dashboard views
    dashboard_view, company_onboarding_view, accountant_onboarding_view
)

urlpatterns = [
    # Auth URLs
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('mfa-verification/', mfa_verification_view, name='mfa_verification'),
    path('register/', register_select_type_view, name='register'),
    path('register/company/', register_company_view, name='register_company'),
    path('register/accountant/', register_accountant_view, name='register_accountant'),
    path('verify-email/', verify_email_view, name='verify_email'),
    path('resend-verification-code/', resend_verification_code_view, name='resend_verification_code'),
    path('password-reset/', password_reset_request_view, name='password_reset_request'),
    path('password-reset/<uuid:user_id>/<str:token>/', password_reset_confirm_view, name='password_reset_confirm'),
    path('unlock-account/<uuid:user_id>/<str:token>/', unlock_account_view, name='unlock_account'),
    
    # Profile URLs
    path('profile/', profile_view, name='profile'),
    path('profile/edit/', edit_basic_info_view, name='edit_basic_info'),
    path('profile/company/edit/', edit_company_profile_view, name='edit_company_profile'),
    path('profile/accountant/edit/', edit_accountant_profile_view, name='edit_accountant_profile'),
    path('profile/security/', security_settings_view, name='security_settings'),
    path('profile/change-password/', change_password_view, name='change_password'),
    path('profile/accounting-settings/', accounting_settings_view, name='accounting_settings'),
    
    # Dashboard URLs
    path('dashboard/', dashboard_view, name='dashboard'),
    path('onboarding/company/', company_onboarding_view, name='company_onboarding'),
    path('onboarding/accountant/', accountant_onboarding_view, name='accountant_onboarding'),
]