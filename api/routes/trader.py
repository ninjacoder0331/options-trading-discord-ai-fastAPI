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

load_dotenv()

router = APIRouter()

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

# class Position(BaseModel):
#     email: str
#     symbol: str
#     date: str
#     optionType: str

# @router.post("/addPosition")
# async def update_trader(Position: Position):
#     try:
#         print("Position: ", Position)
#         trader_collection = await get_database("traders")
#         result = await trader_collection.find_one(
#             {"email": Position.email},
#         )
#         id = result["_id"]
#         print("id: ", id)

#         position_collection = await get_database("positions")
#         result = await position_collection.insert_one(
#             {"id": id, "email": Position.email, "symbol": Position.symbol, "date": Position.date, "optionType": Position.optionType}
#         )

#         print("result: ", result)
#         # print("account: ", account)
        
#         return {"message": "Position added successfully"}
#     except Exception as e:
#         print(f"Error adding position: {str(e)}")
#         raise HTTPException(status_code=500, detail="Failed to add position")


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
        print("traderId: ", trader)
        print("traderAnalyst")

        trader_collection = await get_database("traders")
        trader = await trader_collection.find_one({"_id": ObjectId(trader.traderId)})
        print("trader: ", trader)
        if trader:
            trader["_id"] = str(trader["_id"])
        return trader
    except Exception as e:
        print(f"Error getting trader analysts: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get trader analysts")

@router.post("/addPosition")
async def add_position(position: Position):
    try:
        print("position: ", position)
        trader_collection = await get_database("traders")
        trader = await trader_collection.find_one({"_id": ObjectId(position.userID)})
        trader_amount = 0
        amount = 0

        print("trader: ", trader)

        if trader:
            trader_id = trader["_id"]
            trader_amount = trader["amount"]
            print("trader_amount: ", trader_amount)
            if trader_amount < position.entryPrice * 100:
                raise HTTPException(status_code=404, detail="Insufficient balance")
            else :
                amount = int(trader_amount / (position.entryPrice * 100))
                print("amount: ", amount)
        else:
            raise HTTPException(status_code=404, detail="User not found")
        position.amount = amount
        position_collection = await get_database("positions")

        url = "https://paper-api.alpaca.markets/v2/orders"
        payload = {
            "type": "market",
            "time_in_force": "day",
            "symbol": position.orderSymbol,
            "qty": position.amount,
            "side": "buy",
        }

        alpaca_api_key = os.getenv("ALPACA_API_KEY")
        alpaca_secret_key = os.getenv("ALPACA_SECRET_KEY")
        headers = {
                    "accept": "application/json",
                    "content-type": "application/json",
                    "APCA-API-KEY-ID": alpaca_api_key,
                    "APCA-API-SECRET-KEY": alpaca_secret_key
                }

        print("payload: ", payload)
        response = requests.post(url, json=payload, headers=headers)
        print("response: ", response.status_code)

        if response.status_code == 200:
            print("Success!")
             
            # Convert position to dict and add current time
            position_dict = position.model_dump()
            position_dict["created_at"] = datetime.now().isoformat()
            # await trader_collection.update_one(
            #     {"_id": ObjectId(position.userID)},
            #     {"$set": {"amount": trader_amount - amount * 100 * position.entryPrice}}
            # )
            
            # print("position: ", position_dict)
            result = await position_collection.insert_one(position_dict)
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
    result = await get_position_status_by_traderId("close", traderId.traderId)
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
        positions = await position_collection.find({"status": position, "userID": traderId}).to_list(1000)
        if not positions:
            print("No open positions found")
            positions = []

        for position in positions:
            position["_id"] = str(position["_id"])
            # Convert datetime to string if it exists
            if "created_at" in position:
                position["created_at"] = position["created_at"]
            if position['orderSymbol'] != '' and position['status'] == "open":

                alpaca_api_key = os.getenv("ALPACA_API_KEY")
                alpaca_secret_key = os.getenv("ALPACA_SECRET_KEY")
                headers = {
                            "accept": "application/json",
                            "content-type": "application/json",
                            "APCA-API-KEY-ID": alpaca_api_key,
                            "APCA-API-SECRET-KEY": alpaca_secret_key
                        }
                
                print("headers: ", headers)
                print("position['orderSymbol']: ", position['orderSymbol'])

                # url = f"https://data.alpaca.markets/v1beta1/options/quotes/latest?symbols={position['orderSymbol']}&feed=indicative"
                url = f"https://data.alpaca.markets/v1beta1/options/quotes/latest?symbols={position['orderSymbol']}"
                response = requests.get(url, headers=headers)
                print("response: ", response.text)
                # if position == "open":
                result = get_bid_price(response.text, position['orderSymbol'])
                position['currentPrice'] = result
                # else:
                #     result = get_ask_price(response.text, position['orderSymbol'])
                
                # print(position['currentPrice'])
                # print("response: ", response.text).
        
        # Return combined data
        return {
            "positions": positions
        }
    except Exception as e:
        print(f"Error fetching trader data: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch trader data")

