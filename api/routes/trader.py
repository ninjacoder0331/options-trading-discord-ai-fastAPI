from fastapi import APIRouter, HTTPException
from ..database import get_database
from bson import ObjectId
from pydantic import BaseModel
from ..models.brokerage import Brokerage
from ..models.trader import Position
import os
from datetime import datetime
import requests
import json

router = APIRouter()




@router.get("/getTraders")
async def get_traders():
    try:
        trader_collection = await get_database("traders")
        traders = await trader_collection.find().to_list(1000)
        
        # Convert ObjectId to string for JSON serialization
        for trader in traders:
            trader["_id"] = str(trader["_id"])
            if "user_id" in trader:
                trader["user_id"] = str(trader["user_id"])
                
        return traders
    except Exception as e:
        print(f"Error fetching traders: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch traders")

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

#         # Get API credentials from environment variables
#         # API_KEY = os.getenv("TRADESTATION_KEY")
#         # API_SECRET = os.getenv("TRADESTATION_SECRET")
#         # LOGIN_ID = os.getenv("LOGIN_ID")
        
#         # # Establish your client
#         # client = a.easy_client(API_KEY, API_SECRET, "redirect")

#         # Call your endpoint
#         # account = client.user_accounts()
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



@router.post("/addPosition")
async def add_position(position: Position):
    try:
        position_collection = await get_database("positions")
        # Convert position to dict and add current time
        position_dict = position.model_dump()
        position_dict["created_at"] = datetime.now()
        
        # print("position: ", position_dict)
        result = await position_collection.insert_one(position_dict)
        url = "https://paper-api.alpaca.markets/v2/orders"
        payload = {
            "type": "market",
            "time_in_force": "day",
            "side": position.side,
            "qty": position.quantity,
            "symbol": position.orderSymbol,
            
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
        print("response: ", response.text)

        # print("result: ", result)
        return {"message": "Position added successfully"}
    except Exception as e:
        print(f"Error adding position: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to add position")
    
# get Traders Data
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
                position["created_at"] = position["created_at"].isoformat()
            if position['orderSymbol'] != '':

                alpaca_api_key = os.getenv("ALPACA_API_KEY")
                alpaca_secret_key = os.getenv("ALPACA_SECRET_KEY")
                headers = {
                            "accept": "application/json",
                            "content-type": "application/json",
                            "APCA-API-KEY-ID": alpaca_api_key,
                            "APCA-API-SECRET-KEY": alpaca_secret_key
                        }

                # url = f"https://data.alpaca.markets/v1beta1/options/quotes/latest?symbols={position['orderSymbol']}&feed=indicative"
                url = f"https://data.alpaca.markets/v1beta1/options/quotes/latest?symbols={position['orderSymbol']}&feed=indicative"
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
        return bid_price
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        bid_price = 0.0
    except (KeyError, TypeError) as e:
        print(f"Error accessing data: {e}")
        bid_price = 0.0

class SellAll(BaseModel):
    id: str

@router.post("/sellAll")
async def sell_all(sellAll: SellAll):
    try:
        position_collection = await get_database("positions")
        # Update the status from "open" to "close" where _id matches
        try:
            print("sellAll.id: ", sellAll.id)
            position = await position_collection.find_one({"_id": ObjectId(sellAll.id)})
            if position:
                orderSymbol = position["orderSymbol"]
            else:
                raise ValueError(f"No position found with ID: {sellAll.id}")
            # print("orderSymbol: ", orderSymbol)

            alpaca_api_key = os.getenv("ALPACA_API_KEY")
            alpaca_secret_key = os.getenv("ALPACA_SECRET_KEY")
            headers = {
                        "accept": "application/json",
                        "content-type": "application/json",
                        "APCA-API-KEY-ID": alpaca_api_key,
                        "APCA-API-SECRET-KEY": alpaca_secret_key
                    }

            url = f"https://data.alpaca.markets/v1beta1/options/quotes/latest?symbols={orderSymbol}&feed=indicative"
            print("url: ", url)
            print("headers: ", headers)
            response = requests.get(url, headers=headers)
            print("response: ", response.text)
            closePrice = get_bid_price(response.text, orderSymbol)

            print("closePrice: ", closePrice)
            await position_collection.update_one(
                {"_id": ObjectId(sellAll.id)},
                {"$set": {"status": "close" , "closePrice": closePrice}}
            )
        except Exception as e:
            print(f"Error updating status: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to update status")

        try:
            orderSymbol = position_collection.find_one({"_id": ObjectId(sellAll.id)})["orderSymbol"]
            quantity = position_collection.find_one({"_id": ObjectId(sellAll.id)})["quantity"]

            url = "https://paper-api.alpaca.markets/v2/orders"
            payload = {
                "type": "market",
                "time_in_force": "day",
                "side": "sell",
                "qty": quantity,
                "symbol": orderSymbol,
                
            }
            response = requests.post(url, json=payload, headers=headers)
            print("response: ", response.text)

        except Exception as e:
            print("Error selling all positions: ", str(e))
        
    except Exception as e:
        print(f"Error selling all positions: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to sell all positions")

        
