# Gaboma Hub sur le cluster K3s OVHcloud

Cible : **https://hub.gabomazone.com**. Préparation uniquement : aucun accès au VPS,
aucune modification DNS ni installation dans le cluster n'ont été effectués.

## Architecture et choix

Namespace `gaboma-hub`, PostgreSQL dédié (10 Gio), Redis privé, Django/Gunicorn
et serveur de médias Nginx dans le même pod (volume de 5 Gio). Les fichiers
statiques sont servis par WhiteNoise. Aucun NodePort, hostPort ou nouveau
LoadBalancer : l'Ingress rejoint le contrôleur déjà utilisé par vos autres apps.

Les fichiers JSON sont des manifests Kubernetes standards. Le choix initial est
`ingressClassName: traefik`, habituel sous K3s. Le contrôleur est supposé dans
`kube-system` ; ajuster `ingress.json` et la règle `hub-gateway` de `infra.json`
si votre installation utilise un autre contrôleur/namespace. Ne pas installer
un second contrôleur ni modifier celui des autres applications.

La classe de stockage par défaut du cluster est utilisée. Vérifier qu'elle
convient avant l'installation. Un seul exemplaire de chaque service et une
stratégie Recreate évitent les accès concurrents aux disques ReadWriteOnce.
Une mise à jour peut donc occasionner une courte interruption. Ce profil VPS
n'est pas une architecture haute disponibilité. Pour plusieurs réplicas web,
prévoir d'abord un stockage média partagé/S3 et une base gérée/répliquée.

## Préparation du cluster (opérateur)

1. Vérifier `kubectl config get-contexts`, `kubectl get ingressclass`,
   `kubectl get storageclass` et les ressources disponibles sur les nœuds.
   Les limites cumulées sont environ 2,2 Gio de mémoire ; conserver de la marge
   pour K3s et les autres applications.
2. Faire pointer l'enregistrement DNS A `hub.gabomazone.com` vers l'adresse
   publique du VPS (AAAA seulement si IPv6 fonctionne). Conserver les autres DNS.
3. Créer le namespace :

   ```sh
   kubectl --context CONTEXTE_OVH apply -f deploy/k8s/namespace.json
   ```

4. Préparer un fichier de secrets **hors du dépôt**, par exemple
   `/etc/gaboma-hub/secrets.env`, protégé en mode 600, à partir de
   `secrets.env.example`. Générer SECRET_KEY et POSTGRES_PASSWORD distincts
   (`python3 -c 'import secrets; print(secrets.token_hex(32))'`). Reporter le
   même mot de passe hexadécimal dans DATABASE_URL. Utiliser les identifiants
   de paiement **production** : les identifiants récupérés localement sont
   actuellement en environnement sandbox. Renseigner le SMTP.

   ```sh
   kubectl --context CONTEXTE_OVH -n gaboma-hub create secret generic hub-secrets \
     --from-env-file=/etc/gaboma-hub/secrets.env
   ```

   Ne pas changer POSTGRES_PASSWORD sans rotation effective dans PostgreSQL :
   l'image ne reconfigure pas le mot de passe d'une base déjà initialisée.

5. Fournir le certificat TLS `hub-tls` dans ce namespace. Si cert-manager est
   déjà présent, ajouter à l'Ingress l'annotation `cert-manager.io/cluster-issuer`
   avec le **nom réel de votre issuer**, puis appliquer l'Ingress et attendre
   l'émission du certificat avant de lancer le déploiement. Ne pas créer un
   issuer global arbitraire. Sinon importer un certificat couvrant le domaine :

   ```sh
   kubectl --context CONTEXTE_OVH -n gaboma-hub create secret tls hub-tls \
     --cert=/CHEMIN/fullchain.pem --key=/CHEMIN/privkey.pem
   ```

   Prévoir son renouvellement. Le DNS et les challenges ACME doivent fonctionner.
6. Publier l'image testée via le workflow CI (tag v*) et récupérer son digest GHCR.
   Si l'image est privée, créer un secret registry dans le namespace et ajouter
   `imagePullSecrets` dans les specs des pods `web.json` et `migration.json`.
   Aucun identifiant registry n'est intégré aux manifests.

## Déployer depuis un poste autorisé

```sh
python3 deploy/k8s/deploy.py --context CONTEXTE_OVH \
  --image ghcr.io/ORGANISATION/DEPOT@sha256:DIGEST_COMPLET
```

Le script attend PostgreSQL/Redis, exécute un Job de migrations avec l'image
choisie, attend son succès, déploie le web, puis applique l'Ingress. Il s'arrête
sur une erreur de migration. `--render` génère les manifests sans connexion.
Ne pas lancer plusieurs déploiements manuels en parallèle.

Créer ensuite un vrai administrateur (le compte local admin/admin n'est jamais
créé en production) :

```sh
kubectl --context CONTEXTE_OVH -n gaboma-hub exec -it deploy/hub-web -c web -- python manage.py createsuperuser
kubectl --context CONTEXTE_OVH -n gaboma-hub exec deploy/hub-web -c web -- python manage.py check --deploy --fail-level WARNING
curl --fail https://hub.gabomazone.com/health/ready/
```

Vérifier accueil, connexion admin, upload logo/bannière et lecture des médias,
soumission, paiement contrôlé et publication. Configurer la notification de
paiement sur `https://hub.gabomazone.com/paiements/singpay/callback/` selon le
contrat du prestataire. Les retours navigateur utilisent PUBLIC_BASE_URL.
Tester le paiement réel explicitement avant ouverture commerciale.

## GitHub Actions

Le dépôt GitHub doit avoir le contenu de GabomaHub_Django à sa racine. Le workflow
`deploy-k3s.yml` est manuel et attend une image immuable déjà testée.
Configurer l'environnement GitHub `production` (approbation recommandée), un
runner Linux dédié étiqueté `k3s-hub` avec Python/kubectl et accès privé au cluster,
et le secret d'environnement `HUB_KUBECONFIG`. Utiliser une identité limitée au
namespace, autorisée à gérer les ressources fournies et à lire les secrets requis,
pas le kubeconfig administrateur global de K3s. Précréer le namespace.
Ne jamais exécuter les jobs de PR non fiables sur ce runner.

## Sauvegarde et retour arrière

Avant une mise à jour, sauvegarder PostgreSQL et médias hors du VPS :

```sh
kubectl --context CONTEXTE_OVH -n gaboma-hub exec deploy/hub-db -- pg_dump -U hub -d hub -Fc > hub.dump
kubectl --context CONTEXTE_OVH -n gaboma-hub exec deploy/hub-web -c web -- tar -czf - -C /app media > hub-media.tar.gz
```

Suspendre temporairement les écritures pour une sauvegarde cohérente des deux.
Planifier ces sauvegardes et tester la restauration sur une base séparée. Les
volumes persistants ne remplacent pas une sauvegarde, surtout avec local-path.
Ne pas supprimer le namespace/PVC pour mettre à jour.

En cas de régression applicative, `kubectl ... rollout undo deployment/hub-web`
restaure le pod précédent, **pas le schéma ni les données**. Vérifier la
compatibilité des migrations ; sinon restaurer les sauvegardes pendant une
fenêtre de maintenance. Inspecter `kubectl ... get jobs` et les logs du Job
de migration en échec avant toute nouvelle tentative.

Références : [K3s réseau/Ingress](https://docs.k3s.io/networking/networking-services),
[Kubernetes stockage persistant](https://kubernetes.io/docs/concepts/storage/persistent-volumes/).
