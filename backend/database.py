import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/trading_platform")
client = AsyncIOMotorClient(MONGO_URI)
db = client.get_database("trading_platform")

signals_collection = db["signals"]
market_summary_collection = db["market_summary"]
watchlist_collection = db["watchlist"]
ticker_universe_collection = db["ticker_universe"]
IST = ZoneInfo("Asia/Kolkata")


def db_updated_at() -> datetime:
    return datetime.now(IST)

async def setup_db():
    try:
        await client.admin.command('ping')
        logging.info("Connected to MongoDB successfully!")
    except Exception as e:
        logging.error(f"MongoDB connection failed: {e}")
