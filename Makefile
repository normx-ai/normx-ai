.PHONY: help setup install migrate run test clean

help:
	@echo "Commandes disponibles:"
	@echo "  make setup     - Configuration initiale complète"
	@echo "  make install   - Installer les dépendances"
	@echo "  make migrate   - Exécuter les migrations"
	@echo "  make run       - Lancer le serveur de développement"
	@echo "  make test      - Exécuter les tests"
	@echo "  make clean     - Nettoyer les fichiers temporaires"

setup: install
	@echo "🚀 Configuration de la base de données..."
	cd backend && python manage.py makemigrations
	cd backend && python manage.py migrate_schemas --shared
	cd backend && python manage.py create_public_tenant
	@echo "✅ Setup terminé!"

install:
	@echo "📦 Installation des dépendances backend..."
	cd backend && pip install -r requirements.txt
	@echo "📦 Installation des dépendances frontend..."
	cd frontend && npm install
	@echo "✅ Installation terminée!"

migrate:
	cd backend && python manage.py makemigrations
	cd backend && python manage.py migrate_schemas

run:
	@echo "🚀 Lancement des serveurs..."
	@make -j 2 run-backend run-frontend

run-backend:
	cd backend && python manage.py runserver

run-frontend:
	cd frontend && npm run dev

test:
	@echo "🧪 Tests backend..."
	cd backend && pytest
	@echo "🧪 Tests frontend..."
	cd frontend && npm test

clean:
	find . -type d -name "__pycache__" -exec rm -r {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name ".DS_Store" -delete
