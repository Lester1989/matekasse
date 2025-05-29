# main.py
import logging
import os
from typing import Optional, Generator

from fastapi import Depends
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBasic
from nicegui import app, ui
from sqlalchemy.orm import Session

from src.components.form import form
from src.database import SessionLocal, engine
from src.models import (
    Base,
    TransactionStatus,
    TransactionType,
    User,
    Beverage,
    Transaction,
)
from src.services import (
    authenticate_user,
    confirm_transaction,
    create_beverage,
    create_transaction,
    create_user,
    get_all_pending_transactions,
    get_transactions_for_user,
    get_user,
    get_user_by_email,
    list_beverages,
    list_users,
    update_beverage,
    update_user_balance,
)

security = HTTPBasic()


# Logger setup
logger = logging.getLogger("matekasse")
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
if log_level not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
    log_level = "INFO"
logging.basicConfig(level=log_level, format="%(asctime)s %(levelname)s %(message)s")


# Dependency
def get_db() -> Generator[Session, None, None]:
    """Yield a database session for dependency injection."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(db: Session) -> Optional[User]:
    """Return the currently logged-in user from session storage, or None if not logged in."""
    user_id = app.storage.user.get("user_id")
    if not user_id:
        return None
    return get_user(db, user_id)


@ui.page("/login")
def login_page(db: Session = Depends(get_db)) -> None:
    """Render the login page and handle user authentication."""
    def handle_submit(email: str, password: str) -> None:
        logger.info("Login attempt for %s", email)
        user = authenticate_user(db, email, password)
        if user:
            logger.info("Login success for %s, user_id %s", email, user.id)
            app.storage.user["user_id"] = user.id
            ui.navigate.to("/shop")
        else:
            logger.warning("Login failed for %s", email)
            ui.notify("Login failed", color="negative")
    ui.label("Matekasse").classes("text-h4 mt-16 mb-4 mx-auto ")
    with form(on_submit=handle_submit).classes("mx-auto") as f:
        ui.input("E-Mail").props("key=email type=email").mark("E-Mail")
        ui.input("Password", password=True,password_toggle_button=True).props("key=password type=password").mark(
            "Password"
        ).on("keydown.enter", f.submit)
        f.create_submit_button("Login", icon="login", color="primary").mark("Login")


@ui.page("/logout")
def logout_page() -> None:
    """Log out the current user and redirect to the login page."""
    logger.info("Logout for user %s", app.storage.user.get("user_id"))
    app.storage.user.pop("user_id", None)
    ui.navigate.to("/login")


def user_header(user: User, current_path: str) -> None:
    """Render the fixed header with user info and navigation buttons, highlighting the active route."""
    def nav_button(label: str, route_path: str, mark_name: str) -> None:
        is_active = current_path == route_path
        base_classes = "font-medium border border-blue-700 rounded px-4 py-2 hover:bg-blue-100 transition"
        if is_active:
            classes = f"{base_classes} bg-blue-900 text-white underline"
        else:
            classes = f"{base_classes} bg-white text-blue"
        ui.button(label, on_click=lambda: ui.navigate.to(route_path)).classes(classes).mark(mark_name)

    with ui.row().classes(
        "fixed top-0 left-0 w-full z-50 bg-blue-700 shadow-md items-center px-6 py-3"
    ):
        with ui.column().classes("flex-1 min-w-0"):
            ui.label(f"Welcome, {user.email}").classes(
                "text-lg font-semibold text-white mb-0"
            )
            ui.label(f"Balance: {user.balance:.2f} €").classes(
                "text-sm text-white mt-0"
            )
        with ui.row().classes("gap-2 flex-shrink-0 "):
            nav_button("Shop", "/shop", "Shop")
            nav_button("Transactions", "/transactions", "Transaktionen")
            if user.is_admin:
                nav_button("Admin", "/admin", "Admin")
            nav_button("Logout", "/logout", "Logout")
    ui.space().classes("h-20 block")  # Spacer to push content below fixed header


def render_beverage_row(user: User, db: Session, beverage: Beverage) -> None:
    """Render a row for a beverage with a buy button."""
    with ui.row():
        ui.label(f"{beverage.name} ({beverage.price:.2f} €) - Stock: {beverage.stock}")

        def make_buy_handler(bev):
            def buy():
                if user.balance < bev.price:
                    ui.notify("Not enough balance", color="negative")
                    return
                if bev.stock <= 0:
                    ui.notify("Out of stock", color="negative")
                    return
                create_transaction(
                    db,
                    user.id,
                    -bev.price,
                    TransactionType.PURCHASE,
                    TransactionStatus.CONFIRMED,
                )
                update_beverage(db, bev.id, stock=bev.stock - 1)
                ui.notify(f"{bev.name} purchased!")
                ui.navigate.to("/shop")

            return buy

        ui.button("Buy", on_click=make_buy_handler(beverage)).mark("Kaufen")


def render_deposit_form(user: User, db: Session) -> None:
    """Render the deposit form for users to add balance."""
    def handle_deposit(amount):
        try:
            amount = float(amount)
            if amount <= 0:
                raise ValueError
            create_transaction(
                db, user.id, amount, TransactionType.DEPOSIT, TransactionStatus.PENDING
            )
            ui.notify("Deposit recorded. Waiting for admin confirmation.")
        except Exception as e:
            logger.error("Error processing deposit: %s", e)
            ui.notify("Invalid amount", color="negative")

    with form(on_submit=handle_deposit) as f:
        ui.label("Deposit").classes("text-h5")
        ui.input("Amount (€)").props("key=amount type=number").mark("Betrag (€)")
        f.create_submit_button("Deposit", icon="add", color="primary").mark("Einzahlen")


def render_transaction_table(transactions: list[Transaction]) -> None:
    """Render the transaction history table for the user."""
    ui.label("Transaction History").classes("text-h5")
    ui.table(
        columns=[
            {"name": "date", "label": "Date", "field": "date", "sortable": True},
            {"name": "type", "label": "Type", "field": "type", "sortable": True},
            {
                "name": "amount",
                "label": "Amount (€)",
                "field": "amount",
                "sortable": True,
                "align": "left",
            },
            {"name": "status", "label": "Status", "field": "status", "sortable": True},
        ],
        rows=[
            {
                "date": t.timestamp.strftime("%Y-%m-%d %H:%M"),
                "type": t.type.value,
                "amount": f"{t.amount:.2f}",
                "status": t.status.value,
            }
            for t in transactions
        ],
    )


def render_user_row(db: Session, u: User) -> None:
    """Render a row for a user in the admin user management section."""
    with ui.row():
        ui.label(f"{u.email} ")
        ui.label(f"Balance: {u.balance:.2f} € ")
        ui.label(f"Admin: {u.is_admin}")

        def make_balance_handler(user_id):
            def set_balance():
                def submit_balance(new_balance):
                    try:
                        update_user_balance(db, user_id, float(new_balance))
                        ui.notify("Balance updated")
                        ui.navigate.to("/admin")
                    except Exception:
                        ui.notify("Error updating balance", color="negative")

                with form(on_submit=submit_balance) as f:
                    ui.input("New balance").props("key=new_balance type=number").mark(
                        "Neues Guthaben"
                    )
                    f.create_submit_button("Save", icon="save").mark("Speichern")

            return set_balance

        ui.button("Edit balance", on_click=make_balance_handler(u.id)).mark(
            "Guthaben ändern"
        )


def render_create_user_form(db: Session) -> None:
    """Render the form for admins to create a new user."""
    def handle_create_user(email, password, is_admin):
        try:
            create_user(db, email, password, bool(is_admin))
            logger.info("Admin created user %s (admin=%s)", email, is_admin)
            ui.notify("User created")
        except Exception as e:
            logger.error("Error creating user %s: %s", email, e)
            ui.notify(str(e), color="negative")

    with form(on_submit=handle_create_user) as f:
        ui.input("E-Mail").props("key=email type=email").mark("E-Mail")
        ui.input("Password", password=True).props("key=password type=password").mark(
            "Passwort"
        )
        ui.checkbox("Admin").props("key=is_admin").mark("Admin-Checkbox")
        f.create_submit_button("Create user", icon="person_add").mark("Nutzer anlegen")


def render_beverage_admin_row(db: Session, b: Beverage) -> None:
    """Render a row for a beverage in the admin beverage management section."""
    with ui.row():
        ui.label(f"{b.name} | Price: {b.price:.2f} € | Stock: {b.stock}")

        def make_stock_handler(bev_id):
            def set_stock():
                def submit_stock(new_stock):
                    try:
                        update_beverage(db, bev_id, stock=int(new_stock))
                        ui.notify("Stock updated")
                        ui.navigate.to("/admin")
                    except Exception:
                        ui.notify("Error updating stock", color="negative")

                with form(on_submit=submit_stock) as f:
                    ui.input("New stock").props("key=new_stock type=number").mark(
                        "Neuer Lagerbestand"
                    )
                    f.create_submit_button("Save", icon="save").mark("Speichern")

            return set_stock

        ui.button("Edit stock", on_click=make_stock_handler(b.id)).mark("Lager ändern")


def render_create_beverage_form(db: Session) -> None:
    """Render the form for admins to create a new beverage."""
    def handle_create_beverage(name, price, stock):
        try:
            create_beverage(db, name, float(price), int(stock))
            logger.info(
                "Admin created beverage %s (price=%s, stock=%s)", name, price, stock
            )
            ui.navigate.to("/admin")
            ui.notify("Beverage created")
        except Exception as e:
            logger.error("Error creating beverage %s: %s", name, e)
            ui.notify(str(e), color="negative")

    with form(on_submit=handle_create_beverage) as f:
        ui.input("Name").props("key=name").mark("Name")
        ui.input("Price (€)").props("key=price type=number").mark("Preis (€)")
        ui.input("Stock").props("key=stock type=number").mark("Neu in Lager")
        f.create_submit_button("Create beverage", icon="add").mark("Getränk anlegen")


def render_pending_transaction_row(db: Session, t: Transaction) -> None:
    """Render a row for a pending deposit transaction with a confirm button."""
    with ui.row():
        ui.label(
            f"{t.id} | User: {t.user_id} | Amount: {t.amount:.2f} € | {t.timestamp.strftime('%Y-%m-%d %H:%M')}"
        )

        def make_confirm_handler(tid):
            def confirm():
                try:
                    confirm_transaction(db, tid)
                    ui.notify("Deposit confirmed")
                    ui.navigate.to("/admin")
                except Exception as e:
                    ui.notify(str(e), color="negative")

            return confirm

        ui.button("Confirm", on_click=make_confirm_handler(t.id)).mark("Bestätigen")


@ui.page("/shop")
def purchase_page(db: Session = Depends(get_db)) -> None:
    """Render the shop page for purchasing beverages and making deposits."""
    user = get_current_user(db)
    if not user:
        return RedirectResponse(url="/login")
    user_header(user, "/shop")
    beverages = list_beverages(db)
    with ui.card():
        ui.label("Buy Beverage").classes("text-h5")
        for beverage in beverages:
            render_beverage_row(user, db, beverage)
    render_deposit_form(user, db)


@ui.page("/transactions")
def transactions_page(db: Session = Depends(get_db)) -> None:
    """Render the user's transaction history page."""
    user = get_current_user(db)
    if not user:
        return RedirectResponse(url="/login")
    user_header(user, "/transactions")
    transactions = get_transactions_for_user(db, user.id)
    render_transaction_table(transactions)


