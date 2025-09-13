from sqlalchemy import Column, Integer, ForeignKey, Numeric
from sqlalchemy.orm import relationship
from db.db import Base

class OrderAdd(Base):
    __tablename__ = "order_adds"
    __table_args__ = {"schema": "public"}
    
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("public.orders.id", ondelete="RESTRICT"),nullable=False)
    add_id = Column(Integer, ForeignKey("public.adds.id", ondelete="RESTRICT"),nullable=False)

    # bidirectional relationship
    order = relationship("Order", back_populates="order_adds")
    add = relationship("Add", back_populates="order_adds")
