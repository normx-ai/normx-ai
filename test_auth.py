#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import django

# Configure Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

# Imports supplémentaires
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test.client import RequestFactory
from django.urls import reverse
from django.http import HttpResponse

# Créer une requête bidon
factory = RequestFactory()
request = factory.get('/')

# Assignation d'un utilisateur anonyme
request.user = AnonymousUser()

# Vérifier si l'utilisateur est authentifié (devrait être False)
print(f"Anonymous user is_authenticated: {request.user.is_authenticated}")

# Récupérer le modèle utilisateur
User = get_user_model()

try:
    # Essayer de récupérer un utilisateur réel
    user = User.objects.first()
    if user:
        print(f"Found user: {user.email}, id: {user.id}")
        print(f"User is_authenticated: {user.is_authenticated}")
    else:
        print("No users found in the database")
except Exception as e:
    print(f"Error fetching user: {str(e)}")

# Afficher les paramètres d'authentification
from django.conf import settings
print(f"LOGIN_URL: {settings.LOGIN_URL}")
print(f"LOGIN_REDIRECT_URL: {settings.LOGIN_REDIRECT_URL}")
print(f"LOGOUT_REDIRECT_URL: {settings.LOGOUT_REDIRECT_URL}")