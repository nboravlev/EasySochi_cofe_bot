# schemas/apartment_type.py
from pydantic import BaseModel

class DrinkTypeOut(BaseModel):
    id: int
    name: str

    class Config:
        orm_mode = True
