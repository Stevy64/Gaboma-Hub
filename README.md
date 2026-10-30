# Gaboma Hub pour Django

Un annuaire d'applications ouvert aux projets Gaboma **et aux applications d'autres éditeurs**,
avec une interface mobile bleu, blanc et orange. Le catalogue, les comptes, les favoris,
les soumissions, la modération et les paiements sont gérés côté Django et stockés en base.
Le JavaScript améliore seulement le confort de navigation ; il ne gère aucune autorisation.

La direction visuelle est désormais éditoriale : fond clair chaleureux, encre marine, accents
cuivrés, illustration de marque, en-têtes hiérarchisés et séparateurs numérotés. Le Hero met
une application réelle en vitrine. Les principes de présentation sont décrits dans `DESIGN.md`.

## Découverte des créateurs gabonais, médias et avis

L'accueil met en avant les applications récentes et les créateurs gabonais, avec un catalogue
triable par nouveauté ou par note moyenne. Les notes et compteurs proviennent de vrais avis
en base ; aucun avis, chiffre d'audience ou témoignage de démonstration n'est ajouté.

Chaque nouvelle application demande un **logo et une bannière**, côté utilisateur comme dans
l'administration. La fiche comporte aussi le nom de son créateur ou de son équipe, sa ville
(facultative), une présentation courte et un texte complet. Les anciennes fiches restent
consultables avec un visuel de remplacement jusqu'à l'ajout de leurs médias.

- Logo conseillé : 512 × 512 px. Bannière conseillée : 1600 × 900 px.
- Formats reçus : JPG, PNG ou WebP ; 5 Mo par fichier, 20 millions de pixels maximum.
- Les images sont contrôlées et réencodées en WebP, sans leurs métadonnées d'origine.
- Les médias publics sont enregistrés dans `media/applications/` sous des noms aléatoires.
- Le formulaire permet d'apercevoir les médias choisis avant de les enregistrer.

Une personne connectée peut laisser une **note de 1 à 5** et un commentaire facultatif de
2 000 caractères maximum. Elle peut modifier ou supprimer son avis. Un seul avis est conservé
par personne et par application. Les commentaires sont affichés comme du texte, sans HTML actif.
Les fiches présentent la moyenne, la répartition des étoiles et des pages de dix avis.
Les cœurs servent aux favoris ; les étoiles servent aux notes.

Dans `/admin/`, la rubrique **Avis** permet de masquer ou de réafficher les avis. Un avis masqué
est exclu de la moyenne et du catalogue ; son auteur ne peut pas le réafficher en le modifiant.
La mise en avant gabonaise n'est pas une certification d'origine ou d'identité du créateur :
la modération doit vérifier les informations de la fiche avant publication.

**Sauvegardes :** conserver ensemble `db.sqlite3` et le dossier `media/`. Ces données locales
et les clés privées sont exclues de l'archive de sources. Les médias sont servis automatiquement
en développement (`DEBUG=True`). Pour un futur hébergement, configurer également un service
de fichiers pour `/media/` ; `collectstatic` concerne seulement les styles et scripts.

## Affichage, image du Hero et publicités

Le sélecteur **Grille 1 × 2 / Liste** se trouve au-dessus de la recherche. La grille affiche
deux applications par ligne, y compris sur smartphone. La liste affiche des lignes compactes.
Le basculement est immédiat avec JavaScript et le choix est mémorisé dans le navigateur.
Sans JavaScript, les liens restent fonctionnels et Django conserve le choix dans la session.
Les recherches, catégories, favoris et tris restent utilisables dans les deux modes.

Les cartes regroupent le visuel, le logo, le nom, la catégorie et la note dans un format court.
Le nom et le visuel ouvrent la fiche détaillée ; l'action « Ouvrir » donne un accès direct à
l'application quand son adresse est connue. Les descriptions complètes restent dans les fiches.

L'accueil propose des **carrousels tactiles** : applications disponibles, projets dont le lien
reste à compléter, puis applications appréciées dès que de vrais avis visibles existent.
Défilement au doigt, boutons précédent/suivant et navigation au clavier sont pris en charge.
La recherche et les favoris restent centrés sur leurs résultats, sans carrousel non filtré.
Les catégories se parcourent aussi horizontalement.

