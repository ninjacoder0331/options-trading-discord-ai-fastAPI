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

@router.get("/getAnalysts")
async def get_analysts():
    try:
        analyst_collection = await get_database("analyst")
        analysts = await analyst_collection.find({}).to_list(1000)
        for analyst in analysts:
            analyst["_id"] = str(analyst["_id"])
        print("analysts", analysts)
        return analysts
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class Analyst(BaseModel):
    name : str
    type : str
    currentId : str

@router.post("/updateAnalyst")
async def update_analyst(analyst: Analyst):
    try:
        print("analyst", analyst)
        analyst_collection = await get_database("analyst")
        startDate = datetime.now()
        if not analyst.currentId == "":
            await analyst_collection.update_one({"_id": ObjectId(analyst.currentId)}, {"$set": {"name": analyst.name, "type": analyst.type, "startDate": startDate}})
            return {"message": "Analyst updated successfully"}
        else:
            await analyst_collection.insert_one({"name": analyst.name, "type": analyst.type , "status": "start", "startDate": startDate})
            return {"message": "Analyst created successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class GetAnalyst(BaseModel):
    currentId : str

@router.post("/deleteAnalyst")
async def get_analyst(analyst: GetAnalyst):
    try:
        analyst_collection = await get_database("analyst")
        await analyst_collection.delete_one({"_id": ObjectId(analyst.currentId)})

        trader_collection = await get_database("trader")
        for i in range(4):
            analyst_field = f"analystId{i+1}"
            trader = await trader_collection.find_one({analyst_field: ObjectId(analyst.currentId)})
            if trader:
                print("match found")
                await trader_collection.update_one({analyst_field: ObjectId(analyst.currentId)}, {"$set": {analyst_field: ""}})
        return {"message": "Analyst deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