@router.get("/getClosePositions")
async def get_closed_positions():
    result = await get_position_status("close")
    return result


async def get_position_status(position):
    try:
        # Get positions data
        position_collection = await get_database("positions")
        positions = await position_collection.find(
            {"status": position}
        ).to_list(1000)

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
                        {"$set": {"status": "close"}}
                    )
                    break


                alpaca_api_key = os.getenv("ALPACA_API_KEY")
                alpaca_secret_key = os.getenv("ALPACA_SECRET_KEY")
                headers = {
                            "accept": "application/json",
                            "content-type": "application/json",
                            "APCA-API-KEY-ID": alpaca_api_key,
                            "APCA-API-SECRET-KEY": alpaca_secret_key
                        }
                
                print("headers: ", headers)
                print("position['orderSymbol']: ", position['orderSymbol'])

                # url = f"https://data.alpaca.markets/v1beta1/options/quotes/latest?symbols={position['orderSymbol']}&feed=indicative"
                url = f"https://data.alpaca.markets/v1beta1/options/quotes/latest?symbols={position['orderSymbol']}"
                response = requests.get(url, headers=headers)
                print("response: ", response.text)
                # if position == "open":
                result = get_bid_price(response.text, position['orderSymbol'])
                position['currentPrice'] = result
                # else:
                #     result = get_ask_price(response.text, position['orderSymbol'])
                
                # print(position['currentPrice'])
                # print("response: ", response.text).
        
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
        # Update the status from "open" to "close" where _id matches
        try:
            # print("sellAll.id: ", sellAll.id)
            position = await position_collection.find_one({"_id": ObjectId(sellAll.id)})
            orderSymbol = ""
            if position:
                orderSymbol = position["orderSymbol"]
            else:
                raise ValueError(f"No position found with ID: {sellAll.id}")
            print("orderSymbol: ", orderSymbol)
            print("position: ", position)

            position_amount = position.get("amount")
            position_soldAmount = position.get("soldAmount")
            userID = position.get("userID")

            alpaca_api_key = os.getenv("ALPACA_API_KEY")
            alpaca_secret_key = os.getenv("ALPACA_SECRET_KEY")
            
            payload = {
                "type": "market",
                "time_in_force": "day",
                "symbol": orderSymbol,
                "qty":  sellAll.amount,
                "side": "sell",
            }

            print("payload" , payload)
            
            headers = {
                        "accept": "application/json",
                        "content-type": "application/json",
                        "APCA-API-KEY-ID": alpaca_api_key,
                        "APCA-API-SECRET-KEY": alpaca_secret_key
                    }
            url = "https://paper-api.alpaca.markets/v2/orders"

            # print("url: ", url)
            # print("payload: ", payload)
            # print("headers: ", headers)
            # print("url: ", url)
            response = requests.post(url, json=payload, headers=headers)
            print("response_status_code: ", response.status_code)
            print("response: ", response.json())
            if(response.status_code == 200):

                print("orderSymbol: ", orderSymbol)
                url = f"https://data.alpaca.markets/v1beta1/options/quotes/latest?symbols={orderSymbol}"
                response = requests.get(url, headers=headers)
                print("response: ", response.text)
                closePrice = get_bid_price(response.text, orderSymbol)

                print("closePrice: ", closePrice)
                print("userID: ", userID)

                # current_sold_usd_amount = sellAll.amount * closePrice * 100
                # trader_collection = await get_database("traders")
                # trader = await trader_collection.find_one({"_id": ObjectId(userID)})
                # trader_amount = trader["amount"]
                # trader_amount = trader_amount + current_sold_usd_amount

                # print("trader_amount: ", trader_amount)
                # await trader_collection.update_one(
                #     {"_id": ObjectId(userID)},
                #     {"$set": {"amount": trader_amount}}
                # )
                
                # print("closePrice: ", closePrice)
                # First get the current document to check if soldAmount exists
                if (position_soldAmount + sellAll.amount) < position_amount:
                    await position_collection.update_one(
                        {"_id": ObjectId(sellAll.id)},
                        {"$set": { "closePrice": closePrice, "soldAmount": position_soldAmount + sellAll.amount}}
                    )

                elif (position_soldAmount + sellAll.amount) == position_amount or (position_soldAmount + sellAll.amount) > position_amount:
                    await position_collection.update_one(
                        {"_id": ObjectId(sellAll.id)},
                        {"$set": {"status": "close", "closePrice": closePrice, "soldAmount": position_amount, "exitDate": datetime.now().isoformat()}}
                    )
                
                

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
