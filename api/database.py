from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
from .models.analyst import Analyst

# Load environment variables
load_dotenv()

async def get_database(collection_name: str):
    try:
        MONGODB_URL = os.getenv("MONGODB_URL")
        client = AsyncIOMotorClient(MONGODB_URL)
        
        # Get list of all databases
        dbs = await client.list_database_names()
        
        # Check if optionsTrading database exists
        if "optionsTrading" not in dbs:
            print("Creating optionsTrading database...")
            # Create database by inserting a document
            db = client.get_database("optionsTrading")
            await db.create_collection("traders")  # Create traders collection
            print("Created optionsTrading database with collections")
        
        # Get database and collection
        db = client.get_database("optionsTrading")
        
        # Check if collection exists
        collections = await db.list_collection_names()

        if "analyst" not in collections:
            print("Creating analyst collection with initial data...")
            analyst_collection = db.get_collection("analyst")
            
            # Initial analysts data
            initial_analysts = [{
                    "name": "John",
                    "type": "analyst1"
                },
                {
                    "name": "WiseGuy",
                    "type": "analyst2"
                },
                {
                    "name": "Tommy",
                    "type": "analyst3"
                },
                {
                    "name": "Johnny",
                    "type": "analyst4"
                }]
            await analyst_collection.insert_many(initial_analysts)
            print("Created analyst collection with all initial data")
        
        collection = db.get_collection(collection_name)
        return collection
    
    except Exception as e:
        print(f"Database connection error: {str(e)}")
        raise HTTPException(status_code=500, detail="Database connection failed")

async def init_analyst_collection():
    try:
        MONGODB_URL = os.getenv("MONGODB_URL")
        client = AsyncIOMotorClient(MONGODB_URL)
        db = client.get_database("optionsTrading")
        
        # Check if collection exists
        collections = await db.list_collection_names()
        if "analyst" not in collections:
            print("Creating analyst collection with first row...")
            analyst_collection = db.get_collection("analyst")
            
            # First row of data
            first_analyst = [{
                    "name": "John",
                    "type": "analyst1"
                },
                {
                    "name": "WiseGuy",
                    "type": "analyst2"
                },
                {
                    "name": "Tommy",
                    "type": "analyst3"
                },
                {
                    "name": "Johnny",
                    "type": "analyst4"
                }]
            await analyst_collection.insert_many(first_analyst)
            print("Created analyst collection with first row of data")
        
        client.close()
    except Exception as e:
        print(f"Error initializing analyst collection: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to initialize analyst collection")