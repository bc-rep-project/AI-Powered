#!/usr/bin/env python3
import logging
import asyncio
from sqlalchemy import text

logger = logging.getLogger(__name__)

async def run_migration(engine):
    """
    Add interaction_metadata column to interactions table if it doesn't exist.
    """
    logger.info("Running migration: add_interaction_metadata")
    
    # SQL to check if column exists and add it if it doesn't
    check_and_add_column_sql = """
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 
            FROM information_schema.columns 
            WHERE table_name='interactions' AND column_name='interaction_metadata'
        ) THEN
            ALTER TABLE interactions 
            ADD COLUMN interaction_metadata JSONB;
            
            RAISE NOTICE 'Added interaction_metadata column to interactions table';
        ELSE
            RAISE NOTICE 'interaction_metadata column already exists in interactions table';
        END IF;
    END $$;
    """
    
    try:
        async with engine.begin() as conn:
            await conn.execute(text(check_and_add_column_sql))
            logger.info("Migration completed successfully")
            return True
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        return False

# Run the migration if this file is executed directly
if __name__ == "__main__":
    from app.db.database import engine
    asyncio.run(run_migration(engine)) 