from pydantic import BaseModel

class AnalystCreate(BaseModel):
    name: str
    type: str

    class Config:
        json_schema_extra = {
            "example": {
                "name": "John Doe",
                "type": "Technical"
            }
        }

class Analyst(BaseModel):
    name: str
    type: str

    class Config:
        json_schema_extra = {
            "example": {
                "name": "John Doe",
                "type": "Technical"
            }
        } 