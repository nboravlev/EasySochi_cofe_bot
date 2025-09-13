from sqlalchemy import Column, Integer, String, Numeric
from sqlalchemy.orm import relationship
from db.db import Base

class Add(Base):
    __tablename__ = "adds"
    __table_args__ = {"schema": "public"}
    
    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False, unique=True)
    price = Column(Numeric(4,1), nullable=False)

    # Bidirectional relationship
    # Связи
    drink_adds = relationship(
        "DrinkAdd",
        back_populates="add",
        cascade="all, delete-orphan"
    )
    order_adds = relationship(
        "OrderAdd",
        back_populates="add"
    )