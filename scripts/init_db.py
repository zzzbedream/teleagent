import os
import asyncio
import sys
import logging

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# Add root directory to sys.path to import database models
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from database.models import init_db

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/teleagent")

async def main():
    logging.info(f"Initializing database at {DATABASE_URL}...")
    try:
        await init_db(DATABASE_URL)
        logging.info("Database tables created successfully!")
    except Exception as e:
        logging.error(f"Failed to initialize database: {e}")

if __name__ == "__main__":
    asyncio.run(main())
