from pydantic import BaseModel

class TraderCreate(BaseModel):
    name: str
    password: str
    email: str
    role : str = "trader"
    amount : int = 0

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
    entryPrice : float
    
    childType : str
    userID : str
    amount : int = 0
    soldAmount : int = 0
    exitDate : str = ""
    strikePrice : float

    closePrice : float = 0.0
    status : str = "open"


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
                "date": "2024-03-20",
                "entryPrice": 100,
                "childType": "option",
                "userID": "123",
                "amount": 100,
                "soldAmount": 0,
                "exitDate": "",
                "strikePrice": 100
            }
        }