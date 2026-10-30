# Gaboma Hub sur le cluster

Ce guide s'enchaîne après le guide Wayizé (`docs/premier-cluster.md` du dépôt Wayizé). On le lit de haut en bas. Les numéros 1 à 9 sont ceux de Gaboma Hub. Ils ne reprennent pas les numéros du guide Wayizé.

Dans le terminal, on ne colle que le contenu d'un bloc de commandes (le cadre gris). Les titres, les phrases et les lignes « Ça a marché si » ne sont pas des commandes.

Wayizé publie un frontal et garde une API sur le réseau interne. Gaboma Hub n'a pas ce second processus : les pages, `/admin/` et le callback SingPay sont le même Django. La règle est la même. Seul le site a un Ingress. Redis n'en a pas.

Les manifests `deploy/k8s/*.json` décrivent une autre préparation, avec un Postgres à part. Ici, on utilise le Postgres déjà lancé pour Wayizé.

## Avant l'étape 1

Sur le VPS, une seule fois, le guide Wayizé a déjà fait :

- les étapes 1 à 7 (SSH, système, k3s, kubectl, Traefik, cert-manager, Let's Encrypt) ;
- l'étape 10.2 (le Postgres du namespace `donnees`).

Vérifiez, puis restez dans ce document :

```bash
kubectl get nodes
kubectl get clusterissuer letsencrypt
kubectl -n donnees get deploy postgres
```

Ça a marché si le nœud est `Ready`, l'émetteur `letsencrypt` est `True`, et le déploiement `postgres` existe. Sinon, terminez ces étapes dans le guide Wayizé, puis revenez ici à l'étape 1.

Les commandes se lancent sur le VPS. Si `whoami` affiche `root`, enlevez `sudo`.

| Processus | Rôle | Publié sur Internet |
| --- | --- | --- |
| `hub-web` | Le site. Gunicorn en local dans le pod, nginx sert `/media/` (logos, bannières). WhiteNoise sert `/static/`. | Oui, `hub.gabomazone.com` |
| `redis` | Cache et sessions | Non |

La base s'appelle `hub`. L'application lit `DATABASE_URL`. Le disque `hub-media` (2 Gio) est monté sur `/app/media`. L'utilisateur du conteneur est `hub`, uid 10001.

## 1. Namespace

```bash
kubectl create namespace hub
kubectl get namespaces
```

Ça a marché si `hub` apparaît.

## 2. Nom de domaine

Même IPv4 que Wayizé. Dans la zone `gabomazone.com`, une entrée `A` pour `hub`, pas un `CNAME` en plus. Si cette entrée existe déjà et pointe ailleurs, changez sa cible vers l'IPv4 du VPS.

```bash
dig +short hub.gabomazone.com
dig +short wayize.gabomazone.com
```

Ça a marché si les deux commandes affichent la même adresse.

## 3. Base de données

```bash
APP_PW=$(python3 -c "import secrets; print(secrets.token_urlsafe(24))")
kubectl -n donnees exec -i deploy/postgres -- psql -U postgres -v ON_ERROR_STOP=1 <<SQL
CREATE USER hub WITH PASSWORD '${APP_PW}';
CREATE DATABASE hub OWNER hub;
SQL
```

Gardez `APP_PW` jusqu'à l'étape 5. Si l'utilisateur existe déjà, ne relancez pas le `CREATE`.

Ça a marché si `psql` répond deux fois `CREATE`.

## 4. Image

Faites le choix A ou le choix B, pas les deux. Notez la lettre : elle revient aux étapes 6 et 9.

Le dépôt doit contenir `deploy/k8s/cluster/` et le `Dockerfile`. Poussez-les sur `main` avant de cloner. Le workflow `ci.yml` déjà présent publie une étiquette `v*` après les tests. Le choix A publie en plus l'étiquette `main`, celle du cluster.

### Choix A — GitHub Actions

```bash
sudo mkdir -p /srv/hub
sudo chown "$USER:$USER" /srv/hub
git clone https://github.com/Stevy64/Gaboma-Hub.git /srv/hub
cd /srv/hub
mkdir -p .github/workflows
cp deploy/hub-image.yml .github/workflows/hub-image.yml
git add .github/workflows/hub-image.yml
git commit -m "Build the Gaboma Hub image on GHCR."
git push origin main
```

Si `git push` demande un mot de passe, c'est un jeton GitHub. Ne l'écrivez pas dans le dépôt.

L'onglet Actions doit devenir vert. L'image s'appelle `ghcr.io/stevy64/gaboma-hub`, étiquette `main`. Rendez le paquet public, puis :

```bash
sudo k3s ctr images pull ghcr.io/stevy64/gaboma-hub:main
```

Ça a marché si la commande se termine sans `unauthorized`.

Si le paquet reste privé :

```bash
read -rs GHCR_TOKEN
kubectl -n hub create secret docker-registry ghcr \
  --docker-server=ghcr.io \
  --docker-username=Stevy64 \
  --docker-password="$GHCR_TOKEN"
unset GHCR_TOKEN
```

Ajoutez `imagePullSecrets: [{name: ghcr}]` sous `spec.template.spec` du Deployment et du Job. Passez à l'étape 5.

### Choix B — Construire sur le VPS

```bash
sudo apt install -y docker.io
sudo mkdir -p /srv/hub
sudo chown "$USER:$USER" /srv/hub
if [ ! -d /srv/hub/.git ]; then
  git clone https://github.com/Stevy64/Gaboma-Hub.git /srv/hub
fi
cd /srv/hub
git pull --ff-only
sudo docker build -t gaboma-hub:1 .
sudo docker save gaboma-hub:1 | sudo k3s ctr images import -
sudo k3s ctr images ls | grep gaboma-hub
```

Ça a marché si `grep` affiche `docker.io/library/gaboma-hub:1`.

Passez à l'étape 5. À l'étape 6, la commande sera `hub-deploy local`.

## 5. Variables

`DEBUG=false` sans `SECRET_KEY` empêche le démarrage. `SECURE_SSL_REDIRECT=true` marque les cookies comme sûrs. Les sondes `/health/live/` et `/health/ready/` ne sont pas redirigées. `TRUST_PROXY_HEADERS=true` fait lire `X-Forwarded-Proto`. `/health/ready/` interroge la base et Redis.

```bash
WEB_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(48))")
sudo mkdir -p /etc/hub
sudo tee /etc/hub/app.env >/dev/null <<EOF
DEBUG=false
SECRET_KEY=${WEB_KEY}
ALLOWED_HOSTS=hub.gabomazone.com,localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=https://hub.gabomazone.com
PUBLIC_BASE_URL=https://hub.gabomazone.com
TRUST_PROXY_HEADERS=true
SECURE_SSL_REDIRECT=true
DATABASE_URL=postgresql://hub:${APP_PW}@postgres.donnees.svc.cluster.local:5432/hub?sslmode=disable
REDIS_URL=redis://redis:6379/0
EOF
sudo chmod 600 /etc/hub/app.env
unset WEB_KEY APP_PW
sudo k3s kubectl -n hub create secret generic hub --from-env-file=/etc/hub/app.env
```

Ça a marché si `kubectl -n hub get secrets` liste `hub`.

Le site s'ouvre sans SingPay. Avant d'encaisser, ajoutez les clés de production dans `/etc/hub/app.env` (les noms sont dans `deploy/cluster.env.example`), supprimez le Secret, recréez-le, puis refaites l'étape 9. Le callback à déclarer est `https://hub.gabomazone.com/paiements/singpay/callback/`.

L'e-mail se pose de la même façon. Sans `EMAIL_HOST`, Django écrit le message dans les journaux du pod.

## 6. Lancer

```bash
sudo install -m 755 /srv/hub/deploy/k8s/cluster/update.sh /usr/local/bin/hub-deploy
```

Si vous avez choisi A à l'étape 4 :

```bash
hub-deploy
```

Si vous avez choisi B à l'étape 4 :

```bash
hub-deploy local
```

Le script attend Redis, joue la migration, puis lance le site. Si la migration échoue, il s'arrête.

```bash
kubectl -n hub logs job/hub-migrate
```

Ça a marché si la commande se termine sans erreur.

## 7. Vérifier

```bash
kubectl -n hub get certificate
curl -fsS https://hub.gabomazone.com/health/ready/
```

Ça a marché si `hub-tls` est `READY` = `True` et si `curl` affiche `"status": "ok"`.

S'il reste `False` : `kubectl -n hub describe certificate hub-tls`.

## 8. Compte administrateur

Aucun compte de démonstration n'est créé.

```bash
kubectl -n hub exec -it deploy/hub-web -c gunicorn -- python manage.py createsuperuser
```

Le catalogue de référence, si vous le voulez :

```bash
kubectl -n hub exec deploy/hub-web -c gunicorn -- python manage.py seed_hub
```

Ouvrez `https://hub.gabomazone.com/` puis `https://hub.gabomazone.com/admin/`.

```bash
kubectl -n hub logs deploy/hub-web -c gunicorn
```

## 9. Mettre à jour

### Si vous aviez choisi A

Quand le job Actions est vert :

```bash
cd /srv/hub
git pull --ff-only
hub-deploy
curl -fsS https://hub.gabomazone.com/health/ready/
```

Pour revenir à un commit, remplacez `:main` par le SHA du job, dans le Job et dans le conteneur gunicorn, puis appliquez les manifests.

### Si vous aviez choisi B

```bash
cd /srv/hub
git pull --ff-only
sudo docker build -t gaboma-hub:1 .
sudo docker save gaboma-hub:1 | sudo k3s ctr images import -
hub-deploy local
curl -fsS https://hub.gabomazone.com/health/ready/
```

## À ne pas faire

- Refaire les étapes 1 à 7 du guide Wayizé, ni installer un second Postgres.
- Publier 8000 ou 6379.
- Activer `ufw`.
- Commiter `/etc/hub/app.env`, ou réutiliser le Secret `wayize`.
- Lancer `hub-deploy` sans `local` si l'image a été construite sur le VPS.
- Relancer `CREATE USER` si la base existe déjà.
- Supprimer le disque `hub-media` pour mettre à jour : les logos et les bannières y sont.
