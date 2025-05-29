# app/services.py

from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from passlib.context import CryptContext
from src.models import User, Beverage, Transaction, TransactionType, TransactionStatus

# Password hashing context (SRP: Only responsible for authentication)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """Generates a secure hash for the password."""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Compares a plain text password with the stored hash."""
    return pwd_context.verify(plain_password, hashed_password)

def authenticate_user(db: Session, email: str, password: str):
    """Checks login credentials and returns the user or None."""
    user = db.query(User).filter(User.email == email).first()
    if user and verify_password(password, user.hashed_password):
        return user
    return None

def get_user_by_email(db: Session, email: str):
    """Loads a user by email address."""
    return db.query(User).filter(User.email == email).first()

def get_user(db: Session, user_id: int):
    """Loads a user by ID."""
    return db.query(User).filter(User.id == user_id,).first()

def is_admin(user: User) -> bool:
    """Checks if the user has admin rights."""
    return user.is_admin

def create_user(db: Session, email: str, password: str, is_admin: bool = False):
    """Creates a new user (only by admins)."""
    if get_user_by_email(db, email):
        raise HTTPException(status_code=400, detail="Email already registered.")
    user = User(
        email=email,
        hashed_password=hash_password(password),
        is_admin=is_admin
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def list_users(db: Session):
    """Returns all users."""
    return db.query(User).all()

def update_user_balance(db: Session, user_id: int, new_balance: float):
    """Sets the balance of a user (admin only)."""
    user = get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.balance = new_balance
    db.commit()
    db.refresh(user)
    return user

def create_beverage(db: Session, name: str, price: float, stock: int = 0):
    """Adds a new beverage."""
    beverage = Beverage(name=name, price=price, stock=stock)
    db.add(beverage)
    db.commit()
    db.refresh(beverage)
    return beverage

def list_beverages(db: Session):
    """Returns all beverages."""
    return db.query(Beverage).all()

def update_beverage(db: Session, beverage_id: int, name: str = None, price: float = None, stock: int = None):
    """Updates a beverage."""
    beverage = db.query(Beverage).filter(Beverage.id == beverage_id).first()
    if not beverage:
        raise HTTPException(status_code=404, detail="Beverage not found")
    if name is not None:
        beverage.name = name
    if price is not None:
        beverage.price = price
    if stock is not None:
        beverage.stock = stock
    db.commit()
    db.refresh(beverage)
    return beverage

def create_transaction(
    db: Session,
    user_id: int,
    amount: float,
    transaction_type: TransactionType,
    status: TransactionStatus,
):
    """
    Creates a new transaction (purchase or deposit).
    - For purchase: amount is negative, beverage_id must be set.
    - For deposit: amount is positive, beverage_id is None.
    """
    transaction = Transaction(
        user_id=user_id,
        amount=amount,
        type=transaction_type,
        status=status
    )
    db.add(transaction)
    # Only adjust balance for confirmed transactions
    user = get_user(db, user_id)
    if status == TransactionStatus.CONFIRMED:
        user.balance += amount
    db.commit()
    db.refresh(transaction)
    return transaction

def confirm_transaction(db: Session, transaction_id: int):
    """Confirms a pending transaction (e.g., deposit by admin)."""
    transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    if transaction.status == TransactionStatus.CONFIRMED:
        raise HTTPException(status_code=400, detail="Transaction already confirmed")
    transaction.status = TransactionStatus.CONFIRMED
    # Adjust balance
    user = get_user(db, transaction.user_id)
    user.balance += transaction.amount
    db.commit()
    db.refresh(transaction)
    return transaction

def get_transactions_for_user(db: Session, user_id: int):
    """Returns all transactions of a user, sorted by date."""
    return db.query(Transaction).filter(Transaction.user_id == user_id).order_by(Transaction.timestamp.desc()).all()

def get_all_pending_transactions(db: Session):
    """Returns all unconfirmed (pending) transactions."""
    return db.query(Transaction).filter(Transaction.status == TransactionStatus.PENDING).all()
