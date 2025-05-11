# -*- coding: utf-8 -*-
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

class AuthDebugMiddleware:
    """Middleware de débogage pour les problèmes d'authentification"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        # Avant le traitement de la requête
        if settings.DEBUG and request.path.startswith('/users/'):
            logger.debug(f"[AuthDebug] Request Path: {request.path}")
            logger.debug(f"[AuthDebug] User is authenticated: {request.user.is_authenticated}")
            
            if request.user.is_authenticated:
                logger.debug(f"[AuthDebug] User: {request.user.email}")
                logger.debug(f"[AuthDebug] User ID: {request.user.id}")
                logger.debug(f"[AuthDebug] User Type: {request.user.user_type}")
                logger.debug(f"[AuthDebug] Last Login: {request.user.last_login}")
                
            # Analyser les cookies d'authentification
            logger.debug(f"[AuthDebug] Cookies: {list(request.COOKIES.keys())}")
            if 'sessionid' in request.COOKIES:
                logger.debug(f"[AuthDebug] Session Cookie: {request.COOKIES.get('sessionid')[:8]}...")
        
        # Appel du processus standard de la requête
        response = self.get_response(request)
        
        # Après le traitement de la requête
        if settings.DEBUG and request.path.startswith('/users/'):
            logger.debug(f"[AuthDebug] Response Status: {response.status_code}")
            
            # Vérifier les cookies de session dans la réponse
            if 'Set-Cookie' in response:
                logger.debug(f"[AuthDebug] Set-Cookie Header: {response['Set-Cookie']}")
        
        return response