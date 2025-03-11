from pydantic import BaseModel

class TraderCreate(BaseModel):
    name: str
    password: str
    email: str
    role : str = "trader"

class Trader(BaseModel):
    name: str
    password: str
    email: str
    role : str = "trader"

    class Config:
        json_schema_extra = {
            "example": {
                "email": "john_doe@gmail.com",
                "name": "john_doe",
                "password": "securepassword123",
                "role": "trader"
            }
        }

class Position(BaseModel):
    orderSymbol: str
    symbol: str
    quantity: int
    analyst: str
    side: str
    orderType: str
    timeInForce: str
    date: str

    class Config:
        json_schema_extra = {
            "example": {
                "orderSymbol": "AAPL",
                "symbol": "AAPL",
                "quantity": 1,
                "analyst": "John",
                "side": "buy",
                "orderType": "market",
                "timeInForce": "day",
                "date": "2024-03-20"
            }
        }