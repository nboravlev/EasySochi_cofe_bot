from sqlalchemy import (
    Column,
    Integer,
    ForeignKey,
    Boolean,
    DateTime,
    String,
    text
)
from db.db import Base
from sqlalchemy.orm import relationship
from datetime import datetime


class Image(Base):
    __tablename__ = "images"
    __table_args__ = {"schema": "public"}

    id = Column(Integer, primary_key=True)

    drink_id = Column(Integer, ForeignKey("public.drinks.id", ondelete="CASCADE"), nullable=False)

    tg_file_id = Column(String, nullable=False)  # идентификатор файла в Telegram
    is_active = Column(Boolean, nullable=False, default=True, server_default=text("true"))  # включено в выдачу

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Optional: связь с Apartment
    drink = relationship("Drink", back_populates="images")
