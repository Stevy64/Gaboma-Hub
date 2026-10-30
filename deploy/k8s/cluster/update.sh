#!/bin/sh
# Met à jour Gaboma Hub sur le cluster déjà en place.
# hub-deploy         image GHCR (choix A, etape 4)
# hub-deploy local   image construite sur le VPS (choix B, etape 4)
# La migration passe avant le redémarrage. Si elle échoue, le site en service reste.
set -eu
MODE=${1:-ghcr}
if [ "$MODE" != ghcr ] && [ "$MODE" != local ]; then
  echo "usage: hub-deploy [local]" >&2
  exit 1
fi
NS=hub
DIR=/srv/hub/deploy/k8s/cluster
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
cp "$DIR"/*.yaml "$WORK"/
if [ "$MODE" = local ]; then
  sed -i \
    -e 's|ghcr.io/stevy64/gaboma-hub:main|docker.io/library/gaboma-hub:1|g' \
    -e 's|imagePullPolicy: Always|imagePullPolicy: Never|g' \
    "$WORK"/*.yaml
fi
DIR=$WORK
kubectl apply -f "$DIR/redis.yaml" -f "$DIR/volumes.yaml"
kubectl -n "$NS" rollout status deployment/redis --timeout=180s
kubectl -n "$NS" delete job hub-migrate --ignore-not-found
kubectl apply -f "$DIR/migrate.yaml"
kubectl -n "$NS" wait --for=condition=complete job/hub-migrate --timeout=180s
kubectl apply -f "$DIR/web.yaml"
kubectl -n "$NS" rollout restart deployment/hub-web
kubectl -n "$NS" rollout status deployment/hub-web --timeout=180s
