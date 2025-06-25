from fastapi import APIRouter, HTTPException
from ..database import get_database
from bson import ObjectId
from pydantic import BaseModel
from ..models.trader import Position
import os
from datetime import datetime
import requests
import json
from dotenv import load_dotenv
from ..routes.utils import parse_option_date, check_option_expiry
import time
import asyncio
import ntplib
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

load_dotenv()

router = APIRouter()

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


@router.get("/getTraders")
async def get_traders():
    try:
        trader_collection = await get_database("traders")
        traders = await trader_collection.find({"role": "trader"}).to_list(1000)
        if not traders:
            print("No traders found with role 'trader'")
            traders = []
        
        # Convert ObjectId to string for JSON serialization
        for trader in traders:
            trader["_id"] = str(trader["_id"])
            if "user_id" in trader:
                trader["user_id"] = str(trader["user_id"])
                
        return traders
    except Exception as e:
        print(f"Error fetching traders: {e}")
        traders = []
        return traders

@router.get("/getAnalysts")
async def get_analysts():
    try:
        analyst_collection = await get_database("analyst")
        analysts = await analyst_collection.find().to_list(1000)

        # Convert ObjectId to string for JSON serialization
        for analyst in analysts:
            analyst["_id"] = str(analyst["_id"])

        return analysts
    except Exception as e:
        print(f"Error fetching analysts: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch analysts")

class UpdateBrokerage(BaseModel):
    traderId: str
    brokerageName : str


@router.post("/updateBrokerage")
async def update_brokerage(brokerage: UpdateBrokerage):
    try:
        trader_collection = await get_database("traders")
        result = await trader_collection.update_one(
            {"_id": ObjectId(brokerage.traderId)},
            {"$set": {"brokerageName": brokerage.brokerageName}}
        )
        return {"message": "Brokerage updated successfully"}
    except Exception as e:
        print(f"Error updating brokerage: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update brokerage")

class UpdateAnalyst(BaseModel):
    traderId: str
    analystId: str
    analystNumber : int

@router.post("/updateAnalyst")
async def update_analyst(analyst: UpdateAnalyst):
    try:
        print("analyst: ", analyst)
        trader_collection = await get_database("traders")
        result = await trader_collection.update_one(
            {"_id": ObjectId(analyst.traderId)},
            {"$set": {"analyst"+str(analyst.analystNumber): analyst.analystId}}
        )
        return {"message": "Analyst updated successfully"}
    except Exception as e:
        print(f"Error updating analyst: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update analyst")
    
class DeleteTrader(BaseModel):
    traderId: str

@router.post("/deleteTrader")
async def delete_trader(trader: DeleteTrader):
    try:
        trader_collection = await get_database("traders")
        result = await trader_collection.delete_one({"_id": ObjectId(trader.traderId)})
        return {"message": "Trader deleted successfully"}
    except Exception as e:
        print(f"Error deleting trader: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete trader")

class Get_trader_analyst_class(BaseModel):
    traderId: str

@router.post("/getTraderAnalysts")
async def get_trader_analysts(trader: Get_trader_analyst_class):
    try:
        # print("traderId: ", trader)
        # print("traderAnalyst")

        trader_collection = await get_database("traders")
        trader = await trader_collection.find_one({"_id": ObjectId(trader.traderId)})
        # print("trader: ", trader)
        if trader:
            trader["_id"] = str(trader["_id"])
        return trader
    except Exception as e:
        print(f"Error getting trader analysts: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get trader analysts")

