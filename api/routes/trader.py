from fastapi import APIRouter, HTTPException
from ..database import get_database
from bson import ObjectId
from pydantic import BaseModel
from ..models.brokerage import Brokerage
import os
import requests

router = APIRouter()

# @router.get("/getTraders")
# async def get_traders():
#     try:
#         trader_collection = await get_database("traders")
#         traders = await trader_collection.find().to_list(1000)
        
#         # Convert ObjectId to string for JSON serialization
#         for trader in traders:
#             trader["_id"] = str(trader["_id"])
#             if "user_id" in trader:
#                 trader["user_id"] = str(trader["user_id"])
                
#         return traders
#     except Exception as e:
#         print(f"Error fetching traders: {str(e)}")
#         raise HTTPException(status_code=500, detail="Failed to fetch traders")

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


# @router.get("/getAnalysts")
# async def get_analysts():
#     try:
#         analyst_collection = await get_database("analyst")
#         analysts = await analyst_collection.find().to_list(1000)
        
#         # Convert ObjectId to string for JSON serialization
#         for analyst in analysts:
#             analyst["_id"] = str(analyst["_id"])
                
#         return analysts
#     except Exception as e:
#         print(f"Error fetching analysts: {str(e)}")
#         raise HTTPException(status_code=500, detail="Failed to fetch analysts")

# class UpdateBrokerage(BaseModel):
#     traderId: str
#     brokerageName : str
    

# @router.post("/updateBrokerage")
# async def update_brokerage(brokerage: UpdateBrokerage):
#     try:
#         trader_collection = await get_database("traders")
#         result = await trader_collection.update_one(
#             {"_id": ObjectId(brokerage.traderId)},
#             {"$set": {"brokerageName": brokerage.brokerageName}}
#         )
#         return {"message": "Brokerage updated successfully"}
#     except Exception as e:
#         print(f"Error updating brokerage: {str(e)}")
#         raise HTTPException(status_code=500, detail="Failed to update brokerage")

