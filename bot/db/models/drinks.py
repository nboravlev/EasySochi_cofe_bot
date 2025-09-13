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


class Drink(Base):
    __tablename__ = "drinks"
    __table_args__ = {"schema": "public"}

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    type_id = Column(Integer, ForeignKey("public.drink_types.id", ondelete="RESTRICT"), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(BIGINT, 
                    ForeignKey("public.users.tg_user_id", ondelete="CASCADE"),
                    nullable = False, unique = False)
    is_active = Column(Boolean, nullable=False, default=True, server_default=text("true"))
    is_draft = Column(Boolean, nullable=False, default=True, server_default=text("true"))  


    # отношения (опционально)
# Связи
    drink_type = relationship(
        "DrinkType",
        back_populates="drinks",
        lazy="joined"  # всегда загружаем вместе, т.к. это FK
    )
    drink_sizes = relationship(
        "DrinkSize",
        back_populates="drink",
        lazy="selectin",  # оптимально для коллекций
        cascade="all, delete-orphan"
    )
    images = relationship(
        "Image",
        back_populates="drink",
        lazy="selectin"
    )
    drink_adds = relationship(
        "DrinkAdd",
        back_populates="drink",
        lazy="selectin",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Drink(id={self.id}, name={self.name})>"