@router.post("/addPosition")
async def add_position(position: Position):
    try:
        trader_collection = await get_database("traders")
        trader = await trader_collection.find_one({"_id": ObjectId(position.userID)})
        brokerage_collection = await get_database("brokerageCollection")
        brokerage = await brokerage_collection.find_one({"_id": ObjectId(trader["brokerageName"])})
        alpaca_api_key = brokerage["API_KEY"]
        alpaca_secret_key = brokerage["SECRET_KEY"]
        check_live_trading = brokerage["liveTrading"]
        paper_url = os.getenv("PAPER_URL")
        trader_amount = 0
        amount = 0

        # print("trader: ", trader)

        if trader:
            trader_id = trader["_id"]
            trader_amount = trader["amount"]
            # print("trader_amount: ", trader_amount)
            if trader_amount < position.entryPrice * 100:
                raise HTTPException(status_code=404, detail="Insufficient balance")
            else :
                amount = int(trader_amount / (position.entryPrice * 100))
                # print("amount: ", amount)
        else:
            return 404
            raise HTTPException(status_code=404, detail="User not found")
        position.amount = amount
        position_collection = await get_database("positions")

        if check_live_trading == True:
            url = "https://api.alpaca.markets/v2/orders"
        else:
            url = f"{paper_url}/v2/orders"
        payload = {
            "type": "market",
            "time_in_force": "day",
            "symbol": position.orderSymbol,
            "qty": position.amount,
            "side": "buy",
        }
        print("alpaca_api_key: ", alpaca_api_key)
        print("alpaca_secret_key: ", alpaca_secret_key)
        print("payload: ", payload)
        if(alpaca_api_key == "" or alpaca_secret_key == ""):
            return 429
        headers = {
                    "accept": "application/json",
                    "content-type": "application/json",
                    "APCA-API-KEY-ID": alpaca_api_key,
                    "APCA-API-SECRET-KEY": alpaca_secret_key
                }
        
        check_url = f"https://data.alpaca.markets/v1beta1/options/snapshots?symbols={position.orderSymbol}&feed=indicative&limit=100"

        response = requests.get(check_url, headers=headers)
        response_json = response.json()
        bidPrice = response_json["snapshots"][position.orderSymbol]["latestQuote"]["ap"]
        askPrice = response_json["snapshots"][position.orderSymbol]["latestQuote"]["bp"]

        if abs(bidPrice - askPrice) < position.entryPrice * 0.04:
            position.entryPrice = bidPrice
        else :
            position.entryPrice = askPrice

            times = 3
            while times > 0:
                if position.entryPrice - bidPrice > position.entryPrice * (-0.02):
                    response = requests.get(check_url, headers=headers)
                    response_json = response.json()
                    # print(response_json)
                    bidPrice = response_json["snapshots"][position.orderSymbol]["latestQuote"]["ap"]
                    print("bidPrice: ", bidPrice)
                else :
                    break;
                if times == 0:
                    return 201
                else :
                    times -= 1
                    time.sleep(5)
                    print("times: ", times)
        position.entryPrice = bidPrice
        response = requests.post(url, json=payload, headers=headers)
        print("response: ", response.status_code)
        if response.status_code == 422:
            return 422
        if response.status_code == 403:
            return 455
        tradingId = response.json()["id"]
        # print("response: ", response.status_code)

        if response.status_code == 200 and tradingId != "":
            await asyncio.sleep(2)
            if check_live_trading == True:
                url2 = "https://api.alpaca.markets/v2/orders?status=all&symbols="+position.orderSymbol
            else:
                url2 = "https://paper-api.alpaca.markets/v2/orders?status=all&symbols="+position.orderSymbol
            
            response2 = requests.get(url2, headers=headers)
            for order in response2.json():
                # print("*")
                if order["id"] == tradingId:
                    # print("--------------------" , tradingId)
                    price = order["filled_avg_price"]
                    buy_quantity = order["filled_qty"]
                    entrytimestamp = order["filled_at"]
                    asset_id = order["asset_id"]
                    entry_price = price  # This will now update the global variable
                    # print("*********************" , price ," entrytimestamp " , entrytimestamp)
                    
                    print("buy order is excuted" , entry_price)
                    # print("history data" , history_data)
                    position_dict = {}
                    position_dict["symbol"] = position.symbol
                    position_dict["orderSymbol"] = position.orderSymbol
                    position_dict["quantity"] = buy_quantity
                    position_dict["analyst"] = position.analyst
                    position_dict["side"] = position.side
                    position_dict["orderType"] = position.orderType
                    position_dict["timeInForce"] = position.timeInForce
                    position_dict["date"] = position.date
                    position_dict["entryPrice"] = entry_price
                    position_dict["childType"] = position.childType
                    position_dict["userID"] = position.userID
                    position_dict["amount"] = position.amount
                    position_dict["soldAmount"] = 0
                    position_dict["exitDate"] = position.exitDate
                    position_dict["strikePrice"] = position.strikePrice
                    position_dict["tradingId"] = tradingId
                    position_dict["asset_id"] = asset_id
                    position_dict["status"] = "open"
                    position_dict["closePrice"] = 0
                    position_dict["entryDate"] = entrytimestamp
                    position_dict["created_at"] = datetime.now().isoformat()
                    
                    await position_collection.insert_one(position_dict)
                    break;
             
            # Convert position to dict and add current time
            

            return 200
        else:
            print(f"Unexpected status code: {response.status_code}")
            # return {"message": "Failed to add position. Please check the market time"}
            return 422
        # print("result: ", result)
        return {"message": "Position added successfully"}
    except Exception as e:
        print(f"Error adding position: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to add position")
    
