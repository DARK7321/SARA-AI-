import asyncio
import os
import sys
from dotenv import load_dotenv

# Ensure omnibrain root is on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
load_dotenv(".env")

from packages.core.db.session import engine, async_session_maker
from packages.core.db.base import Base
import packages.core.db.models as models
from packages.core.db.models import User
from packages.core.security.auth import get_password_hash
from sqlalchemy import text, select

async def main():
    print("Connecting to Supabase database...")
    db_url = os.getenv("DATABASE_URL", "")
    # Mask password for security
    print("Database URL host:", db_url.split("@")[-1] if "@" in db_url else "UNKNOWN")

    async with engine.begin() as conn:
        print("Enabling extensions (uuid-ossp, vector)...")
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";'))
        try:
            await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "vector";'))
            print("pgvector extension enabled!")
        except Exception as e:
            print("vector extension notice:", e)

        print("Creating all tables from SQLAlchemy models...")
        await conn.run_sync(Base.metadata.create_all)
        print("Tables created successfully!")

    async with async_session_maker() as session:
        result = await session.execute(select(User).where(User.email == "admin@omnibrain.local"))
        user = result.scalar_one_or_none()
        if not user:
            print("Seeding owner user admin@omnibrain.local...")
            owner = User(
                email="admin@omnibrain.local",
                name="Vikas (Owner)",
                role="owner",
                password_hash=get_password_hash("OmniBrain@2026"),
                timezone="Asia/Kolkata",
                settings={"language": "hi", "voice": "auto", "active_voice": "auto"}
            )
            session.add(owner)
            await session.commit()
            print("Owner user admin@omnibrain.local created successfully!")
        else:
            print("Owner user already exists!")

        # Verify tables in public schema
        result = await session.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name"))
        tables = result.scalars().all()
        print("VERIFIED SUPABASE TABLES:", tables)

if __name__ == "__main__":
    asyncio.run(main())
