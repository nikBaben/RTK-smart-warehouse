.DEFAULT_GOAL := help

DEV := docker compose --project-name rtk-smart-warehouse-dev --env-file .env.dev -f compose.yaml -f compose.dev.yaml
PROD := docker compose --project-name rtk-smart-warehouse-prod --env-file .env.prod -f compose.yaml -f compose.prod.yaml

.PHONY: help dev dev-build dev-up dev-down dev-logs dev-ps dev-config dev-migrate dev-compose prod-build prod-up prod-down prod-logs prod-ps prod-config prod-migrate prod-compose

help:
	@echo 'Dev:  make dev-build / dev-up / dev-down / dev-logs / dev-ps / dev-config'
	@echo 'Prod: make prod-build / prod-up / prod-down / prod-logs / prod-ps / prod-config'
	@echo 'Other commands: make dev-compose ARGS="..." / prod-compose ARGS="..."'

dev dev-build dev-up dev-down dev-logs dev-ps dev-config dev-migrate dev-compose: COMPOSE = $(DEV)
prod-build prod-up prod-down prod-logs prod-ps prod-config prod-migrate prod-compose: COMPOSE = $(PROD)

.env.dev:
	cp .env.dev.example .env.dev

dev dev-build dev-up dev-down dev-logs dev-ps dev-config dev-migrate dev-compose test: | .env.dev

dev: dev-build
	$(COMPOSE) up -d --no-build --wait --wait-timeout 180

dev-build prod-build:
	$(COMPOSE) build api frontend

dev-up:
	$(COMPOSE) up -d --no-build --wait --wait-timeout 180

prod-up:
	$(COMPOSE) up -d --no-build

dev-down prod-down:
	$(COMPOSE) down

dev-logs prod-logs:
	$(COMPOSE) logs -f --tail=100

dev-ps prod-ps:
	$(COMPOSE) ps

dev-config prod-config:
	$(COMPOSE) config --quiet

dev-migrate prod-migrate:
	$(COMPOSE) run --rm --no-deps api alembic upgrade head

dev-compose prod-compose:
	$(COMPOSE) $(ARGS)

# Unit and HTTP tests use fakes; no database, Redis or Keycloak is started.
.PHONY: test
test:
	$(DEV) run --rm --no-deps api python -m pytest tests/unit -q
