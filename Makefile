DEV = docker compose -f compose.dev.yaml
PROD = docker compose --env-file .env.production -f compose.yaml
.DEFAULT_GOAL := help
.PHONY: help dev prod deploy stop-dev stop-prod logs-dev logs-prod test check migrate superuser superuser-dev ps backup
help:
	@echo "dev | prod | deploy | stop-dev | stop-prod | logs-dev | logs-prod | test | check | migrate | superuser | superuser-dev | ps | backup"
dev:
	$(DEV) up -d --build --wait
prod:
	$(PROD) build
	$(PROD) up -d --wait db redis
	$(PROD) run --rm migrate
	$(PROD) up -d --wait
# Deployer une image versionnee deja publiee (HUB_IMAGE dans .env.production).
deploy:
	$(PROD) pull
	$(PROD) up -d --wait db redis
	$(PROD) run --rm migrate
	$(PROD) up -d --no-build --wait
stop-dev:
	$(DEV) down
stop-prod:
	$(PROD) down
logs-dev:
	$(DEV) logs -f --tail=100
logs-prod:
	$(PROD) logs -f --tail=100
ps:
	$(PROD) ps
migrate:
	$(PROD) run --rm migrate
superuser:
	$(PROD) exec web python manage.py createsuperuser
superuser-dev:
	$(DEV) exec web python manage.py createsuperuser
test:
	$(DEV) exec -T web python manage.py test hub config --verbosity 1
check:
	$(PROD) run --rm web python manage.py check --deploy --fail-level WARNING
backup:
	$(PROD) exec -T db sh -c 'pg_dump -U hub -d hub -Fc -f /tmp/hub.dump'
	$(PROD) cp db:/tmp/hub.dump ./hub-backup.dump
	$(PROD) exec -T web tar -czf /tmp/media.tar.gz -C /app media
	$(PROD) cp web:/tmp/media.tar.gz ./hub-media-backup.tar.gz

# Explicit context and immutable image, e.g. make k3s-deploy CONTEXT=ovh IMAGE=ghcr.io/org/hub@sha256:...
.PHONY: k3s-render k3s-deploy
k3s-render:
	python3 deploy/k8s/deploy.py --context "$(CONTEXT)" --image "$(IMAGE)" --render
k3s-deploy:
	python3 deploy/k8s/deploy.py --context "$(CONTEXT)" --image "$(IMAGE)"
