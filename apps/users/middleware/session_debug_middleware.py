# -*- coding: utf-8 -*-
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

class SessionDebugMiddleware:
    """Middleware de débogage pour les problèmes de session"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        # Avant le traitement de la requête
        if settings.DEBUG and request.path.startswith('/users/'):
            logger.debug(f"[SessionDebug] Request Path: {request.path}")
            logger.debug(f"[SessionDebug] Session ID: {request.session.session_key}")
            logger.debug(f"[SessionDebug] Session Modified: {request.session.modified}")
            logger.debug(f"[SessionDebug] Session is Empty: {request.session.is_empty()}")
            
            if not request.session.is_empty():
                logger.debug(f"[SessionDebug] Session Data: {dict(request.session)}")
        
        # Appel du processus standard de la requête
        response = self.get_response(request)
        
        # Après le traitement de la requête
        if settings.DEBUG and request.path.startswith('/users/') and hasattr(request, 'session'):
            logger.debug(f"[SessionDebug] After Response - Session ID: {request.session.session_key}")
            logger.debug(f"[SessionDebug] After Response - Session Modified: {request.session.modified}")
            logger.debug(f"[SessionDebug] After Response - Session is Empty: {request.session.is_empty()}")
        
        return response