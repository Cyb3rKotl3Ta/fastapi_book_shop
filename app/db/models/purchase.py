import enum
from sqlalchemy import Column, Integer, Float, Enum as SQLEnum, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from decimal import Decimal

from app.db.base import Base

class PurchaseStatus(str, enum.Enum):
    IN_CART = "in_cart"
    PENDING = "pending" # Awaiting payment confirmation or processing
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class Purchase(Base):
    __tablename__ = "purchases"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False)
    purchase_date = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(SQLEnum(PurchaseStatus), nullable=False, default=PurchaseStatus.IN_CART)
    cost_at_purchase = Column(Float(precision=10, decimal_return_scale=2), nullable=False)

    # Relationships
    user = relationship("User", back_populates="purchases")
    book = relationship("Book", back_populates="purchases")