from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from db.db import Base

class DrinkType(Base):
    __tablename__ = "drink_types"
    __table_args__ = {"schema": "public"}
    
    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False, unique=True)
    
    # Bidirectional relationship
    drinks = relationship("Drink", back_populates="drink_type")
    
 