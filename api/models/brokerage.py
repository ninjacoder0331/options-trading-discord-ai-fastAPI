from pydantic import BaseModel

class BrokerageCreate(BaseModel):
    brokerage_name: str
    brokerage_type: str
    login_name: str
    password: str
    account: str

    class Config:
        json_schema_extra = {
            "example": {
                "brokerage_name": "Zerodha",
                "brokerage_type": "discount",
                "login_name": "trader123",
                "password": "securepassword123",
                "account": "AB1234"
            }
        }

class Brokerage(BaseModel):
    brokerage_name: str
    brokerage_type: str
    login_name: str
    password: str
    account: str

    class Config:
        json_schema_extra = {
            "example": {
                "brokerage_name": "Zerodha",
                "brokerage_type": "discount",
                "login_name": "trader123",
                "password": "securepassword123",
                "account": "AB1234"
            }
        } 
