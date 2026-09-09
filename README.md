# OmniBrain — Personal AI Operating System

OmniBrain is a personal AI OS that thinks and acts on your behalf.

## Tech Stack
- Python 3.12+ / FastAPI / Pydantic v2 / SQLAlchemy 2
- PostgreSQL 16 + pgvector / Redis 7
- Docker Compose
- JWT auth

## Quick Start
```bash
docker compose up
```

## Project Structure
- `apps/`: Application logic
- `tests/`: Tests
- `scripts/`: Utility scripts

## Development Commands
- `make up`: Start services
- `make down`: Stop services
- `make logs`: View logs
- `make build`: Build containers
- `make migrate`: Run migrations
- `make seed`: Seed database
- `make test`: Run tests
- `make lint`: Check linting
- `make format`: Format code
- `make shell`: Open api shell
- `make db-shell`: Open db shell
- `make clean`: Clean up containers and volumes