# # get Traders Data
@router.get("/getTraderData")
async def get_trader_data():
    try:
        # Get analysts data
        analyst_collection = await get_database("analyst")
        analysts = await analyst_collection.find().to_list(1000)
        
        # Get positions data
        position_collection = await get_database("positions")
        positions = await position_collection.find().to_list(1000)
        
        # Convert ObjectId to string for JSON serialization
        for analyst in analysts:
            analyst["_id"] = str(analyst["_id"])
        
        for position in positions:
            position["_id"] = str(position["_id"])
            # Convert datetime to string if it exists
            if "created_at" in position:
                position["created_at"] = position["created_at"].isoformat()
        
        # Return combined data
        return {
            "analysts": analysts,
            "positions": positions
        }
    except Exception as e:
        print(f"Error fetching trader data: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch trader data")
    
@router.get("/getOpenPositions")
async def get_options_position():
   result = await get_position_status("open")
   return result

class TraderClosePositions(BaseModel):
    traderId: str

@router.post("/getTraderClosePositions")
async def get_trader_close_positions(traderId: TraderClosePositions):
    # print("traderId: ", traderId.traderId)
    result = await get_position_status_by_traderId("closed", traderId.traderId)
    return result

class TraderOpenPositions(BaseModel):
    traderId: str

@router.post("/getTraderOpenPositions")
async def get_trader_open_positions(traderId: TraderOpenPositions):
    result = await get_position_status_by_traderId("open", traderId.traderId)
    return result

async def get_position_status_by_traderId(position, traderId):
    try:
        position_collection = await get_database("positions")
        trader_collection = await get_database("traders")
        brokerage_collection = await get_database("brokerageCollection")
        trader = await trader_collection.find_one({"_id": ObjectId(traderId)})
        brokerage = await brokerage_collection.find_one({"_id": ObjectId(trader["brokerageName"])})

        alpaca_api_key = brokerage["API_KEY"]
        alpaca_secret_key = brokerage["SECRET_KEY"]
        check_live_trading = brokerage["liveTrading"]

        positions = await position_collection.find({"status": position, "userID": traderId}).to_list(1000)
        if not positions:
            # print("No open positions found")
            positions = []


        for position in positions:
            position["_id"] = str(position["_id"])
            # Convert datetime to string if it exists
            if "created_at" in position:
                current_time = datetime.now()
                # Convert ISO format string to datetime object
                created_at = datetime.fromisoformat(position["created_at"].replace('Z', '+00:00'))
                # Calculate difference in minutes
                difference = int((current_time - created_at).total_seconds() / 60)
                # print("difference in minutes: ", difference)
                position["timeDifference"] = difference
            if position['orderSymbol'] != '' and position['status'] == "open":

                headers = {
                            "accept": "application/json",
                            "content-type": "application/json",
                            "APCA-API-KEY-ID": alpaca_api_key,
                            "APCA-API-SECRET-KEY": alpaca_secret_key
                        }
                

                if check_live_trading == True:
                    url = "https://api.alpaca.markets/v2/positions/" + position['orderSymbol']
                else:
                    url = "https://paper-api.alpaca.markets/v2/positions/" + position['orderSymbol']

                response = requests.get(url, headers=headers)
                
                position['currentPrice'] = response.json()['current_price']
        return {
            "positions": positions
        }
    except Exception as e:
        print(f"Error fetching trader data: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch trader data")

@router.get("/getClosePositions")
async def get_closed_positions():
    result = await get_position_status_closed("closed")
    return result


