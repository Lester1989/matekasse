from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Enum

import enum
from datetime import datetime
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

# Enum für Transaktionstypen
class TransactionType(enum.Enum):
    PURCHASE = "purchase"
    DEPOSIT = "deposit"

# Enum für Transaktionsstatus
class TransactionStatus(enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    balance = Column(Float, default=0.0)
    is_admin = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Beverage(Base):
    __tablename__ = "beverages"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)
    price = Column(Float)
    stock = Column(Integer)

class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    amount = Column(Float)
    type = Column(Enum(TransactionType))
    status = Column(Enum(TransactionStatus))
    timestamp = Column(DateTime, default=datetime.utcnow)
