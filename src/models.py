import enum
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Enum, Float, Integer, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()


# Enum for transaction types
class TransactionType(enum.Enum):
    """Enumeration for transaction types."""

    PURCHASE = "purchase"
    DEPOSIT = "deposit"


# Enum for transaction status
class TransactionStatus(enum.Enum):
    """Enumeration for transaction status."""

    PENDING = "pending"
    CONFIRMED = "confirmed"


class User(Base):
    """Database model for a user."""

    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    balance = Column(Float, default=0.0)
    is_admin = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Beverage(Base):
    """Database model for a beverage."""

    __tablename__ = "beverages"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)
    price = Column(Float)
    stock = Column(Integer)


class Transaction(Base):
    """Database model for a transaction."""

    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    amount = Column(Float)
    type = Column(Enum(TransactionType))
    status = Column(Enum(TransactionStatus))
    timestamp = Column(DateTime, default=datetime.utcnow)
