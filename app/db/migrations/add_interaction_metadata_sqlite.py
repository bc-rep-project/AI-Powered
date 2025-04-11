#!/usr/bin/env python3
import logging
import asyncio
from sqlalchemy import text, inspect

logger = logging.getLogger(__name__)

async def run_migration(engine):
    """
    Add interaction_metadata column to interactions table for SQLite if it doesn't exist.
    """
    logger.info("Running migration: add_interaction_metadata_sqlite")
    
    # Check if we're using SQLite
    if not str(engine.url).startswith('sqlite'):
        logger.info("Skipping SQLite migration for non-SQLite database")
        return True
    
    try:
        # Check if column exists
        inspector = inspect(engine)
        columns = [c['name'] for c in inspector.get_columns('interactions')]
        
        if 'interaction_metadata' not in columns:
            async with engine.begin() as conn:
                # SQLite doesn't support JSONB, use TEXT instead
                await conn.execute(text(
                    "ALTER TABLE interactions ADD COLUMN interaction_metadata TEXT"
                ))
                logger.info("Added interaction_metadata column to interactions table in SQLite")
        else:
            logger.info("interaction_metadata column already exists in interactions table")
        
        return True
    except Exception as e:
        logger.error(f"SQLite migration failed: {str(e)}")
        return False

# Run the migration if this file is executed directly
if __name__ == "__main__":
    from app.db.database import engine
    asyncio.run(run_migration(engine)) 