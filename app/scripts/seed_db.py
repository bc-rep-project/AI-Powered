import asyncio
import sys
import os

# Add the parent directory to Python path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app.database import get_db, mongodb
from app.data.seed import seed_database

async def main():
    print("Starting database seeding process...")
    
    try:
        # Get database session
        async for db in get_db():
            # Run seeding process
            success = await seed_database(db, mongodb)
            
            if success:
                print("Database seeding completed successfully!")
            else:
                print("Database seeding failed!")
                
    except Exception as e:
        print(f"Error during database seeding: {str(e)}")
        return False
    
    return True

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1) 