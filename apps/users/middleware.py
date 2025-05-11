# -*- coding: utf-8 -*-
import logging

logger = logging.getLogger(__name__)

class AuthDebugMiddleware:
    """Middleware pour le débogage de l'authentification"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        """Exécuté pour chaque requête avant la vue"""

        # Analyse complète de l'authentification
        print("\n" + "=" * 60)
        print(f"AUTH DEBUG - Request to: {request.path}")
        print(f"User: {request.user}")
        print(f"User authenticated: {request.user.is_authenticated}")
        print(f"User anonymous: {request.user.is_anonymous}")

        # Analyse de la session
        print(f"Session key: {request.session.session_key}")
        print(f"Session keys: {list(request.session.keys())}")
        print(f"Session modified: {request.session.modified}")
        print(f"Session is empty: {request.session.is_empty()}")

        # Analyse des cookies
        print("Cookies:")
        for key, value in request.COOKIES.items():
            print(f"  {key}: {value[:20]}..." if len(str(value)) > 20 else f"  {key}: {value}")

        # Si l'utilisateur est authentifié, afficher les détails
        if request.user.is_authenticated:
            print(f"Authenticated user: {request.user.email}, ID: {request.user.id}")
            print(f"User type: {request.user.user_type}")
            print(f"Last login: {request.user.last_login}")

        # Process the request
        response = self.get_response(request)

        # Log the response status
        print(f"Response status: {response.status_code}")
        if hasattr(response, 'url'):
            print(f"Redirect URL: {response.url}")
        print("=" * 60 + "\n")

        return response

class SessionDebugMiddleware:
    """Middleware pour le débogage des sessions dans les cas problématiques"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Vérifier si l'utilisateur est authentifié mais ne devrait pas l'être
        if request.path == '/users/login/' and request.user.is_authenticated:
            print(f"\n!!! USER IS AUTHENTICATED ON LOGIN PAGE !!!")
            print(f"User: {request.user.email}")
            print(f"Forcing session flush to fix authentication issue")

            # Forcer la déconnexion
            from django.contrib.auth import logout
            logout(request)
            request.session.flush()

            print("Session flushed and user logged out")

        # Vérifier si l'utilisateur n'est pas authentifié mais tente d'accéder à une page protégée
        if '/dashboard/' in request.path and not request.user.is_authenticated:
            print(f"\n!!! USER IS NOT AUTHENTICATED BUT TRYING TO ACCESS DASHBOARD !!!")

        # Continuer le traitement
        response = self.get_response(request)

        return response