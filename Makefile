.PHONY: up down ps logs worker

# Docker commands
up:
	docker compose -f scripts/docker/docker-compose.yml up -d --remove-orphans

down:
	docker compose -f scripts/docker/docker-compose.yml down

ps:
	docker compose -f scripts/docker/docker-compose.yml ps

logs:
	docker compose -f scripts/docker/docker-compose.yml logs -f

rebuild:
	docker compose -f scripts/docker/docker-compose.yml build --no-cache
