# Administration Django pour Normx-AI

Ce document décrit l'implémentation de l'interface d'administration Django pour le projet Normx-AI.

## Structure de l'Administration

L'administration a été structurée de manière modulaire pour faciliter la maintenance et l'évolution :

### App Utilisateurs (`apps/users/admin/`)

* `__init__.py` - Importe et enregistre tous les modèles administratifs
* `user_admin.py` - Administration des utilisateurs
* `profile_admin.py` - Administration des profils (entreprise et expert-comptable)
* `permission_admin.py` - Administration des rôles, attributions de rôles et journaux d'audit

### App Comptabilité (`apps/comptabilite/admin/`)

Dossier créé pour accueillir les futurs modules d'administration lorsque les modèles de comptabilité seront implémentés.

## Fonctionnalités d'Administration

### Gestion des Utilisateurs

* Affichage personnalisé avec liens vers les profils associés
* Actions pour débloquer les comptes verrouillés
* Actions pour activer/désactiver les utilisateurs
* Gestion de la sécurité (tentatives de connexion, verrouillage)

### Gestion des Profils

* Profils entreprise avec système comptable configuré
* Profils expert-comptable avec certification
* Liens vers les utilisateurs associés
* Validation des types d'utilisateurs

### Gestion des Rôles et Permissions

* Hiérarchie de rôles avec héritage de permissions
* Attribution de rôles aux utilisateurs
* Journal d'audit sécurisé (lecture seule)

## Migrations

Une migration a été créée pour ajouter le champ `code` au modèle `Role`.

## Prochaines Étapes

1. Implémenter les modèles de comptabilité
2. Créer les interfaces d'administration pour ces modèles
3. Ajouter des actions d'administration supplémentaires (export de données, validation)
4. Améliorer le système de permissions avec des contrôles au niveau des lignes

## Notes de Sécurité

Le journal d'audit (`AuditLog`) est protégé contre la modification et la suppression via l'administration, assurant ainsi l'intégrité des traces d'audit.