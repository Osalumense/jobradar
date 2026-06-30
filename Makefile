.PHONY: build up down logs backend-logs frontend-logs ps clean test-backend seed-db

# Build all Docker containers
build:
	docker compose build

# Start the application services in the background
up:
	docker compose up -d

# Stop the application services
down:
	docker compose down

# View real-time aggregated logs
logs:
	docker compose logs -f

# View backend scorer service logs
backend-logs:
	docker compose logs -f backend

# View frontend Nuxt logs
frontend-logs:
	docker compose logs -f frontend

# List running containers
ps:
	docker compose ps

# Stop containers and remove volumes/cached resources
clean:
	docker compose down -v --rmi all --remove-orphans

# Run backend test suite
test-backend:
	cd services/scorer && source venv/bin/activate && pytest

# Seed the master profile and target queries in the database
seed-db:
	cd services/scorer && export $$(grep -v '^#' ../../.env | xargs) && source venv/bin/activate && python run_onboarding_seed.py
