import logging
import importlib
import os
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

async def run_all_migrations(engine):
    """
    Run all migrations in the migrations directory.
    """
    logger.info("Running all database migrations")
    
    # Get the migrations directory
    migrations_dir = Path(__file__).parent
    
    # Get all Python files in the migrations directory
    migration_files = [f for f in os.listdir(migrations_dir) 
                       if f.endswith('.py') and f != '__init__.py']
    
    # Sort migration files to ensure they run in order
    migration_files.sort()
    
    success_count = 0
    failure_count = 0
    
    # Run each migration
    for migration_file in migration_files:
        migration_name = migration_file[:-3]  # Remove .py extension
        logger.info(f"Running migration: {migration_name}")
        
        try:
            # Import the migration module
            module_path = f"app.db.migrations.{migration_name}"
            migration_module = importlib.import_module(module_path)
            
            # Run the migration
            if hasattr(migration_module, 'run_migration'):
                result = await migration_module.run_migration(engine)
                if result:
                    success_count += 1
                    logger.info(f"Migration {migration_name} completed successfully")
                else:
                    failure_count += 1
                    logger.error(f"Migration {migration_name} failed")
            else:
                logger.warning(f"Migration {migration_name} does not have a run_migration function")
        except Exception as e:
            failure_count += 1
            logger.error(f"Error running migration {migration_name}: {str(e)}")
    
    logger.info(f"Migrations complete: {success_count} succeeded, {failure_count} failed")
    return success_count, failure_count 