@ui.page("/admin")
def admin_page(db: Session = Depends(get_db)) -> None:
    """Render the admin panel for user, beverage, and deposit management."""
    user = get_current_user(db)
    if not user or not user.is_admin:
        return RedirectResponse(url="/login")
    user_header(user, "/admin")
    ui.label("Admin Panel").classes("text-h5")

    # Einzahlungen bestätigen
    ui.label("Open Transactions").classes("text-h6")
    pending = get_all_pending_transactions(db)
    for t in pending:
        render_pending_transaction_row(db, t)
    # Nutzerverwaltung
    ui.label("User Management").classes("text-h6")
    users = list_users(db)
    for u in users:
        render_user_row(db, u)
    render_create_user_form(db)
    # Getränkeverwaltung
    ui.label("Beverage Management").classes("text-h6")
    beverages = list_beverages(db)
    for b in beverages:
        render_beverage_admin_row(db, b)
    render_create_beverage_form(db)


def main() -> None:
    """Initialize the database and run the NiceGUI application."""
    Base.metadata.create_all(bind=engine)
    # Testnutzer/Admin anlegen, falls nicht vorhanden
    with SessionLocal() as db:
        admin_email = os.getenv("INITIAL_ADMIN_USER","admin@matekasse.de")
        admin_pw = os.getenv("INITIAL_ADMIN_PASSWORD","admin")
        if not get_user_by_email(db, admin_email):
            create_user(db, admin_email, admin_pw, is_admin=True)
    ui.run(storage_secret=os.getenv("STORAGE_KEY","some_string_to_encrypt_some_session_data_could_even_be_random"), reload=True)


if __name__ in {"__main__", "__mp_main__"}:
    main()
