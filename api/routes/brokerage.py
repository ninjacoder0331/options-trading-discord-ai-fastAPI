from fastapi import APIRouter, HTTPException, Request, Header, Depends
from ..models.trader import TraderCreate, Trader
from bson import ObjectId
from passlib.context import CryptContext # type: ignore
from pydantic import BaseModel
from typing import Optional
from  ..database import get_database
from ..models.brokerage import BrokerageCreate, Brokerage

router = APIRouter()

# Add this near the top with other initializations

@router.get("/getBrokerages")
async def get_brokerages():
    try:
        brokerage_collection = await get_database("brokerageCollection")
        brokerages = await brokerage_collection.find().to_list(1000)
        
        # Convert ObjectId to string for JSON serialization
        for brokerage in brokerages:
            brokerage["_id"] = str(brokerage["_id"])
                
        return brokerages
    except Exception as e:
        print(f"Error fetching brokerages: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch brokerages")

@router.post("/create", response_model=dict)
async def create_brokerage(brokerage: BrokerageCreate):
    try:
        print("brokerage",brokerage)
        brokerage_collection = await get_database("brokerageCollection")    
        print("checked")    
        
        # Create new brokerage
        brokerage_dict = brokerage.model_dump()
        result = await brokerage_collection.insert_one(brokerage_dict)
        return {"id": str(result.inserted_id)}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Create a model for the delete request
class DeleteBrokerageRequest(BaseModel):
    brokerageId: str

@router.post("/deleteBrokerage")
async def delete_brokerage(request: DeleteBrokerageRequest):
    try:
        brokerage_collection = await get_database("brokerageCollection")
        
        # Convert string ID to ObjectId
        result = await brokerage_collection.delete_one({"_id": ObjectId(request.brokerageId)})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Brokerage not found")
            
        return {"message": "Brokerage deleted successfully"}
    except Exception as e:
        print(f"Error deleting brokerage: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete brokerage")
