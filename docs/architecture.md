# OmniBrain Architecture

This outlines the high-level architecture per ADR-001-foundation.

## Stack
- Python 3.12+
- FastAPI (API layer)
- PostgreSQL (Database)
- Redis (Cache/Tasks)

## Structure
- `apps/`: Deployable services (api, orchestrator, worker)
- `packages/`: Shared libraries (core schemas, connectors, etc.)
- `config/`: Configuration files (YAML)
- `docs/`: Documentation and ADRs