L'interface utilise des icônes SVG locales, des transitions courtes, un indicateur de navigation
et un spinner lors de l'envoi d'un formulaire valide. Aucun délai artificiel n'est ajouté.
L'envoi répété est bloqué pendant une soumission et les commandes sont rétablies au retour
arrière. Les champs de mot de passe disposent d'une commande afficher/masquer ; les zones de
texte avec limite affichent leur compteur de caractères. Les préférences de réduction des
animations du système sont respectées. Ces améliorations utilisent les fonctions natives du
navigateur et ne nécessitent aucune nouvelle bibliothèque JavaScript.

Dans l'administration :

1. **Apparence de l'accueil → Ajouter** : choisissez l'image de fond du Hero. Un seul réglage
   global est créé ; utilisez ensuite **Modifier** pour le remplacer. Décochez « Activer l'image
   de fond » pour revenir au fond clair, ou effacez l'image. Le voile clair est automatique afin
   de conserver la lisibilité. Format conseillé : 1920 × 1080 px.
2. **Publicités → Ajouter** : renseignez le titre, l'annonceur facultatif, le visuel et le lien
   de destination facultatif. Choisissez l'emplacement sous le Hero ou sous le catalogue.
3. Activez la publicité. Sans dates, elle est diffusée tant qu'elle est activée. Sinon,
   renseignez début et/ou fin. La fin est exclusive : l'annonce disparaît à l'heure indiquée.
   L'ordre croissant permet de classer plusieurs annonces. Les dates de l'administration
   suivent le fuseau configuré dans Django, actuellement `Africa/Libreville`.

Les publicités portent la mention « Publicité », utilisent des images contrôlées et ne
chargent aucun script de régie externe. Les liens s'ouvrent dans un nouvel onglet.
Format conseillé : 1600 × 500 px ; le visuel entier reste visible sur mobile.
Comme pour les médias des applications, JPG, PNG et WebP sont acceptés (5 Mo maximum),
réencodés en WebP et sauvegardés dans `media/`. Aucun visuel de campagne ou fond de Hero
n'est ajouté par défaut : vous choisissez votre propre contenu dans l'administration.

## Démarrer en local

Prérequis : Python 3.10 minimum, de préférence Python 3.12 ou 3.13. Une connexion Internet
est nécessaire pour la première installation des dépendances. SQLite est fourni avec Python.
Aucun Node.js, npm, Redis, Docker ni abonnement d'hébergement n'est nécessaire.

Dans un terminal ouvert dans ce dossier, sous Windows :

```powershell
py -3 start.py --admin
```

Sous macOS ou Linux :

```sh
python3 start.py --admin
```

Le lanceur prépare `.venv`, installe les dépendances, crée les tables, initialise les six
applications du catalogue, vous demande de choisir **vos propres identifiants administrateur**,
puis démarre le serveur. Le mot de passe saisi dans le terminal ne s'affiche pas.

- Hub : http://127.0.0.1:8000/
- Administration : http://127.0.0.1:8000/admin/
- Création d'un compte utilisateur : http://127.0.0.1:8000/inscription/
- Espace personnel : http://127.0.0.1:8000/mon-espace/

Pour les prochains lancements, ne recréez pas l'administrateur :

```powershell
py -3 start.py
```

Si le port est occupé : `py -3 start.py --port 8005`.
Ctrl+C arrête le serveur ; les données restent dans `db.sqlite3`.
`start.ps1 -CreateAdmin` est une autre entrée possible si les scripts PowerShell sont autorisés
sur votre ordinateur. Aucun changement de politique PowerShell n'est requis : utilisez `start.py`
si un script est bloqué.

### Préparation manuelle

```powershell
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe manage.py migrate
.venv\Scripts\python.exe manage.py seed_hub
.venv\Scripts\python.exe manage.py createsuperuser
.venv\Scripts\python.exe manage.py runserver
```

Sous macOS/Linux, remplacez `.venv\Scripts\python.exe` par `.venv/bin/python`.
`requirements-lock.txt` fournit les versions effectivement utilisées pour la recette.
Pour reproduire exactement cet environnement, installez ce fichier à la place de `requirements.txt`.

