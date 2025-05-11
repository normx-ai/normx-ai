● J'ai préparé un ensemble complet de tests pour votre système d'authentification dans Normx-AI. Voici ce qui a été
   créé :

  1. Tests de modèles (test_models.py) :
    - Tests des différentes classes de modèles (User, CompanyProfile, AccountantProfile)
    - Tests des fonctionnalités de verrouillage de compte
    - Tests des enregistrements de tentatives de connexion
    - Tests du système de rôles et permissions
  2. Tests de services (test_services.py) :
    - Tests des services d'authentification
    - Tests d'inscription des différents types d'utilisateurs
    - Tests de vérification d'email
    - Tests de génération et validation de tokens JWT
  3. Tests de formulaires (test_forms.py) :
    - Tests de validation des formulaires d'inscription
    - Tests des formulaires de connexion et vérification
    - Tests des formulaires de profil et paramètres de sécurité
  4. Tests de vues (test_views.py) :
    - Tests des vues d'authentification (connexion, inscription, vérification)
    - Tests des vues de profil et paramètres
    - Tests du tableau de bord et onboarding
  5. Tests d'API (test_api.py) :
    - Tests des endpoints d'API pour l'authentification et la gestion de profil
  6. Configuration de tests (conftest.py) :
    - Fixtures pytest pour faciliter la création d'objets de test réutilisables
  7. Configuration :
    - Configuration pytest avec pytest.ini
    - Configuration de couverture de code avec .coveragerc
    - Script d'exécution des tests run_tests.sh

  Pour exécuter les tests, vous pouvez utiliser le script run_tests.sh que j'ai créé, qui lancera les tests avec
  pytest et générera un rapport de couverture.

  Ces tests valident tous les aspects du système d'authentification, y compris :
  - L'inscription et l'activation de compte avec vérification par email
  - La connexion avec protection contre les attaques par force brute
  - Le support de l'authentification à deux facteurs (MFA)
  - La gestion des profils d'utilisateurs (entreprises et experts-comptables)
  - Les fonctionnalités de sécurité (verrouillage/déverrouillage de compte, réinitialisation de mot de passe)

╭───────────────────