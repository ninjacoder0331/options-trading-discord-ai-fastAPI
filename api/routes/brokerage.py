from fastapi import APIRouter, HTTPException, Request, Header, Depends
# from fastapi.security import OAuth2PasswordRequestForm
from ..models.trader import TraderCreate, Trader
from bson import ObjectId
from passlib.context import CryptContext # type: ignore
import jwt # type: ignore
import os
from pydantic import BaseModel
from typing import Optional
from  ..database import get_database
from ..models.brokerage import BrokerageCreate, Brokerage

router = APIRouter()

# Add this near the top with other initializations

@router.get("/getBrokerages")
async def get_brokerages():
    try:
        brokerage_collection = await get_database("brokerage")
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
        brokerage_collection = await get_database("brokerage")        
        # Check if brokerage exists
        existing_brokerage = await brokerage_collection.find_one({"name": brokerage.name})
        
        if existing_brokerage:
            raise HTTPException(
                status_code=400,
                detail="Brokerage with this name already exists"
            )
        
        # Create new brokerage
        brokerage_dict = brokerage.model_dump()
        result = await brokerage_collection.insert_one(brokerage_dict)
        return {"id": str(result.inserted_id)}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

