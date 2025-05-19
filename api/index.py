from fastapi import FastAPI, HTTPException
# from motor.motor_asyncio import AsyncIOMotorClient
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from .routes import auth
from .routes import trader
from .routes import brokerage
from .routes import analyst
from bson import ObjectId
import os
# import platform
# import asyncio
from .database import get_database
from datetime import datetime
from zoneinfo import ZoneInfo
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.schedulers.background import BackgroundScheduler
from .routes.utils import parse_option_date
from dotenv import load_dotenv
import requests
import ntplib
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

scheduler = AsyncIOScheduler()

async def check_open_positions():
    return "Checking open positions"

async def check_stoploss_profit(position_id, option_symbol, entry_price, user_id, total_amount, sold_amount, asset_id):
    trader_collection = await get_database("traders")
    trader = await trader_collection.find_one({"_id": ObjectId(user_id)})

    brokerage_collection = await get_database("brokerageCollection")
    brokerage = await brokerage_collection.find_one({"_id": ObjectId(trader["brokerageName"])})

    api_key = brokerage["API_KEY"]
    api_secret = brokerage["SECRET_KEY"]

    headers = {
        "APCA-API-KEY-ID": api_key,
        "APCA-API-SECRET-KEY": api_secret,
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    print("asset_id: ", asset_id)
    url = f"https://paper-api.alpaca.markets/v2/positions/{asset_id}"

    response = requests.get(url, headers=headers)
    response_json = response.json()
    current_price = float(response_json["current_price"])
    entry_price = float(response_json["avg_entry_price"])

    trader_collection = await get_database("traders")
    trader = await trader_collection.find_one({"_id": ObjectId(user_id)})

    if trader:
        stoploss = float(trader.get("stopLoss", 0))
        profit = float(trader.get("profitTaking", 0))

        if stoploss != 0:
            stoploss_condition_price = entry_price * (1 - stoploss / 100)
            print("stoploss_condition_price: ", stoploss_condition_price)

            if stoploss_condition_price >= current_price:
                try:
                    position_collection = await get_database("positions")
                    open_position = await position_collection.find_one({"asset_id": asset_id})
                    if open_position:
                        await auto_sell_options(option_symbol, total_amount, sold_amount, position_id, api_key, api_secret)
                except Exception as e:
                    print(f"Error in stoploss check: {e}")
            
        if profit != 0:
            profit_condition_price = entry_price * (1 + profit / 100)
            print("profit_condition_price: ", profit_condition_price)
            if profit_condition_price <= current_price:
                try:
                    position_collection = await get_database("positions")
                    open_position = await position_collection.find_one({"asset_id": asset_id})
                    print("open_position: ", open_position)
                    if open_position:
                        await auto_sell_options(option_symbol, total_amount, sold_amount, position_id, api_key, api_secret)
                except Exception as e:
                    print(f"Error in profit check: {e}")
    return "Checking stoploss and profit"

async def check_market_time():
    try:
        # Get time from NTP server
        ntp_client = ntplib.NTPClient()
        response = ntp_client.request('pool.ntp.org')
        # Convert NTP time to datetime and set timezone to ET
        current_time = datetime.fromtimestamp(response.tx_time, ZoneInfo("America/New_York"))
    except Exception as e:
        print(f"Error getting NTP time: {e}")
        # Fallback to local time if NTP fails
        current_time = datetime.now(ZoneInfo("America/New_York"))

    print("current_time: ", current_time)

    # Check if it's a weekday (0 = Monday, 6 = Sunday)
    if current_time.weekday() >= 5:  # Saturday or Sunday
        return False

    # Create time objects for market open and close
    market_open = current_time.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = current_time.replace(hour=16, minute=0, second=0, microsecond=0)

    # Check if current time is within market hours
    is_market_open = market_open <= current_time <= market_close
    return is_market_open

async def auto_sell_options(option_symbol , total_amount , sold_amount , position_id , api_key, secret_key):
    try:
        headers = {
            "APCA-API-KEY-ID": api_key,
            "APCA-API-SECRET-KEY": secret_key,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        url = "https://paper-api.alpaca.markets/v2/orders"
        payload = {
            "type": "market",
            "time_in_force": "day",
            "symbol": option_symbol,
            "qty": total_amount - sold_amount,
            "side": "sell",
        }
        response = requests.post(url, headers=headers, json=payload)

        position_collection = await get_database("positions")
        current_date = datetime.now(ZoneInfo("America/New_York")).date()
        await position_collection.update_one({"_id": ObjectId(position_id)}, {"$set": {"status": "closed"}})
        await position_collection.update_one({"_id": ObjectId(position_id)}, {"$set": {"soldAmount": total_amount}})
        await position_collection.update_one({"_id": ObjectId(position_id)}, {"$set": {"exitDate": current_date}})
        return response.json()
    except Exception as e:
        print(f"Error in auto sell options: {e}")
            

async def check_date_expired(option_symbol , total_amount , sold_amount , position_id , user_id):
    try:
        # print("options symbol" , option_symbol)
        month, date = parse_option_date(option_symbol)
        try:
            # Get time from NTP server
            ntp_client = ntplib.NTPClient()
            response = ntp_client.request('pool.ntp.org')
            # Convert NTP time to datetime and set timezone to ET
            current_time = datetime.fromtimestamp(response.tx_time, ZoneInfo("America/New_York"))
        except Exception as e:
            print(f"Error getting NTP time: {e}")
            # Fallback to local time if NTP fails
            current_time = datetime.now(ZoneInfo("America/New_York"))
            
        # Create expiration date object (40 minutes before market close)
        expiration_date = current_time.replace(month=int(month), day=int(date), hour=15, minute=20, second=0, microsecond=0)
        
        # Check if current time is on expiration date and 40 minutes before close
        if current_time.date() == expiration_date.date() and current_time >= expiration_date:
            print(f"Option {option_symbol} is 40 minutes before market close on expiration date")
            trader_collection = await get_database("traders")
            trader = await trader_collection.find_one({"_id": ObjectId(user_id)})
            brokerage_collection = await get_database("brokerageCollection")
            brokerage = await brokerage_collection.find_one({"_id": ObjectId(trader["brokerageName"])})

            api_key = brokerage["API_KEY"]
            api_secret = brokerage["SECRET_KEY"]
            await auto_sell_options(option_symbol , total_amount , sold_amount , position_id , api_key, api_secret)
            return True
        else:
            print(f"Current time: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"Expiration check time: {expiration_date.strftime('%Y-%m-%d %H:%M:%S')}")
            return False
            
    except Exception as e:
        print(f"Error in date expired check: {e}")
        return False

async def check_funtion():
    try:
        # First check if market is open
        is_market_open = await check_market_time()
        if not is_market_open:
            print(f"Market is closed.")
            return "Market is closed."

        position_collection = await get_database("positions")
        open_positions = await position_collection.find({"status": "open"}).to_list(length=1000)    

        if open_positions:
            print(f"Found {len(open_positions)} open positions")
            for position in open_positions:
                await check_stoploss_profit(position["_id"] , position["orderSymbol"] , position["entryPrice"] , position["userID"] , position["amount"] , position["soldAmount"], position["asset_id"])
        else:
            print(f"No open positions")

        return "Function executed successfully"
    except Exception as e:
        print(f"Error in function: {str(e)}")
        return "Error occurred"

# Schedule job to run every 10 seconds with proper cooldown
scheduler.add_job(
    check_funtion,
    trigger='interval',
    seconds=60,     # Run every 10 seconds
    timezone=ZoneInfo("America/New_York"),  # ET timezone
    misfire_grace_time=30,  # Allow jobs to be 30 seconds late
    max_instances=1,  # Only allow one instance to run at a time
    coalesce=True  # Combine multiple pending jobs into one
)

# Start the scheduler when the application starts
@app.on_event("startup")
async def start_scheduler():
    scheduler.start()

# Shutdown the scheduler when the application stops
@app.on_event("shutdown")
async def shutdown_scheduler():
    scheduler.shutdown()
