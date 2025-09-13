from pydantic import BaseModel
from decimal import Decimal

class AddsOut(BaseModel):
    id: int
    name: str
    price: Decimal

    class Config:
        orm_mode = True
