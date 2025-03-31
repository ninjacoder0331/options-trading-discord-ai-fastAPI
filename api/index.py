from fastapi import FastAPI, HTTPException
# from motor.motor_asyncio import AsyncIOMotorClient
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from .routes import auth
from .routes import trader
from .routes import brokerage
from .routes import analyst
# import os
# import platform
# import asyncio
from .database import get_database
from datetime import datetime
from zoneinfo import ZoneInfo
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.schedulers.background import BackgroundScheduler
from .routes.utils import parse_option_date


# if platform.system()=='Windows':
#     asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
# else:
#     asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())
# Load environment variables
load_dotenv()

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# MongoDB connection

# db = client.optionsTrading


# Include routers
app.include_router(auth.router, prefix="/api/auth")
app.include_router(trader.router, prefix="/api/trader")
app.include_router(brokerage.router, prefix="/api/brokerage")
app.include_router(analyst.router, prefix="/api/analyst")

@app.get("/")
async def read_root():
    return {"message": "Welcome to FastAPI with MongoDB"}

# Example endpoint to get items
@app.get("/items")
async def get_items():
    try:
        # Get count of traders collection
        trader_collection = await get_database("traders")
        count = await trader_collection.count_documents({})
        print(count)
        # Or get all traders
        return {"total_traders": count}
        # return {"message": "Hello World"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Example endpoint to create an item
@app.post("/items")
async def create_item(item: dict):
    try:
        global traders
        result = await traders.insert_one(item)
        return {"id": str(result.inserted_id)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Create and start scheduler
scheduler = AsyncIOScheduler()

# auto sell logic
async def check_open_positions():
    position_collection = await get_database("positions")
    open_positions = await position_collection.find({"status": "open"}).to_list(length=1000)
    for position in open_positions:
        print(position["orderSymbol"])
        month, date = parse_option_date(position["orderSymbol"])
        print(month, date)
        current_et = datetime.now(ZoneInfo("America/New_York"))
        print("today is", current_et.strftime("%m-%d"))

    current_time = datetime.now(ZoneInfo("America/New_York"))
    print(f"Function executed at: {current_time}")

# Use AsyncIOScheduler instead of BackgroundScheduler
scheduler.start()

# Schedule job to run at 3:00:00 PM ET
scheduler.add_job(
    check_open_positions, 
    trigger='cron',
    hour=3,      # 3 PM
    minute=6,     # 40 minutes
    second=0,     # 00 seconds
    timezone=ZoneInfo("America/New_York"),  # ET timezone
    misfire_grace_time=None  # Optional: handle misfired jobs
)

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

# Get local time and attach local timezone
local = datetime.now().astimezone()
print(f"Local time with TZ: {local.strftime('%Y-%m-%d %H:%M:%S %Z')}")

# Convert to ET
et_time = local.astimezone(ZoneInfo("America/New_York"))
print(f"ET time: {et_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")

# For verification, also show system local time
local_time = datetime.now()
print(f"System local time: {local_time.strftime('%Y-%m-%d %H:%M:%S')}")

# For Singapore time
current_sg_time = datetime.now(ZoneInfo("Asia/Singapore"))
print(f"Current time in Singapore: {current_sg_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")

