from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Boolean,
    DateTime,
    ForeignKey,
    Numeric,
    CheckConstraint,
    text,
    BIGINT
)
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry
from datetime import datetime
from db.db import Base

from decimal import Decimal


class DrinkSize(Base):
    __tablename__ = "drink_sizes"
    __table_args__ = {"schema": "public"}

    id = Column(Integer, primary_key=True)
    drink_id = Column(Integer, ForeignKey("public.drinks.id", ondelete="CASCADE"), nullable=False)
    size_id = Column(Integer, ForeignKey("public.sizes.id", ondelete="CASCADE"), nullable=False)
    price = Column(Numeric(5,1), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, nullable=False, default=True, server_default=text("true"))


    # отношения (опционально)
    drink = relationship("Drink", back_populates="drink_sizes")
    sizes = relationship("Size", back_populates = "drink_sizes")
    orders = relationship("Order", back_populates="drink_size")

