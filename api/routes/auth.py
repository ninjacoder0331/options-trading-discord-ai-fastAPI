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
from datetime import datetime

router = APIRouter()

# Add this near the top with other initializations
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@router.post("/signup", response_model=dict)
async def create_trader(trader: TraderCreate, request: Request):
    try:
        trader_collection = await get_database("traders")
        # Check if trader exists
        existing_trader = await trader_collection.find_one({"email": trader.email})
        
        if existing_trader:
            # If trader exists, return message without updating
            raise HTTPException(
                status_code=400,
                detail="User already exists"
            )
        
        # Create new trader if doesn't exist
        trader_dict = trader.model_dump()
        trader_dict["password"] = trader_dict["password"]  # Store password directly
        trader_dict["user_id"] = str(ObjectId())
        trader_dict["created_at"] = datetime.now().isoformat()
        trader_dict["status"] = "start"
        trader_dict["stopLoss"] = 0
        trader_dict["brokerageName"] = ""
        trader_dict["API_KEY"] = ""
        trader_dict["SECRET_KEY"] = ""
        trader_dict["profitTaking"] = 0
        result = await trader_collection.insert_one(trader_dict)
        return {"id": str(result.inserted_id)}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class TraderUpdate(BaseModel):
    email: str
    amount: int
    name : str
    password : str
    traderId : str
    stopLoss : float
    profitTaking : float

@router.post("/updateTrader" , response_model=dict)
async def update_trader(trader: TraderUpdate):
    try:
        # print("trader: ", trader)
        trader_collection = await get_database("traders")
        result = await trader_collection.update_one(
            {"_id": ObjectId(trader.traderId)},
            {"$set": trader.model_dump()}
        )
        # print("result: ", result)
        return {"message": "Trader updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class BrokerageTrader(BaseModel):
    traderId: str
    brokerageName: str
    API_KEY: str
    SECRET_KEY: str
    liveTrading: bool

@router.post("/updateBrokerageTrader")
async def update_brokerage_trader(trader: BrokerageTrader):
    try:
        trader_collection = await get_database("brokerageCollection")
        print("trader: ", trader)
        result = await trader_collection.update_one(
            {"_id": ObjectId(trader.traderId)},
            {"$set": {"brokerageName": trader.brokerageName, "API_KEY": trader.API_KEY, "SECRET_KEY": trader.SECRET_KEY, "liveTrading": trader.liveTrading}}
        )
        return {"message": "Brokerage trader updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class DeleteBrokerage(BaseModel):
    traderId: str

@router.post("/deleteBrokerage")
async def delete_brokerage(trader: DeleteBrokerage):
    try:
        trader_collection = await get_database("brokerageCollection")
        result = await trader_collection.delete_one({"_id": ObjectId(trader.traderId)})
        return {"message": "Brokerage deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/traderSignup")
async def traderSignup(trader: TraderUpdate):
    try:

        trader_collection = await get_database("traders")
        existing_trader = await trader_collection.find_one({"email": trader.email})
        if existing_trader:
            raise HTTPException(
                status_code=400,
                detail="User already exists"
            )
        
        trader_dict = trader.model_dump()
        trader_dict["password"] = trader_dict["password"]  # Store password directly
        trader_dict["user_id"] = str(ObjectId())
        trader_dict["created_at"] = datetime.now().isoformat()
        trader_dict["status"] = "start"
        trader_dict["brokerageName"] = ""
        trader_dict["API_KEY"] = ""
        trader_dict["SECRET_KEY"] = ""
        trader_dict["role"] = "trader"
        
        result = await trader_collection.insert_one(trader_dict)
        return {"message": "Trader created successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
class SignInRequest(BaseModel):
    email: str
    password: str

@router.post("/signin")
async def signin(request: Request, credentials: SignInRequest):
    try:
        trader_collection = await get_database("traders")
        # Find trader by email
        trader = await trader_collection.find_one({"email": credentials.email})
        
        if not trader :
            raise HTTPException(
                status_code=401,
                detail="Incorrect email or password"
            )

        if trader["status"] == "stop":
            raise HTTPException(
                status_code=401,
                detail="Account is currently disabled , contact Admin"
            )
        
        # Check if password exists in trader document
        if 'password' not in trader:
            raise HTTPException(
                status_code=401,
                detail="No password set for this account"
            )

        try:
            print("verifying password")
            # Direct password comparison
            if credentials.password != trader['password']:
                raise HTTPException(
                    status_code=401,
                    detail="Incorrect email or password"
                )
            print("password verified")
        except Exception as password_error:
            print(f"Password verification error: {str(password_error)}")
            raise HTTPException(
                status_code=401,
                detail="Password verification failed"
            )
            
        # Create JWT token
        auth_token = jwt.encode(
            {
                "email": trader['email'],
                "user_id": str(trader['_id'])
            },
            os.getenv("SECRET"),
            algorithm="HS256"
        )
        print("auth_token", auth_token)
        print("trader", trader['_id'])
        return {
            "authToken": auth_token,
            "user": {
                "email": trader['email'],
                "user_id": str(trader['_id']),
                "role": trader['role']
            }
        }
        
    except Exception as e:
        print(f"Signin error: {str(e)}")
        raise HTTPException(status_code=401, detail=str(e))


@router.post("/verify")
async def verify_token(request: Request, authorization: Optional[str] = Header(None)):
    try:
        trader_collection = await get_database("traders")
        if not authorization:
            raise HTTPException(
                status_code=401,
                detail="Authorization header missing"
            )
        
        token = authorization.replace("Bearer ", "")
        
        try:
            # Verify and decode the JWT token
            payload = jwt.decode(
                token,
                os.getenv("SECRET"),
                algorithms=["HS256"]
            )
            
            # Find trader by email from token
            trader = await trader_collection.find_one({"email": payload["email"]})
            
            if not trader:
                raise HTTPException(
                    status_code=401,
                    detail="Invalid token"
                )
                
            return {
                "valid": True,
                "user": {
                    "email": trader["email"],
                    "user_id": str(trader["_id"])
                }
            }
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=401,
                detail="Token has expired"
            )
        except jwt.JWTError:
            raise HTTPException(
                status_code=401,
                detail="Invalid token"
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail=str(e)
        )

class ChangePasswordRequest(BaseModel):
    currentPassword: str
    newPassword: str
    confirmPassword: str
    userID: str

@router.post("/changePassword")
async def change_password(changePassword: ChangePasswordRequest):
    try:
        print("changePassword: ", changePassword)
        trader_collection = await get_database("traders")
        trader = await trader_collection.find_one({"password": changePassword.currentPassword, "_id": ObjectId(changePassword.userID)})
        if not trader:
            return 404
            
        if changePassword.newPassword != changePassword.confirmPassword:
            return 402
        
        if changePassword.currentPassword == changePassword.newPassword:
            return 400
            
        
        await trader_collection.update_one(
            {"_id": ObjectId(changePassword.userID)},
            {"$set": {"password": changePassword.newPassword}}
        )
        return 200
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
