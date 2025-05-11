# -*- coding: utf-8 -*-
import logging
import os
from django.conf import settings
from django.middleware.csrf import CsrfViewMiddleware

logger = logging.getLogger(__name__)

class CSRFDebugMiddleware(CsrfViewMiddleware):
    """Middleware de débogage pour les problèmes CSRF"""

    def __init__(self, get_response):
        super().__init__(get_response)
        self.csrf_disabled = os.environ.get('CSRF_DISABLED', '').lower() == 'true'
        if self.csrf_disabled and settings.DEBUG:
            logger.warning("CSRF PROTECTION IS DISABLED - NEVER USE THIS IN PRODUCTION")

    def process_view(self, request, callback, callback_args, callback_kwargs):
        # En mode développement avec CSRF désactivé, ignorer complètement la vérification CSRF
        if settings.DEBUG and self.csrf_disabled:
            # Log détaillé pour le débogage, mais ne pas bloquer la requête
            if request.method == 'POST':
                logger.debug(f"CSRF Check Bypassed (DEV ONLY): {request.path}")

                # Enregistrer quand même les détails pour le débogage
                self._log_csrf_debug_info(request)

            # Permettre à la requête de continuer sans vérification CSRF
            return None

        # Autrement, appeler le processeur de vue parent pour vérifier CSRF
        result = super().process_view(request, callback, callback_args, callback_kwargs)

        # Si en mode DEBUG et que la validation CSRF a échoué
        if settings.DEBUG and result is not None and result.status_code == 403:
            logger.warning("CSRF validation failed")
            self._log_csrf_debug_info(request)

        return result

    def _log_csrf_debug_info(self, request):
        # Afficher des informations détaillées sur la requête
        logger.debug(f"Request Path: {request.path}")
        logger.debug(f"Request Method: {request.method}")
        logger.debug(f"Session ID: {request.session.session_key}")
        logger.debug(f"Session Modified: {request.session.modified}")
        logger.debug(f"Session is Empty: {request.session.is_empty()}")

        # Détails sur les tokens CSRF
        token_from_form = request.POST.get('csrfmiddlewaretoken', '[MISSING]')
        token_from_cookie = request.COOKIES.get(settings.CSRF_COOKIE_NAME, '[MISSING]')
        token_from_session = request.session.get('_csrftoken', '[MISSING]')

        if token_from_form != '[MISSING]':
            logger.debug(f"CSRF Token from Form: {token_from_form[:8]}...")
        else:
            logger.debug("CSRF Token from Form: [MISSING]")

        if token_from_cookie != '[MISSING]':
            logger.debug(f"CSRF Token from Cookie: {token_from_cookie[:8]}...")
        else:
            logger.debug("CSRF Token from Cookie: [MISSING]")

        if token_from_session and token_from_session != '[MISSING]':
            logger.debug(f"CSRF Token from Session: {token_from_session[:8]}...")
        else:
            logger.debug("CSRF Token from Session: [MISSING]")

        # Vérifier l'origine
        logger.debug(f"HTTP_REFERER: {request.META.get('HTTP_REFERER', '[MISSING]')}")
        logger.debug(f"HTTP_HOST: {request.META.get('HTTP_HOST', '[MISSING]')}")