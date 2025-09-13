from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from datetime import datetime
from db.db import Base
import re

class Size(Base):
    __tablename__ = "sizes"
    __table_args__ =  {"schema": "public"}


    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False, unique=True)
    volume_ml = Column(Integer, nullable=False)

    # Bidirectional relationship
    drink_sizes = relationship("DrinkSize",back_populates="sizes")
