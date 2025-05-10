from .auth_views import (
    login_view, logout_view, mfa_verification_view,
    register_select_type_view, register_company_view, register_accountant_view,
    verify_email_view, resend_verification_code_view,
    password_reset_request_view, password_reset_confirm_view, unlock_account_view
)

from .profile_views import (
    profile_view, edit_basic_info_view, edit_company_profile_view,
    edit_accountant_profile_view, security_settings_view,
    change_password_view, accounting_settings_view
)

from .dashboard_views import (
    dashboard_view, company_onboarding_view, accountant_onboarding_view
)