from pydantic import BaseModel

class BrokerageCreate(BaseModel):
    brokerageName: str
    brokerage: str
    loginName: str
    password: str
    accountNumber: str
    apiInfo : str
    apiLink : str

    class Config:
        json_schema_extra = {
            "example": {
                "brokerageName": "Zerodha",
                "brokerage": "discount",
                "loginName": "trader123",
                "password": "securepassword123",
                "accountNumber": "AB1234",
                "apiInfo": "apiInfo",
                "apiLink": "apiLink"
            }
        }

class Brokerage(BaseModel):
    brokerageName: str
    brokerage: str
    loginName: str
    password: str
    accountNumber: str
    apiInfo : str
    apiLink : str

    class Config:
        json_schema_extra = {
            "example": {
                "brokerageName": "Zerodha",
                "brokerage": "discount",
                "loginName": "trader123",
                "password": "securepassword123",
                "accountNumber": "AB1234",
                "apiInfo": "apiInfo",
                "apiLink": "apiLink"
            }
        } 
