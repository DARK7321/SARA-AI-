.PHONY: up down logs build migrate seed test lint format shell db-shell clean

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

build:
	docker compose build

migrate:
	alembic upgrade head

seed:
	python scripts/seed.py

test:
	pytest tests/ -v

lint:
	ruff check .

format:
	ruff format .

shell:
	docker compose exec api bash

db-shell:
	docker compose exec postgres psql -U omnibrain

clean:
	docker compose down -v
