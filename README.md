# Normx-AI

Projet Normx-AI, une plateforme de gestion et d'intégration d'agents IA pour le secteur de la comptabilité.

## Structure du projet

Le projet est organisé en modules:
- **Users**: Gestion de l'authentification et des profils utilisateurs
- **Comptabilite**: Gestion des entreprises et des relations entre entités
- **Agents**: Services d'intelligence artificielle spécialisés

## Installation

```bash
# Cloner le dépôt
git clone https://github.com/votre-organisation/normx-ai.git
cd normx-ai

# Installer les dépendances
pip install -r requirements/development.txt

# Lancer les migrations
python manage.py migrate

# Démarrer le serveur
python manage.py runserver
```

## Développement

Le projet utilise Django comme framework principal avec une architecture modulaire.