## Deux façons d'ajouter une application

### Administration sans paiement

1. Connectez-vous à `/admin/` avec votre administrateur.
2. Ouvrez **Applications → Ajouter**.
3. Renseignez la fiche, une catégorie, son adresse publique et son apparence.
4. L'état **Publiée** rend la fiche visible immédiatement.

Une fiche créée dans cette administration est identifiée comme un ajout gratuit de l'admin.
Les trois adresses encore inconnues — GabomaMarket, Gabomazone SaaS et GabomaPass — peuvent
être complétées ici. Les adresses connues de Fallaman, Zanalyze et Gab Event sont déjà renseignées.

### Utilisateur avec paiement au tarif administrable

1. Le visiteur crée un compte ou se connecte.
2. Il sélectionne **Proposer**, décrit l'application et son adresse. Il peut référencer
   une application d'un autre éditeur ; le compte représente le déposant, pas une preuve de propriété.
3. Une fiche privée **À finaliser** est créée. Rien n'est encore publié ou encaissé.
4. Il confirme le tarif enregistré sur sa fiche (**2 000 FCFA par défaut**) et est redirigé vers SingPay.
5. SingPay traite le règlement sur sa propre interface.
6. Django vérifie le paiement auprès du prestataire. La fiche passe **En validation**.
7. L'administrateur examine puis publie la fiche, ou demande des corrections.

Le paiement n'est pas un abonnement et ne déclenche pas une publication automatique.
Une fiche payée renvoyée pour correction peut être corrigée puis resoumise sans payer à nouveau.
Les fiches publiées ou en examen restent figées pour éviter des changements de liens non modérés.
L'administrateur peut les modifier ou les archiver.

Un refus n'entraîne **pas de remboursement automatique**. Le traitement d'un remboursement
éventuel se fait auprès de SingPay par l'administrateur, selon la politique qu'il définit et
communique aux déposants. Ce projet ne contient pas de bouton de remboursement fictif.

## Configurer SingPay

L'intégration reprend le client utilisé dans le projet Fallaman fourni : paiement externalisé
par `POST /v1/ext`, puis vérification serveur par référence ou identifiant. Elle ne réutilise
**aucun secret** de Fallaman automatiquement et ne modifie pas son portefeuille ou sa callback.

1. Copiez `.env.example` en `.env` dans ce dossier.
2. Renseignez localement les valeurs de votre Workspace SingPay :

```dotenv
SINGPAY_API_KEY=
SINGPAY_API_SECRET=
SINGPAY_MERCHANT_ID=
SINGPAY_DISBURSEMENT_ID=
SINGPAY_ENVIRONMENT=sandbox
SINGPAY_WEBHOOK_SECRET=
PUBLIC_BASE_URL=http://127.0.0.1:8000
```

3. Redémarrez Django.
4. Configurez la notification dans le Workspace SingPay :

```text
https://votre-domaine-public/paiements/singpay/callback/
```

La callback est configurée dans le portefeuille SingPay, pas dans le corps `/ext`, conformément
au contrat utilisé par Fallaman. Pour deux applications différentes, prévoyez un portefeuille
et une callback dédiés, ou confirmez auprès de SingPay la configuration à utiliser avant de toucher
un portefeuille déjà en production. N'écrasez pas la callback de Fallaman pour tester ce hub.

### Cas du localhost

SingPay ne peut pas appeler `127.0.0.1` sur votre ordinateur. Pour tester les callbacks, il faut
une URL HTTPS de développement joignable depuis Internet. `PUBLIC_BASE_URL`, `ALLOWED_HOSTS`
et `CSRF_TRUSTED_ORIGINS` doivent correspondre à cette URL si vous utilisez un accès public.
Ne rendez pas public le serveur de développement avec de vrais comptes ou secrets de production.

Le retour navigateur et le bouton **Vérifier mon paiement** interrogent aussi SingPay côté serveur.
Leur fonctionnement dépend des URL de retour acceptées par votre configuration SingPay et de
l'accès réseau sortant de votre ordinateur. Sans clé configurée, la soumission reste enregistrée
mais le règlement est indisponible ; aucun paiement simulé ne peut donner droit à une publication.

