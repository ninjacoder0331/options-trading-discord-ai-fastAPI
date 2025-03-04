from fastapi import APIRouter, HTTPException
from ..database import get_database
from bson import ObjectId

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

# Optional: Add a GET endpoint for a single trader
@router.get("/{trader_id}")
async def get_trader(trader_id: str):
    try:
        trader_collection = await get_database("traders")
        trader = await trader_collection.find_one({"_id": ObjectId(trader_id)})
        
        if trader:
            # Convert ObjectId to string for JSON serialization
            trader["_id"] = str(trader["_id"])
            if "user_id" in trader:
                trader["user_id"] = str(trader["user_id"])
            return trader
        else:
            raise HTTPException(status_code=404, detail="Trader not found")
    except Exception as e:
        print(f"Error fetching trader: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch trader") 