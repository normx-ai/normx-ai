● L'erreur indique que "admin" n'est pas une valeur valide pour le champ "Type d'utilisateur". Dans notre modèle
  User, nous avons défini deux types d'utilisateurs via la classe UserType :

  1. COMPANY - Pour les entreprises ou organisations
  2. ACCOUNTANT - Pour les experts-comptables

  Voici les valeurs attendues pour le champ "Type d'utilisateur" :

  - COMPANY - Si vous créez un compte pour une entreprise
  - ACCOUNTANT - Si vous créez un compte pour un expert-comptable

  Donc lorsque vous créez un superutilisateur, vous devez choisir l'une de ces deux valeurs. Pour un administrateur
   du système, je vous recommande d'utiliser COMPANY.