### Confirmation et reprise

- Signature HMAC obligatoire sur les notifications, puis confirmation serveur indépendante.
- Montant attendu strictement égal au tarif enregistré sur le paiement, référence exacte et identifiant non réutilisable.
- Un simple paramètre `status=success` dans le navigateur n'accorde rien.
- Les notifications répétées sont idempotentes et ne republient pas une fiche archivée.
- Un double clic réutilise le paiement en attente au lieu d'initialiser un second encaissement.
- Une initialisation incertaine reste en attente : faire une vérification ou demander une revue
  au support SingPay avant d'envisager un nouvel essai. Ne pas changer son état en base pour forcer un débit.

Le format HMAC compatible est celui du client Fallaman :
`HMAC-SHA256(secret, timestamp + JSON trié compact)`, avec ses variantes de compatibilité.
Les horodatages reconnus et périmés sont refusés. Pour exiger un horodatage reconnu dans tous
les cas, activez `SINGPAY_WEBHOOK_REQUIRE_FRESH_TIMESTAMP=true` après avoir confirmé le format
réel fourni par votre compte. La confirmation API est obligatoire dans les deux modes.

Une commande permet de reprendre les contrôles sans créer de nouveaux débits :

```powershell
.venv\Scripts\python.exe manage.py reconcile_payments --limit 30
```

Dans l'admin, **Paiements SingPay → Revérifier** propose le même contrôle. Les paiements ne peuvent
pas être ajoutés, modifiés manuellement ou supprimés dans l'admin. Les notifications conservent
une référence et un résultat, pas un corps complet ni les identifiants secrets.

## Catalogue et personnalisation

- Recherche par nom, description ou catégorie.
- Catégories administrables.
- Fiches publiques seulement après publication.
- Favoris liés au compte, disponibles depuis plusieurs appareils utilisant la même base.
- Application externe ouverte dans un nouvel onglet.
- Icônes intégrées ou initiales, sans upload de SVG ou téléchargement automatique de logos.
- Interface utilisable sans JavaScript ; formulaire et recherche restent fonctionnels.

`seed_hub` est idempotente et ne remplace pas vos modifications. Elle ne crée aucun utilisateur.

## Structure

```text
GabomaHub_Django/
  manage.py
  start.py                      lanceur local Windows / macOS / Linux
  start.ps1                     alternative PowerShell
  requirements.txt
  requirements-lock.txt
  .env.example                  uniquement des exemples sans secrets
  config/                       réglages, routes principales, WSGI
  hub/
    models.py                   catalogue, favoris et paiements
    forms.py                    formulaires publics et inscription
    views.py                    parcours des utilisateurs et callback
    admin.py                    ajout gratuit, modération et vérification
    payments/                   client SingPay et logique de confirmation
    migrations/                 schéma prêt à appliquer
    management/commands/        initialisation et reprise des paiements
    tests.py                    recette automatisée sans argent réel
  templates/                    vues Django, authentification comprise
  static/hub/                   charte mobile, icônes et JavaScript léger
```

## Vérifier le projet

```powershell
.venv\Scripts\python.exe manage.py check
.venv\Scripts\python.exe manage.py test hub
.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
```

Les tests remplacent les appels SingPay par des réponses contrôlées. Ils vérifient notamment
la modération, les droits d'accès, les montants absents ou falsifiés, les références étrangères,
les signatures, l'idempotence et les retours navigateur trompeurs. Aucun encaissement réel n'est exécuté.
Un test de bout en bout avec votre portefeuille sandbox reste nécessaire avant d'accepter de l'argent réel.

## Données locales et accès administrateur

`db.sqlite3` conserve le catalogue, les utilisateurs, les favoris et les paiements. Sauvegardez ce
fichier serveur arrêté, ainsi que votre `.env`. Ne les publiez pas et ne les ajoutez pas à Git.
`.local-secret` est généré automatiquement pour les sessions locales si `SECRET_KEY` est vide.
Pour la production, `DEBUG=false` exige une vraie `SECRET_KEY` configurée dans l'environnement.

En local, les e-mails de réinitialisation sont affichés dans le terminal Django. Configurez un
backend SMTP réel avant d'en faire bénéficier d'autres utilisateurs. Les routes de réinitialisation
ne révèlent pas si l'adresse existe.

