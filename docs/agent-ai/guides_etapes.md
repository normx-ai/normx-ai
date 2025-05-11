🧭 guides_etapes.md
Agent : Accueil & Orientation – NormX IA
Objectif : Assister l’utilisateur tout au long de son inscription jusqu’à l’activation de son compte.

🔹 Étape 1 : Arrivée sur la page d’accueil
Action utilisateur	Intervention de l’agent
L’utilisateur visite la page d’accueil	Affichage automatique d’un message de bienvenue personnalisé : "Bienvenue sur NormX IA ! Souhaitez-vous de l’aide pour commencer ?"
L’utilisateur hésite entre “S’inscrire” et “Se connecter”	L’agent peut demander : "Avez-vous déjà un compte ?" et rediriger selon la réponse.

🔹 Étape 2 : Choix du type de profil
Action utilisateur	Intervention de l’agent
L’utilisateur clique sur “S’inscrire”	L’agent IA affiche une explication claire des deux profils possibles avec exemple à l’appui.
L’utilisateur survole une option (COMPANY ou ACCOUNTANT)	L’agent affiche un encart explicatif avec les cas d’usage les plus courants.
L’utilisateur semble hésiter	L’agent pose des questions-guides : "Travaillez-vous pour une entreprise ? Gérez-vous plusieurs clients ?" pour aider au choix.

🔹 Étape 3 : Remplissage du formulaire d’inscription
Phase	Intervention de l’agent
Champs email / téléphone	Vérifie le format en direct, propose un exemple si champ mal rempli.
Mot de passe	Affiche les critères de sécurité requis en temps réel.
Champs fiscaux ou juridiques	L’agent peut expliquer chaque champ : "Le numéro d’identification fiscale est délivré par…"
Blocage utilisateur (champ vide ou erreur)	Message personnalisé : "Ce champ semble incorrect, puis-je vous aider ?", avec bouton d’explication rapide.

🔹 Étape 4 : Choix du système comptable
Action utilisateur	Intervention de l’agent
Sélection du système	Affichage d’un tableau comparatif simplifié si l’utilisateur clique sur "?"
Indécision de l’utilisateur	L’agent propose un mini-arbre de décision interactif basé sur des questions : secteur, taille, activité.
Erreur d’incompatibilité (ex : SYSBENYL pour une société commerciale)	Alerte pédagogique : "Ce système est normalement réservé aux associations. Souhaitez-vous revoir votre choix ?"

🔹 Étape 5 : Acceptation des conditions
Action utilisateur	Intervention de l’agent
Coche des CGU	L’agent peut proposer un résumé interactif : "Souhaitez-vous connaître les points clés de notre politique de confidentialité ?"

🔹 Étape 6 : Validation du formulaire
Action utilisateur	Intervention de l’agent
L’utilisateur clique sur “Valider”	L’agent effectue un check final : cohérence des champs, format email/téléphone, duplication d’email
Si erreur	Message d’erreur clair, lien vers assistance immédiate ou retour automatique au champ problématique
Si tout est bon	Message d’encouragement : "Parfait, il ne vous reste plus qu’à confirmer votre adresse email pour activer votre compte."

🔹 Étape 7 : Attente de confirmation
Situation	Intervention de l’agent
Email non reçu après 1 min	L’agent propose : "Souhaitez-vous que je renvoie le code de validation ?"
Code erroné saisi	L’agent affiche une explication du code (6 chiffres, durée de validité) + propose un renvoi
Code expiré	L’agent propose un lien pour générer un nouveau code
Code validé	Message de bienvenue avec lien vers l’assistant d’onboarding personnalisé selon le profil choisi

💬 Ton et personnalisation
Le ton utilisé est chaleureux, pédagogique, rassurant, adapté au niveau de l’utilisateur.

Les réponses sont dynamiques et ajustées selon les mots-clés détectés dans le comportement (profil, hésitation, erreurs).

