# Contenu du CONTRIBUTING.md ci-dessus
# Guide de Contribution - NORMX AI

## 🚀 Workflow de développement

### 1. Récupérer les dernières modifications
```bash
git checkout main
git pull origin main
```

### 2. Créer une branche pour votre fonctionnalité
```bash
# Format: type/description-courte
git checkout -b feature/ajout-rapport-comptable
git checkout -b fix/correction-calcul-tva
git checkout -b docs/mise-a-jour-readme
```

### 3. Conventions de nommage des branches
- `feature/` : Nouvelle fonctionnalité
- `fix/` : Correction de bug
- `docs/` : Documentation
- `refactor/` : Refactoring du code
- `test/` : Ajout ou modification de tests
- `style/` : Changements UI/UX

### 4. Faire vos modifications
```bash
# Vérifier le statut
git status

# Ajouter les fichiers modifiés
git add .

# Ou ajouter des fichiers spécifiques
git add src/components/MonComposant.tsx
```

### 5. Conventions de commit
Format : `<type>(<scope>): <sujet>`

**Types :**
- `feat`: Nouvelle fonctionnalité
- `fix`: Correction de bug
- `docs`: Documentation
- `style`: Formatage, points-virgules manquants, etc.
- `refactor`: Refactoring du code
- `test`: Ajout de tests
- `chore`: Maintenance, mise à jour des dépendances

**Exemples :**
```bash
git commit -m "feat(comptabilité): ajout du module de saisie d'écritures"
git commit -m "fix(api): correction de l'erreur 404 sur les journaux"
git commit -m "docs(readme): ajout des instructions d'installation"
```

### 6. Pousser votre branche
```bash
git push origin feature/ajout-rapport-comptable
```

### 7. Créer une Pull Request
1. Aller sur GitHub
2. Cliquer sur "Compare & pull request"
3. Remplir le template de PR
4. Assigner un reviewer (normx-ai ou Tred95)
5. Attendre la review

### 8. Après l'approbation
```bash
# Mettre à jour avec main si nécessaire
git checkout feature/ma-branche
git pull origin main
git push origin feature/ma-branche

# La PR sera mergée via GitHub
```

### 9. Nettoyer après le merge
```bash
# Revenir sur main
git checkout main
git pull origin main

# Supprimer la branche locale
git branch -d feature/ma-branche
```

## 📋 Checklist avant de créer une PR

- [ ] Code testé localement
- [ ] Pas de console.log() oubliés
- [ ] Code commenté si nécessaire
- [ ] Documentation mise à jour
- [ ] Commits suivent les conventions
- [ ] Branche à jour avec main

## 🛠 Configuration de l'environnement

### Backend (Django)
```bash
cd /chemin/vers/projet
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

### Frontend (React)
```bash
cd frontend
npm install
npm run dev
```

## 🤝 Code Review

### Pour les reviewers :
- Vérifier la logique du code
- Suggérer des améliorations
- Vérifier les conventions de code
- Tester localement si nécessaire
- Être constructif et bienveillant

### Pour les contributeurs :
- Répondre aux commentaires
- Faire les modifications demandées
- Expliquer vos choix si nécessaire
- Remercier pour les reviews

## 📞 Contact

- **Lead Dev**: @normx-ai
- **Frontend**: @Tred95
- **Email**: contact@normx-ai.com

## 🎯 Priorités du projet

1. **Stabilité** : Le code doit être robuste
2. **Maintenabilité** : Code clair et bien documenté
3. **Performance** : Optimiser quand nécessaire
4. **UX** : Interface intuitive et réactive