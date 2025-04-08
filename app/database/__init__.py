# This file makes the directory a Python package 
from .postgresql import test_database_connection, engine, Base, get_db, init_db, UserInDB

# Import Redis and MongoDB with proper error handling
try:
    from ..db.redis import redis_client
except ImportError:
    redis_client = None

try:
    from ..db.mongodb import mongodb
except ImportError:
    mongodb = None

__all__ = ['test_database_connection', 'engine', 'Base', 'get_db', 'init_db', 'UserInDB', 'redis_client', 'mongodb'] 

# Expose important functions and classes
test_database_connection = test_database_connection
engine = engine
Base = Base
get_db = get_db
init_db = init_db
UserInDB = UserInDB 