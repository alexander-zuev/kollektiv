.PHONY: up down ps logs worker

# Docker commands
up:
	docker compose --env-file config/.env -f scripts/docker/compose.yaml up -d --remove-orphans

down:
	docker compose --env-file config/.env -f scripts/docker/compose.yaml down

ps:
	docker compose --env-file config/.env -f scripts/docker/compose.yaml ps

logs:
	docker compose --env-file config/.env -f scripts/docker/compose.yaml logs -f

rebuild:
	docker compose --env-file config/.env -f scripts/docker/compose.yaml build --no-cache
