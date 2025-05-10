Processus d'authentification de Normx IA - Parcours utilisateur détaillé
1. Inscription (Sign-up)
Arrivée sur la page d'accueil

L'utilisateur arrive sur la page d'accueil de Normx IA
Il voit un bouton "S'inscrire" et un bouton "Se connecter"
Il clique sur "S'inscrire"

Choix du type de compte

L'utilisateur est présenté avec deux options:

"Je suis une entreprise ou organisation" (COMPANY)
"Je suis un expert-comptable" (ACCOUNTANT)


L'utilisateur sélectionne l'option qui correspond à son profil

Formulaire d'inscription adapté au profil
Pour un profil COMPANY:

Informations d'authentification:

Adresse email (servira d'identifiant)
Mot de passe (avec critères de sécurité)
Confirmation du mot de passe


Informations personnelles:

Nom et prénom
Fonction dans l'entreprise
Numéro de téléphone


Informations de l'entreprise:

Nom de l'entreprise
Forme juridique
Numéro d'identification fiscale
Adresse complète


Choix du système comptable:

SYSCOHADA (standard)
SYSBENYL (associations/ONG)
Système minimal (TPE)


Conditions d'utilisation et politique de confidentialité

Pour un profil ACCOUNTANT:

Informations d'authentification:

Adresse email (servira d'identifiant)
Mot de passe (avec critères de sécurité)
Confirmation du mot de passe


Informations personnelles:

Nom et prénom
Numéro de téléphone


Informations du cabinet:

Nom du cabinet
Numéro d'agrément professionnel
Adresse complète


Compétences/certifications:

SYSCOHADA (oui/non)
SYSBENYL (oui/non)
Système minimal (oui/non)


Conditions d'utilisation et politique de confidentialité

Validation et confirmation

L'utilisateur soumet le formulaire
Le système vérifie:

L'unicité de l'email
La complexité du mot de passe
La validité des informations (ex: format du numéro fiscal)


Un email de confirmation est envoyé à l'adresse fournie
Une page de confirmation s'affiche avec des instructions

Activation du compte

L'utilisateur reçoit l'email avec un code de vérification à 6 chiffres 
L'utilisateur doit saisir ce code sur une page de validation dédiée
Le code expire après 30 minutes pour des raisons de sécurité
L'utilisateur peut demander un nouveau code si nécessaire
Une fois le code validé, le compte est activé immédiatement

2. Connexion (Login)
Page de connexion

Champs requis:

Email
Mot de passe


Options supplémentaires:

Case à cocher "Se souvenir de moi"
Lien "Mot de passe oublié"



Processus d'authentification

L'utilisateur saisit ses identifiants et soumet le formulaire
Le système:

Vérifie l'existence de l'email dans la base de données
Compare le mot de passe hashé
Vérifie que le compte est actif et validé


Si les informations sont correctes:

Génère un token JWT pour l'API
Crée une session pour l'interface web
Enregistre la date/heure de dernière connexion


Si les informations sont incorrectes:

Affiche un message d'erreur générique (pour des raisons de sécurité)
Incrémente un compteur de tentatives échouées



Protection contre les attaques

Après 3 tentatives échouées, 
- un délai de 10 mimutes est imposé avant de pouvoir réessayer
- Un message explicatif est affiché avec compte à rebours
Après 5 tentatives, 
- le compte est temporairement verrouillé pendnat 1 heure
- un email d'alerte est envoyé à l'utilsateurs
- L'utilisateur peut débloquer son compte immédiatement via un lien sécurisé dans l'email
Les connexions depuis des localisations inhabituelles déclenchent une vérification supplémentaire

3. Premier accès après connexion
Pour un profil COMPANY (première fois)

Redirection vers un assistant de configuration (onboarding)
Étapes de l'assistant:

Bienvenue et présentation du système
Configuration de l'exercice fiscal initial
Paramétrage des préférences comptables
Importation du plan comptable OHADA (pré-rempli selon le système choisi)
Configuration des journaux comptables
Tutoriel rapide des fonctionnalités principales


Après complétion, redirection vers le tableau de bord personnalisé

Pour un profil ACCOUNTANT (première fois)

Redirection vers un assistant d'onboarding spécifique
Étapes de l'assistant:

Bienvenue et présentation du système
Configuration du cabinet et des paramètres par défaut
Options pour ajouter des clients existants:

Invitation par email
Création manuelle de comptes clients


Configuration des modèles de documents
Tutoriel des fonctionnalités spécifiques aux experts-comptables


Après complétion, redirection vers le tableau de bord du cabinet

4. Connexions ultérieures
Pour un profil COMPANY

Redirection directe vers le tableau de bord de l'entreprise
Affichage des notifications importantes (échéances fiscales, tâches en attente)
Accès direct aux fonctionnalités les plus utilisées

Pour un profil ACCOUNTANT

Redirection vers le tableau de bord du cabinet
Affichage de la liste des clients avec indicateurs d'activité
Option pour basculer rapidement entre les entreprises clientes
Lors du changement de client:

L'interface s'adapte au système comptable du client sélectionné
Les données et options spécifiques à ce client sont chargées
Le contexte utilisateur est mis à jour pour refléter le client actif



5. Déconnexion

L'utilisateur clique sur le bouton de déconnexion
Le système:

Invalide le token JWT
Détruit la session côté serveur
Efface les cookies de session
Enregistre l'heure de déconnexion


Redirection vers la page d'accueil avec confirmation de déconnexion

6. Récupération de mot de passe

L'utilisateur clique sur "Mot de passe oublié" depuis la page de connexion
Il saisit son adresse email
Un email avec un lien de réinitialisation à usage unique est envoyé
Le lien expire après 24 heures
En cliquant sur le lien, l'utilisateur accède à un formulaire de création de nouveau mot de passe
Après confirmation, l'utilisateur est redirigé vers la page de connexion avec un message de succès

Cette structure d'authentification complète assure sécurité, flexibilité et une expérience utilisateur fluide adaptée aux différents profils d'utilisateurs de Normx IA.