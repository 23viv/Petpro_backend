from pymongo import MongoClient
from dotenv import load_dotenv
from pathlib import Path
import os

# Load the shared .env
env_path = Path(__file__).parent / "env" / ".env"
load_dotenv(env_path)

MONGO_URL      = os.getenv("MONGO_URL", "mongodb://localhost:27017")
MONGO_DB_NAME  = os.getenv("MONGO_DB_NAME", "petpro")

# One client instance for the whole app lifetime
_client = MongoClient(MONGO_URL)
_db     = _client[MONGO_DB_NAME]


def get_messages_collection():
    """Return the 'messages' collection from MongoDB."""
    return _db["messages"]
