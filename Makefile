.PHONY: up down ps logs worker rebuild push-ghcr rebuild-and-push

# Docker commands
up:
	docker compose --env-file config/.env -f scripts/docker/compose.yaml up -d --remove-orphans

dev:
	docker compose --env-file config/.env -f scripts/docker/compose.yaml up --remove-orphans --watch

down:
	docker compose --env-file config/.env -f scripts/docker/compose.yaml down

ps:
	docker compose --env-file config/.env -f scripts/docker/compose.yaml ps

logs:
	docker compose --env-file config/.env -f scripts/docker/compose.yaml logs -f

rebuild:
	docker compose --env-file config/.env -f scripts/docker/compose.yaml build
	docker compose --env-file config/.env -f scripts/docker/compose.yaml up -d --remove-orphans

push-ghcr:
	docker build -f scripts/docker/Dockerfile -t ghcr.io/alexander-zuev/kollektiv-rq:latest .
	docker push ghcr.io/alexander-zuev/kollektiv-rq:latest

rebuild-and-push: rebuild push-ghcr
