from sqlalchemy import Column, Integer, ForeignKey, Boolean, text
from sqlalchemy.orm import relationship
from db.db import Base

class DrinkAdd(Base):
    __tablename__ = "drink_adds"
    __table_args__ = {"schema": "public"}
    
    id = Column(Integer, primary_key=True)
    drink_id = Column(Integer, ForeignKey("public.drinks.id", ondelete="CASCADE"),nullable=False)
    add_id = Column(Integer, ForeignKey("public.adds.id", ondelete="CASCADE"),nullable=False)
    is_active = Column(Boolean, nullable=False, default=True, server_default=text("true"))

    # bidirectional relationship
    drink = relationship("Drink", back_populates="drink_adds")
    add = relationship("Add", back_populates="drink_adds")