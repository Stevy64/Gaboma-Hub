# Exploitation DevOps de Gaboma Hub

## Architecture

Une application Django conteneurisée et des services d'infrastructure séparés :
- `web` : Gunicorn, utilisateur non-root, statiques versionnés servis par WhiteNoise.
- `db` : PostgreSQL 16, volume persistant, aucun port public.
- `redis` : cache partagé et sessions `cached_db` (source durable en PostgreSQL). Le cache est jetable, limité à 128 Mo et non exposé.
- `migrate` : tâche ponctuelle ; échec des migrations = démarrage web bloqué.
- `proxy` : Caddy, HTTPS et renouvellement des certificats ; médias en lecture seule.

Le code métier reste dans Django. Il ne s'agit pas d'un découpage artificiel en microservices métier et aucun worker Celery inutile n'est démarré.

## Développement

Prérequis : Docker Desktop avec moteur Linux, Compose v2 récent ; GNU Make sous WSL/Linux, ou PowerShell sous Windows. Dans le dossier du projet :

```sh
make dev
make superuser-dev
make test
make logs-dev
make stop-dev
```

Sous Windows, équivalents : `./devops.ps1 dev`, `./devops.ps1 test`, etc.
Accès : http://localhost:8010 (le serveur local historique reste sur 8000).
Le code est monté pour rechargement automatique. Base Docker distincte de la base SQLite existante. Aucun compte administrateur ni paiement réel créé automatiquement.
Pour remplir le catalogue de référence : `docker compose -f compose.dev.yaml exec web python manage.py seed_hub`.

## Production sur VPS

Le cluster k3s déjà utilisé par Wayizé est décrit dans [docs/ovh-cluster.md](docs/ovh-cluster.md). Le reste de cette section est le chemin Docker Compose sur une machine vide.

1. Installer Docker/Compose et copier le projet, ou le cloner dans un dépôt dédié.
2. Copier `.env.production.example` vers `.env.production`. Générer deux secrets distincts avec `python -c "import secrets; print(secrets.token_hex(32))"` : `SECRET_KEY` et `POSTGRES_PASSWORD` (hex pour compatibilité URL).
3. Renseigner le vrai domaine et l'adresse ACME. Pointer le DNS vers le VPS et autoriser les ports 80/443. Ces prérequis ne sont pas configurés par le projet.
4. Renseigner les paramètres SMTP et SingPay selon `.env.example`. Le modèle reste volontairement en sandbox ; basculer après vérification du contrat marchand et des webhooks.
5. Exécuter `make prod`, `make check`, puis `make superuser`. PowerShell : mêmes noms de tâches.

Caddy définit les en-têtes de proxy fiables ; Gunicorn n'est pas exposé directement. Ne pas publier son port avec `TRUST_PROXY_HEADERS=true`. Ne pas réutiliser les paramètres dev en production. Les sessions et cookies sécurisés nécessitent HTTPS.

`make stop-prod` conserve les volumes. Aucun raccourci ne supprime les données.

## GitHub Actions et publication

**Mettre le contenu de GabomaHub_Django à la racine d'un dépôt dédié**, avec `.github/workflows/ci.yml`. Aucun dépôt distant n'a été créé ou modifié par cette préparation.

- Pull request, push sur `main`, déclenchement manuel : configuration Compose, construction Docker, tests sur PostgreSQL/Redis, migrations manquantes, contrôles Django production et démarrage Gunicorn.
- Tag `v*` (exemple `v1.0.0`) : après succès des tests, publication GHCR sous `ghcr.io/proprietaire/depot:v1.0.0` et `sha-COMMIT`, avec provenance/SBOM.
- Autoriser GitHub Actions et l'écriture des packages pour le workflow. Le `GITHUB_TOKEN` fourni par GitHub suffit au workflow. Pour un package privé, le serveur devra être connecté à GHCR avec un accès de lecture.

Aucun déploiement automatique vers un serveur inconnu. Sur le VPS : sauvegarder, définir `HUB_IMAGE` avec le tag immuable souhaité dans `.env.production`, puis `make deploy`. Les migrations sont exécutées avant le redémarrage. Une migration compatible avec l'ancienne version est nécessaire pendant cette courte transition ; planifier une maintenance pour une migration incompatible. Ce Compose mono-hôte ne garantit pas le zéro interruption.

## Supervision et sauvegardes

- `/health/live/` : processus HTTP ; `/health/ready/` : connexion SQL et lecture/écriture cache. Réponses génériques sans secrets. Ces deux routes restent accessibles en HTTP pour les sondes internes.
- `make ps`, `make logs-prod` : état et journaux stdout/stderr.
- `make backup` : `hub-backup.dump` et `hub-media-backup.tar.gz` dans le dossier courant. Ces noms sont écrasés à la sauvegarde suivante : archiver avec date, chiffrer et copier hors du serveur. Les fichiers sont exclus de Git et des images Docker.
- Pour une sauvegarde cohérente des médias et de la base, mettre le site en maintenance et arrêter `web` pendant les deux exports. Les volumes PostgreSQL, médias et certificats ne doivent jamais être supprimés par `down -v` en production.

Restaurer d'abord dans un environnement isolé : copier le dump dans le conteneur DB (`docker compose ... cp hub-backup.dump db:/tmp/restore.dump`), puis `pg_restore -U hub -d hub --clean --if-exists /tmp/restore.dump` avec le site arrêté. Cette commande remplace les données existantes : sauvegarder avant et vérifier le projet Compose ciblé. Restaurer l'archive médias dans `/app/media`, vérifier droits UID/GID 10001, puis redémarrer et contrôler les sondes, connexion et images.

Retour arrière : remettre l'ancien tag d'image, mais ne pas supposer qu'il accepte la nouvelle base. Les migrations inverses/restaurations nécessitent une procédure testée. Les secrets restent uniquement sur le serveur ; ne jamais publier `.env*`, SQLite ou médias dans GHCR.

## Références

- https://docs.docker.com/compose/how-tos/startup-order/
- https://docs.djangoproject.com/en/5.2/ref/settings/#secure-proxy-ssl-header

HSTS couvre le hub pendant un an. Les avertissements Django W005/W021 sont volontairement exclus du contrôle bloquant : inclure tous les sous-domaines et demander le preload doivent rester un choix explicite du propriétaire du domaine. Les variables SECURE_HSTS_INCLUDE_SUBDOMAINS et SECURE_HSTS_PRELOAD permettent ce choix.

## Validation locale du 28 octobre 2026

Image construite avec succès ; services dev Django/PostgreSQL/Redis healthy ; 63 tests passent sur SQLite et PostgreSQL/Redis ; aucune migration manquante ; contrôle Django production passé (W005/W021 exclus volontairement, voir ci-dessus) ; Gunicorn sert accueil et CSS avec HTTP 200 et readiness OK. Les deux fichiers Compose et la syntaxe PowerShell ont été validés. HTTPS public, publication GHCR et exécution sur GitHub restent à vérifier dans le dépôt et sur le domaine de destination.
