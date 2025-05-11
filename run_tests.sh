#!/bin/bash

# Activer l'environnement virtuel si nécessaire
# source venv/bin/activate

# Exécuter les tests avec pytest et générer un rapport de couverture
python -m pytest apps/users/tests/ -v --cov=apps.users --cov-report=term-missing:skip-covered

# Générer un rapport HTML détaillé de la couverture (facultatif)
# python -m pytest apps/users/tests/ -v --cov=apps.users --cov-report=html

# Afficher le résultat des tests
echo "Tests terminés. Voir les résultats ci-dessus."