async def get_position_status_closed(position):
    try:
        # Get positions data
        position_collection = await get_database("positions")
        positions = await position_collection.find(
            {"status": position}
        ).to_list(1000)

        print("positions: ", positions)

        if not positions:
            print("No open positions found")
            positions = []
        for position in positions:
            position["_id"] = str(position["_id"])
            
            # Convert datetime to string if it exists
            if "created_at" in position:
                position["created_at"] = position["created_at"]
            if position['orderSymbol'] != '' and position['status'] == "open":
                month, date = parse_option_date(position['orderSymbol'])
                is_valid_option = check_option_expiry(month, date)
                if not is_valid_option:
                    await position_collection.update_one(
                        {"_id": ObjectId(position["_id"])},
                        {"$set": {"status": "closed"}}
                    )
                    break

        return {
            "positions": positions
        }
    except Exception as e:
        print(f"Error fetching trader data: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch trader data")


async def get_position_status(position):
    try:
        # Get positions data
        position_collection = await get_database("positions")
        positions = await position_collection.find(
            {"status": position}
        ).to_list(1000)

        print("positions: ", positions)
        trader_collection = await get_database("traders")

        if not positions:
            print("No open positions found")
            positions = []
        for position in positions:
            position["_id"] = str(position["_id"])
            trader = await trader_collection.find_one({"_id": ObjectId(position.get("userID"))})
            brokerage_collection = await get_database("brokerageCollection")
            brokerage = await brokerage_collection.find_one({"_id": ObjectId(trader["brokerageName"])})

            alpaca_api_key = brokerage["API_KEY"]
            alpaca_secret_key = brokerage["SECRET_KEY"]
            check_live_trading = brokerage["liveTrading"]
            
            # Convert datetime to string if it exists
            if "created_at" in position:
                position["created_at"] = position["created_at"]
            if position['orderSymbol'] != '' and position['status'] == "open":
                month, date = parse_option_date(position['orderSymbol'])
                is_valid_option = check_option_expiry(month, date)
                if not is_valid_option:
                    await position_collection.update_one(
                        {"_id": ObjectId(position["_id"])},
                        {"$set": {"status": "closed"}}
                    )
                    break

                headers = {
                            "accept": "application/json",
                            "content-type": "application/json",
                            "APCA-API-KEY-ID": alpaca_api_key,
                            "APCA-API-SECRET-KEY": alpaca_secret_key
                        }
                
                if check_live_trading == True:
                    url = "https://api.alpaca.markets/v2/positions/" + position['orderSymbol']
                else:
                    url = "https://paper-api.alpaca.markets/v2/positions/" + position['orderSymbol']

                response = requests.get(url, headers=headers)
                
                position['currentPrice'] = response.json()['current_price']
        
        # Return combined data
        return {
            "positions": positions
        }
    except Exception as e:
        print(f"Error fetching trader data: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch trader data")

def get_ask_price(response_data, symbol):
    try:
        # First, make sure response_data is parsed from JSON if it's a string
        if isinstance(response_data, str):
            response_data = json.loads(response_data)
        
        ask_price = float(response_data["quotes"][symbol]["ap"])
        return ask_price
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        ask_price = 0.0
    except (KeyError, TypeError) as e:
        print(f"Error accessing data: {e}")
        ask_price = 0.0

def get_bid_price(response_data, symbol):
    try:
        # First, make sure response_data is parsed from JSON if it's a string
        if isinstance(response_data, str):
            response_data = json.loads(response_data)
        
        bid_price = float(response_data["quotes"][symbol]["bp"])
        print("bid_price: ", bid_price)
        return bid_price
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        bid_price = 0.0

class SellAll(BaseModel):
    id: str
    amount : int

