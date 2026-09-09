# ADR-001: Foundation Stack

## Status
Accepted

## Context
We need to establish the baseline stack for the OmniBrain project. 

## Decision
We will use:
- **Language**: Python 3.12+
- **API Framework**: FastAPI for high performance async API
- **Database**: PostgreSQL 16 + pgvector for persistent data and embeddings
- **Cache/Tasks**: Redis 7
- **Authentication**: JWT with python-jose + passlib
- **Repo Structure**: Monorepo with separated apps and shared packages

## Consequences
- Requires async-first development practices
- Dependency management across monorepo packages