## Avant une ouverture au public

Ce dossier est préparé pour une utilisation locale. Pour une mise en production : serveur WSGI
adapté (pas `runserver`), HTTPS, `DEBUG=false`, secret indépendant, hôtes et CSRF explicitement
configurés, cookies sécurisés, courriels opérationnels, sauvegardes et test complet SingPay.
Un déploiement multi-utilisateur important doit aussi prévoir PostgreSQL, une limitation des
tentatives de connexion et de vérification des paiements, ainsi que la supervision adaptée.

La version Sites précédemment publiée demeure une maquette statique distincte. Ce dossier Django
fonctionne indépendamment et n'exige aucune connexion à ChatGPT pour son utilisation locale.

### Documentation de référence

- Django : https://docs.djangoproject.com/en/5.2/
- SingPay : https://client.singpay.ga/doc/reference/index.html
- Documentation d'intégration SingPay : https://github.com/singpay-ga/singpay-doc


## Gestion de la vitrine et des paramètres

Dans **Administration → Paramètres du Hub**, créez la configuration unique si elle n'existe pas encore :
- Tarif de référencement en FCFA, de 1 à 1 000 000 (2 000 par défaut).
- Accroche, titre, titre coloré et description de l'accueil.
- Activation de la vitrine et des carrousels de découverte.
- Image de fond du Hero et son activation.

Chaque nouvelle fiche enregistre le tarif courant côté serveur. Une modification du tarif n'affecte pas les fiches existantes, les corrections, ni les paiements déjà engagés. Les ajouts de l'administrateur restent gratuits. La configuration ne contient aucun secret SingPay : ceux-ci restent dans `.env`.

Dans **Administration → Publicités → Ajouter** :
1. Saisissez le titre, l'annonceur facultatif et téléversez le visuel (JPG/PNG/WebP, 5 Mo maximum).
2. Choisissez **En vitrine — carrousel du Hero**. Format conseillé : 1200 × 700 px ; l'image reste entière, sans recadrage.
3. Ajoutez un lien facultatif, l'ordre, les dates de diffusion facultatives, puis activez la publicité.
4. Répétez pour les autres diapositives. Les aperçus, l'ordre et l'activation sont accessibles dans la liste d'administration.

Les annonces désactivées, futures ou expirées sont exclues. La vitrine affiche les annonces actives, ou les applications disponibles quand aucune annonce n'est active. Défilement tactile et boutons précédent/suivant avec compteur, sans rotation automatique. Les autres emplacements publicitaires sont conservés.

Le catalogue présente une recherche directe, les catégories horizontales et un panneau **Filtres** repliable (catégorie et tri). **Appliquer** valide les réglages ; **Effacer les filtres** remet la recherche à zéro tout en conservant le mode favoris. Le mode grille/liste reste mémorisé.


## Docker et GitHub Actions

Voir [DEVOPS.md](DEVOPS.md) pour les services Docker, Redis, PostgreSQL, HTTPS, les commandes Makefile/PowerShell, la CI et les sauvegardes. Démarrage : `make dev` ou `./devops.ps1 dev`.


## Mode jour / nuit
Le bouton soleil/lune de l’en-tête change le thème du portail et mémorise le choix dans ce navigateur. Sans préférence enregistrée, le thème suit celui de l’appareil. Les cartes, menus, formulaires, états et navigation mobile possèdent une palette sombre dédiée ; les images conservent leurs couleurs. L’administration Django garde son propre sélecteur de thème.


## PWA et rapidité
Le Hub reste installable sur l’écran d’accueil. Les ressources d’affichage sont conservées sur le téléphone pour accélérer les visites, avec les préférences de l’utilisateur. Le catalogue et les opérations nécessitent Internet. Voir [PWA.md](PWA.md).


## Console d’administration locale

La console `/admin/` propose une navigation latérale, des indicateurs liés aux permissions et des listes/formulaires adaptés au mobile, inspirés de GabEvent. Pour créer le compte de démonstration demandé, exécuter `docker compose -f compose.dev.yaml exec web python manage.py create_local_admin`. Identifiants locaux : `admin` / `admin`. La commande refuse de fonctionner avec DEBUG=false et ne fait pas partie du démarrage automatique. En production, créer un compte distinct avec un mot de passe fort.

