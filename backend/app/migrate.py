import asyncio
from sqlalchemy import text
from app.core.database import engine

async def migrate():
    async with engine.begin() as conn:
        print("Running PostgreSQL DDL Migrations on Neon Cloud...")
        # 1. Add workers_needed column to jobs table if missing
        await conn.execute(text("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS workers_needed INTEGER DEFAULT 1;"))
        print("-> Column jobs.workers_needed verified/added.")

        # 2. Ensure conversations table exists
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS conversations (
                id VARCHAR PRIMARY KEY,
                job_id INTEGER REFERENCES jobs(id) ON DELETE CASCADE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))
        print("-> Table conversations verified/created.")

        # 3. Ensure conversation_members table exists
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS conversation_members (
                conversation_id VARCHAR REFERENCES conversations(id) ON DELETE CASCADE,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (conversation_id, user_id)
            );
        """))
        print("-> Table conversation_members verified/created.")

        # 4. Ensure chat_messages table exists
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id VARCHAR PRIMARY KEY,
                conversation_id VARCHAR REFERENCES conversations(id) ON DELETE CASCADE,
                sender_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                content TEXT NOT NULL,
                message_type VARCHAR DEFAULT 'text',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                read_at TIMESTAMP NULL
            );
        """))
        print("-> Table chat_messages verified/created.")

    await engine.dispose()
    print("MIGRATIONS COMPLETED SUCCESSFULLY!")

if __name__ == "__main__":
    asyncio.run(migrate())
