# 🚀 NORMXIA - Plateforme SaaS Comptable Intelligente

## 📋 Description
NORMXIA est une plateforme SaaS multi-tenant de gestion comptable, fiscale et sociale pour l'espace OHADA, intégrant des IA multiples.

## 🏗️ Architecture
- **Backend**: Django + Django REST Framework + PostgreSQL
- **Frontend**: React + TypeScript + Material-UI
- **AI**: OpenAI + Anthropic + ML personnalisé
- **Multi-tenant**: django-tenants avec isolation par schéma

## 🚀 Installation rapide

```bash
# Cloner le projet
git clone https://github.com/votre-username/normxia.git
cd normxia

# Setup complet
make setup

# Lancer l'application
make run

# 1. Importer les comptes OHADA
python manage.py tenant_command import_ohada_accounts --schema=testcompany

# 2. Importer les journaux
python manage.py tenant_command import_journaux --create-defaults --schema=testcompany