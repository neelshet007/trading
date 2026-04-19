import logging
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import certifi
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv(Path(__file__).resolve().parent / ".env")

logger = logging.getLogger(__name__)
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/trading_platform")
IST = ZoneInfo("Asia/Kolkata")


def _create_client():
    try:
        options = {"tlsCAFile": certifi.where()} if MONGO_URI.startswith("mongodb+srv://") else {}
        return AsyncIOMotorClient(MONGO_URI, **options)
    except Exception as exc:
        logger.error("MongoDB client initialization failed: %s", exc)
        return None


client = _create_client()
db = client.get_database("trading_platform") if client else None

signals_collection = db["signals"] if db is not None else None
market_summary_collection = db["market_summary"] if db is not None else None
watchlist_collection = db["watchlist"] if db is not None else None
ticker_universe_collection = db["ticker_universe"] if db is not None else None


def db_updated_at() -> datetime:
    return datetime.now(IST)

async def setup_db():
    if client is None:
        logger.warning("MongoDB is unavailable. Continuing in degraded mode.")
        return False
    try:
        await client.admin.command("ping")
        logger.info("Connected to MongoDB successfully!")
        return True
    except Exception as e:
        logger.error("MongoDB connection failed: %s", e)
        return False