Le compte a été créé dans la base PostgreSQL Docker locale, pas dans les archives distribuées. La configuration de paiement locale est chargée depuis `.env`, exclu de Git, Docker et ZIP. Elle reprend l’environnement sandbox du projet source. L’accès marchand a répondu HTTP 200 en lecture seule ; aucun encaissement réel n’a été testé. Avant exploitation publique, fournir le domaine HTTPS de retour et vérifier les réglages de notification marchands. Les libellés clients utilisent Paiement Mobile, indépendamment du fournisseur technique.

## Administration mobile et suivi des dossiers

Depuis l’administration, ouvrir **Suivi des soumissions** (`/admin/hub/application/suivi/`). Les cartes et filtres permettent de suivre les fiches à finaliser, paiements en attente, validations, corrections, publications et archives. Chaque dossier regroupe fiche, tentatives de paiement, décision motivée et historique administratif. Les boutons sont adaptés au tactile, avec indicateur de traitement et respect du mouvement réduit.

**Vérifier et valider le paiement** interroge le prestataire : aucune confirmation manuelle fictive. Une publication exige un paiement confirmé au montant du dossier, ou un ajout gratuit administratif. Le contrôle du paiement et la publication restent deux actions distinctes. Les corrections et l’archivage exigent un motif affiché au créateur dans son suivi. Les décisions et vérifications faites depuis ce parcours sont journalisées avec leur auteur. Les anciennes décisions sans journal ne sont pas reconstituées ; la dernière décision connue reste affichée. Permissions Django : consultation des applications pour accéder au suivi, modification des applications pour modérer, modification des paiements pour vérifier.

## Administration mobile et production K3s

Le menu **Suivi des soumissions** ouvre les dossiers filtrés par étape : paiements en attente, validation, corrections et publication. Chaque dossier regroupe sa fiche, ses paiements, ses décisions motivées et son historique. Une vérification administrative interroge le prestataire : une validation manuelle est aussi disponible après contrôle effectif des fonds, avec justificatif, motif et identité de l’administrateur. Les permissions Django séparent consultation, modération et vérification des paiements.

La navigation mobile est fixe en bas de l’écran, les actions sont tactiles et le compte est accessible dans un menu compact.

Pour `hub.gabomazone.com` sur le VPS qui fait déjà tourner Wayizé, suivre [docs/ovh-cluster.md](docs/ovh-cluster.md) : namespace `hub`, Postgres partagé, deux façons de construire l'image (GitHub Actions ou `docker build` sur le VPS).

Le [guide K3s isolé](deploy/k8s/README.md) et les manifests JSON restent une autre préparation, avec un Postgres à part. Le profil Compose reste disponible. Aucun déploiement distant n'a encore été effectué.

### Validation manuelle et gestion des volumes
Dans Suivi des soumissions → Examiner le dossier → Paiements, ouvrir **Valider le paiement manuellement**. Renseigner la référence du reçu, le montant exact et le motif du contrôle, puis cocher la confirmation de réception. Cette option fonctionne aussi sans tentative en ligne. Elle ne réalise aucun transfert bancaire ; elle enregistre un encaissement constaté. La publication reste une décision distincte. Les références manuelles sont uniques et les actions historisées. Recherche étendue, catégorie, tri ancien/récent/nom, pagination 12/24/48 et retour à la liste filtrée facilitent le traitement.

### Compteurs de la section d’accueil
Les apps disponibles sont les fiches publiées possédant un lien. Les visiteurs cumulés sont comptés depuis l’activation, avec un identifiant aléatoire signé conservé un an dans le navigateur et seulement son empreinte SHA-256 en base. Actualiser ne recompte pas le navigateur. Les comptes staff et robots courants sont exclus. Aucun IP ni historique de navigation n’est enregistré. Effacer les cookies ou changer de navigateur crée un nouveau visiteur ; ce compteur ne constitue pas une mesure des personnes uniques et ne reconstruit pas les anciennes visites. La table persistante est incluse dans les sauvegardes PostgreSQL.