@router.post("/sellAmount")
async def sell_all(sellAll: SellAll):
    try:
        position_collection = await get_database("positions")
        try:
            position = await position_collection.find_one({"_id": ObjectId(sellAll.id)})
            orderSymbol = ""
            if position:
                orderSymbol = position["orderSymbol"]
            else:
                raise ValueError(f"No position found with ID: {sellAll.id}")
            # print("orderSymbol: ", orderSymbol)
            # print("position: ", position)

            position_amount = position.get("amount")
            position_soldAmount = position.get("soldAmount")
            userID = position.get("userID")

            trader_collection = await get_database("traders")
            brokerage_collection = await get_database("brokerageCollection")
            trader = await trader_collection.find_one({"_id": ObjectId(userID)})
            brokerage = await brokerage_collection.find_one({"_id": ObjectId(trader["brokerageName"])})

            alpaca_api_key = brokerage["API_KEY"]
            alpaca_secret_key = brokerage["SECRET_KEY"]
            check_live_trading = brokerage["liveTrading"]

            paper_url = os.getenv("PAPER_URL")
            
            payload = {
                "type": "market",
                "time_in_force": "day",
                "symbol": orderSymbol,
                "qty":  sellAll.amount,
                "side": "sell",
            }
            headers = {
                        "accept": "application/json",
                        "content-type": "application/json",
                        "APCA-API-KEY-ID": alpaca_api_key,
                        "APCA-API-SECRET-KEY": alpaca_secret_key
                    }
            if check_live_trading == True:
                url = "https://api.alpaca.markets/v2/orders"
            else:
                url = f"{paper_url}/v2/orders"

            response = requests.post(url, json=payload, headers=headers)
            print("response: ", response.json())
            tradingId = response.json()["id"]

            if(response.status_code == 200):
                await asyncio.sleep(2)
                if check_live_trading == True:
                    url = "https://api.alpaca.markets/v2/orders?status=all&symbols="+orderSymbol
                else:
                    url = "https://paper-api.alpaca.markets/v2/orders?status=all&symbols="+orderSymbol
                response = requests.get(url, headers=headers)

                price = 0
                for order in response.json():
                    if order["id"] == tradingId:
                        closePrice = order["filled_avg_price"]
                        
                        exitTimestamp = order["filled_at"]

                        if (position_soldAmount + sellAll.amount) < position_amount:
                            await position_collection.update_one(
                                {"_id": ObjectId(sellAll.id)},
                                {"$set": { "closePrice": closePrice, "soldAmount": position_soldAmount + sellAll.amount}}
                            )
                        elif (position_soldAmount + sellAll.amount) == position_amount or (position_soldAmount + sellAll.amount) > position_amount:
                            await position_collection.update_one(
                                {"_id": ObjectId(sellAll.id)},
                                {"$set": {"status": "closed", "closePrice": closePrice, "soldAmount": position_amount, "exitDate": exitTimestamp}}
                            )
                        return {"message": "Sell order processed successfully", "status": "success", "exitPrice": price}
                    break;

                return 200
            else:
                return 422
        except Exception as e:
            print(f"Error updating position: {e}")
            raise HTTPException(status_code=500, detail="Failed to update position")
        
    except Exception as e:
        print(f"Error selling all positions: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to sell all positions")


class StartStopTrader(BaseModel):
    id: str

@router.post("/startStopTrader")
async def start_stop_trader(startStopTrader: StartStopTrader):
    try:
        trader_collection = await get_database("traders")
        trader = await trader_collection.find_one({"_id": ObjectId(startStopTrader.id)})
        if trader:
            trader_status = trader["status"]
            if trader_status == "stop":
                result = await trader_collection.update_one(
                    {"_id": ObjectId(startStopTrader.id)},
                    {"$set": {"status": "start"}}
                )
            else:
                result = await trader_collection.update_one(
                    {"_id": ObjectId(startStopTrader.id)},
                    {"$set": {"status": "stop"}}    
                )
        return {"message": "Trader status updated successfully"}
    except Exception as e:
        print(f"Error updating trader status: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update trader status")

class StartStopAnalyst(BaseModel):
    id: str

@router.post("/startStopAnalyst")
async def start_stop_analyst(startStopAnalyst: StartStopAnalyst):
    try:
        analyst_collection = await get_database("analyst")
        analyst = await analyst_collection.find_one({"_id": ObjectId(startStopAnalyst.id)})
        if analyst:
            analyst_status = analyst["status"]
            if analyst_status == "stop":
                result = await analyst_collection.update_one(
                    {"_id": ObjectId(startStopAnalyst.id)},
                    {"$set": {"status": "start"}}
                )
            else:
                result = await analyst_collection.update_one(
                    {"_id": ObjectId(startStopAnalyst.id)},
                    {"$set": {"status": "stop"}}
                )
        return {"message": "Analyst status updated successfully"}
    except Exception as e:
        print(f"Error updating analyst status: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update analyst status")
