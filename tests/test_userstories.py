import sys
import os
import pytest
from nicegui.testing import User
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.models import Base
import src.main as main
import src.services as services
import logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

pytest_plugins = ['nicegui.testing.user_plugin']


@pytest.fixture(autouse=True)
def process_log_messages_and_check_login(caplog):
    caplog.set_level(logging.INFO, logger="matekasse")
    yield
    # Check for login failures in the logs after each test
    login_failures = [r for r in caplog.records if r.levelname == 'WARNING' and 'Login failed for' in r.getMessage()]
    assert not login_failures, f"Login failed during test: {[r.getMessage() for r in login_failures]}"


@pytest.fixture(autouse=True, scope='function')
def in_memory_db(monkeypatch):
    # Create a new in-memory SQLite engine and session for each test
    engine = create_engine('sqlite:///:memory:', connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    # Patch the get_db dependency in main.py
    monkeypatch.setattr(main, 'get_db', override_get_db)
    # Patch the SessionLocal and engine in main.py (if used elsewhere)
    monkeypatch.setattr(main, 'SessionLocal', TestingSessionLocal, raising=False)
    monkeypatch.setattr(main, 'engine', engine, raising=False)
    # Also patch in src.services and src.database to ensure all use the in-memory DB
    import src.services as services_mod
    import src.database as database_mod
    monkeypatch.setattr(services_mod, 'SessionLocal', TestingSessionLocal, raising=False)
    monkeypatch.setattr(services_mod, 'engine', engine, raising=False)
    monkeypatch.setattr(database_mod, 'SessionLocal', TestingSessionLocal, raising=False)
    monkeypatch.setattr(database_mod, 'engine', engine, raising=False)
    yield
    # No teardown needed, as the DB is in-memory and will be discarded


# User story: Login and view balance
@pytest.mark.module_under_test(main)
async def test_login_and_see_balance(user: User):
    # Ensure user exists
    with main.SessionLocal() as db:
        if not services.get_user_by_email(db, 'user@matekasse.de'):
            services.create_user(db, 'user@matekasse.de', 'user', is_admin=False)
    await user.open('/login')
    user.find('E-Mail').type('user@matekasse.de')
    user.find('Password').type('user')
    user.find('Login').click()
    await user.should_see('Welcome, user@matekasse.de')
    await user.should_see('Balance:')


# User story: View beverage list
@pytest.mark.module_under_test(main)
async def test_beverage_list_visible(user: User):
    # Ensure user exists
    with main.SessionLocal() as db:
        if not services.get_user_by_email(db, 'user@matekasse.de'):
            services.create_user(db, 'user@matekasse.de', 'user', is_admin=False)
    await user.open('/login')
    user.find('E-Mail').type('user@matekasse.de')
    user.find('Password').type('user')
    user.find('Login').click()
    await user.open('/shop')
    await user.should_see('Buy Beverage')


# User story: Purchase beverage
@pytest.mark.module_under_test(main)
async def test_purchase_beverage(user: User):
    # Ensure user and beverage exist
    with main.SessionLocal() as db:
        u = services.create_user(db, 'user@matekasse.de', 'user', is_admin=False)
        services.update_user_balance(db, u.id, 10.0)  # Set initial balance
        services.create_beverage(db, 'TestCola', 2.0, 10)
    await user.open('/login')
    user.find('E-Mail').type('user@matekasse.de')
    user.find('Password').type('user')
    user.find('Login').click()
    await user.open('/shop')
    user.find('Buy').click()
    await user.should_see('Balance: 8.00 €')


# User story: Record deposit
@pytest.mark.module_under_test(main)
async def test_deposit(user: User):
    # Ensure user exists
    with main.SessionLocal() as db:
        if not services.get_user_by_email(db, 'user@matekasse.de'):
            services.create_user(db, 'user@matekasse.de', 'user', is_admin=False)
    await user.open('/login')
    user.find('E-Mail').type('user@matekasse.de')
    user.find('Password').type('user')
    user.find('Login').click()
    await user.open('/shop')
    user.find('Amount (€)').type('5')
    user.find('Deposit').click()
    await user.should_see('Deposit recorded')


# User story: View transaction history
@pytest.mark.module_under_test(main)
async def test_transaction_history(user: User):
    # Ensure user exists
    with main.SessionLocal() as db:
        if not services.get_user_by_email(db, 'user@matekasse.de'):
            services.create_user(db, 'user@matekasse.de', 'user', is_admin=False)
    await user.open('/login')
    user.find('E-Mail').type('user@matekasse.de')
    user.find('Password').type('user')
    user.find('Login').click()
    await user.open('/transactions')
    await user.should_see('Transaction History')


# Admin story: Login and access admin panel
@pytest.mark.module_under_test(main)
async def test_admin_login_and_panel(user: User):
    # Ensure admin exists
    with main.SessionLocal() as db:
        if not services.get_user_by_email(db, 'admin@matekasse.de'):
            services.create_user(db, 'admin@matekasse.de', 'admin', is_admin=True)
    await user.open('/login')
    user.find('E-Mail').type('admin@matekasse.de')
    user.find('Password').type('admin')
    user.find('Login').click()
    await user.should_see('Admin')
    user.find('Admin').click()
    await user.should_see('Admin Panel')


# Admin story: Create user
@pytest.mark.module_under_test(main)
async def test_admin_create_user(user: User):
    # Ensure admin exists
    with main.SessionLocal() as db:
        if not services.get_user_by_email(db, 'admin@matekasse.de'):
            services.create_user(db, 'admin@matekasse.de', 'admin', is_admin=True)
    await user.open('/login')
    user.find('E-Mail').type('admin@matekasse.de')
    user.find('Password').type('admin')
    user.find('Login').click()
    await user.should_see('Admin')
    user.find('Admin').click()
    await user.should_see('Create user')
    user.find('E-Mail').type('neu@matekasse.de')
    user.find('Password').type('pw')
    user.find('Create user').click()
    await user.should_see('neu@matekasse.de')


# Admin story: Edit user balance
@pytest.mark.module_under_test(main)
async def test_admin_edit_balance(user: User):
    # Ensure admin exists
    with main.SessionLocal() as db:
        if not services.get_user_by_email(db, 'admin@matekasse.de'):
            services.create_user(db, 'admin@matekasse.de', 'admin', is_admin=True)
    await user.open('/login')
    user.find('E-Mail').type('admin@matekasse.de')
    user.find('Password').type('admin')
    user.find('Login').click()
    await user.should_see('Admin')
    user.find('Admin').click()
    await user.should_see('Edit balance')
    user.find('Edit balance').click()
    await user.should_see('New balance')
    user.find('New balance').type('25')
    user.find('Save').click()
    await user.should_see('Balance: 25.00 €')


# Admin story: Create beverage
@pytest.mark.module_under_test(main)
async def test_admin_create_beverage(user: User):
    # Ensure admin exists
    with main.SessionLocal() as db:
        if not services.get_user_by_email(db, 'admin@matekasse.de'):
            services.create_user(db, 'admin@matekasse.de', 'admin', is_admin=True)
    await user.open('/login')
    user.find('E-Mail').type('admin@matekasse.de')
    user.find('Password').type('admin')
    user.find('Login').click()
    await user.should_see('Admin')
    user.find('Admin').click()
    await user.should_see('Neu in Lager')
    user.find('Name').type('Testgetränk')
    user.find('Price (€)').type('1.5')
    user.find('Neu in Lager').type('10')
    user.find('Create beverage').click()
    await user.should_see('Testgetränk | Price: 1.50 € | Stock: 10')


# Admin story: Edit beverage stock
@pytest.mark.module_under_test(main)
async def test_admin_edit_stock(user: User):
    # Ensure admin exists
    with main.SessionLocal() as db:
        if not services.get_user_by_email(db, 'admin@matekasse.de'):
            services.create_user(db, 'admin@matekasse.de', 'admin', is_admin=True)
        # Ensure at least one beverage exists
        beverages = db.query(getattr(services, 'Beverage')).all() if hasattr(services, 'Beverage') else []
        if not beverages:
            if hasattr(services, 'create_beverage'):
                services.create_beverage(db, 'TestCola', 2.0, 10)
    await user.open('/login')
    user.find('E-Mail').type('admin@matekasse.de')
    user.find('Password').type('admin')
    user.find('Login').click()
    await user.should_see('Admin')
    user.find('Admin').click()
    await user.should_see('Edit stock')
    user.find('Edit stock').click()
    user.find('New stock').type('123')
    user.find('Save').click()
    await user.should_see('TestCola | Price: 2.00 € | Stock: 123')


# Admin story: Confirm pending deposit
@pytest.mark.module_under_test(main)
async def test_admin_confirm_deposit(user: User):
    # Ensure admin exists
    with main.SessionLocal() as db:
        if not services.get_user_by_email(db, 'admin@matekasse.de'):
            services.create_user(db, 'admin@matekasse.de', 'admin', is_admin=True)
        if not services.get_user_by_email(db, 'user@matekasse.de'):
            services.create_user(db, 'user@matekasse.de', 'user', is_admin=False)
        # Ensure at least one user exists with a pending deposit
        u = services.get_user_by_email(db, 'user@matekasse.de')
        u.balance = 0.0
        services.create_transaction(
            db, u.id, 10.0, services.TransactionType.DEPOSIT, services.TransactionStatus.PENDING
        )
        db.commit()
    await user.open('/login')
    user.find('E-Mail').type('admin@matekasse.de')
    user.find('Password').type('admin')
    user.find('Login').click()
    await user.should_see('Admin')
    user.find('Admin').click()
    await user.should_see('Confirm')
    user.find('Confirm').click()
    await user.should_see('Balance: 10.00 €')


# Admin story: View all transactions
@pytest.mark.module_under_test(main)
async def test_see_all_transactions(user: User):
    # Ensure admin exists
    with main.SessionLocal() as db:
        if not services.get_user_by_email(db, 'user@matekasse.de'):
            services.create_user(db, 'user@matekasse.de', 'user', is_admin=True)
        # Ensure at least one transaction exists
        u = services.get_user_by_email(db, 'user@matekasse.de')
        services.create_transaction(
            db, u.id, 5.0, services.TransactionType.PURCHASE, services.TransactionStatus.CONFIRMED
        )
        services.create_transaction(
            db, u.id, 10.0, services.TransactionType.DEPOSIT, services.TransactionStatus.PENDING
        )
    await user.open('/login')
    user.find('E-Mail').type('user@matekasse.de')
    user.find('Password').type('user')
    user.find('Login').click()
    await user.should_see('Transactions')
    user.find('Transactions').click()
    await user.should_see('Transaction History')


# Other: Logout
@pytest.mark.module_under_test(main)
async def test_logout(user: User):
    # Ensure user exists
    with main.SessionLocal() as db:
        if not services.get_user_by_email(db, 'user@matekasse.de'):
            services.create_user(db, 'user@matekasse.de', 'user', is_admin=False)
    await user.open('/login')
    user.find('E-Mail').type('user@matekasse.de')
    user.find('Password').type('user')
    user.find('Login').click()
    await user.should_see('Logout')
    user.find('Logout').click()
    await user.should_see('Login')


