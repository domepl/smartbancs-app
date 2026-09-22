from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import engine, get_db
from app.models import Account

app = FastAPI(
    title="SmartBancs API",
    description="MVP API para Smartbancs",
    version="1.0.0",
)


@app.get("/")
def root():
    return {
        "application": "SmartBancs API",
        "status": "running"
    }


@app.get("/health")
def health_check():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        return {
            "status": "UP",
            "database": "UP",
        }

    except SQLAlchemyError as error:
        return {
            "status": "DOWN",
            "database": "DOWN",
            "error": str(error),
        }

@app.get("/accounts")
def get_accounts(db: Session = Depends(get_db)):
    accounts = db.query(Account).all()

    return [
        {
            "id": account.id,
            "account_number": account.account_number,
            "customer_name": account.customer_name,
            "balance": float(account.balance),
            "currency": account.currency,
        }
        for account in accounts
    ]