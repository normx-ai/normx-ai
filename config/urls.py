from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.urls import reverse

def home_view(request):
    """Redirection vers le dashboard ou la page de login selon l'état d'authentification"""
    from django.contrib.auth import logout

    # Vérifier si l'URL a un paramètre pour forcer la déconnexion
    should_force_logout = 'force_logout' in request.GET

    # Détails complets sur l'authentification pour le débogage
    print("=" * 50)
    print("HOME VIEW - Authentication Details")
    print(f"User: {request.user}")
    print(f"User is authenticated: {request.user.is_authenticated}")
    print(f"User is anonymous: {request.user.is_anonymous}")
    print(f"Session ID: {request.session.session_key}")
    print(f"Session data: {dict(request.session)}")
    print(f"Session modified: {request.session.modified}")
    print(f"Session is empty: {request.session.is_empty()}")
    print(f"Force logout requested: {should_force_logout}")
    print("=" * 50)

    # Si la déconnexion est demandée, déconnecter l'utilisateur
    if should_force_logout and request.user.is_authenticated:
        print("Forcing logout as requested")
        logout(request)
        request.session.flush()
        # Rediriger vers la page d'accueil sans le paramètre
        return HttpResponseRedirect('/')

    # Vérification explicite de l'authenticité de l'utilisateur
    if request.user.is_authenticated:
        print("Redirecting to dashboard (user is authenticated)")
        return HttpResponseRedirect('/users/dashboard/')
    else:
        # Si l'utilisateur n'est pas dans un processus d'inscription, nettoyer toutes les données associées
        if 'registration_user_type' in request.session:
            del request.session['registration_user_type']
            print("Cleaned up registration session data")

        print("Redirecting to login (user is NOT authenticated)")
        return HttpResponseRedirect('/users/login/')

def debug_view(request):
    """Vue de débogage pour vérifier l'état d'authentification"""
    from django.http import HttpResponse
    import datetime

    # Informations sur l'utilisateur et la session
    user_info = [
        f"<h2>DEBUG INFO - {datetime.datetime.now()}</h2>",
        f"<p><strong>User:</strong> {request.user}</p>",
        f"<p><strong>Authenticated:</strong> {request.user.is_authenticated}</p>",
        f"<p><strong>Anonymous:</strong> {request.user.is_anonymous}</p>",
        f"<p><strong>Session Key:</strong> {request.session.session_key}</p>",
        f"<p><strong>Session Data:</strong> {dict(request.session)}</p>",
        f"<p><strong>Cookies:</strong> {request.COOKIES}</p>"
    ]

    # Informations sur les variables d'environnement
    user_info.append("<h3>Environment</h3>")
    user_info.append(f"<p><strong>Request Method:</strong> {request.method}</p>")
    user_info.append(f"<p><strong>Request Path:</strong> {request.path}</p>")
    user_info.append(f"<p><strong>Request GET:</strong> {request.GET}</p>")

    # Actions de débogage
    user_info.append("<h3>Debug Actions</h3>")
    user_info.append(f'<p><a href="/users/login/">Go to Login</a></p>')
    user_info.append(f'<p><a href="/users/register/">Go to Register</a></p>')
    user_info.append(f'<p><a href="/users/dashboard/">Go to Dashboard</a></p>')
    user_info.append(f'<p><a href="/debug/reset-session/">Reset Session</a></p>')
    user_info.append(f'<p><a href="/?force_logout=1" style="color: red;">Force Logout</a></p>')

    return HttpResponse("<br>".join(user_info))

def reset_session_view(request):
    """Vue pour réinitialiser complètement la session"""
    from django.http import HttpResponse
    import datetime

    # Réinitialiser la session
    request.session.flush()

    return HttpResponse(f"""
    <h2>Session Reset at {datetime.datetime.now()}</h2>
    <p>Your session has been completely reset.</p>
    <p><a href="/debug/">Back to Debug</a></p>
    <p><a href="/">Go to Home</a></p>
    """)

urlpatterns = [
    path('admin/', admin.site.urls),

    # Applications URLs
    path('users/', include('apps.users.urls')),
    path('users', RedirectView.as_view(url='/users/'), name='users_redirect'),
    path('comptabilite/', include('apps.comptabilite.urls')),
    path('agents/', include('apps.agents.urls')),
    path('api/', include('apps.api.urls')),

    # Redirect root based on authentication status
    path('', home_view, name='home'),

    # Redirect login/register endpoints at root level
    path('login/', RedirectView.as_view(url='/users/login/'), name='root_login'),
    path('register/', RedirectView.as_view(url='/users/register/'), name='root_register'),

    # Debug views
    path('debug/', debug_view, name='debug'),
    path('debug/reset-session/', reset_session_view, name='reset_session'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)