from fastapi import (
    Depends,
    FastAPI,
    Header,
    Response,
    status,
)
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import engine, get_db
from app.models import (
    Account,
    Recommendation,
)

from app.schemas import (
    TransactionCreate,
    TransactionResponse,
)
from app.services import process_transaction

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

@app.post(
    "/transactions",
    response_model=TransactionResponse,
)
def create_transaction(
    request: TransactionCreate,
    response: Response,
    idempotency_key: str = Header(
        ...,
        alias="Idempotency-Key",
        min_length=1,
        max_length=100,
    ),
    db: Session = Depends(get_db),
):
    transaction, created = process_transaction(
        db=db,
        request=request,
        idempotency_key=idempotency_key,
    )

    if created:
        response.status_code = status.HTTP_201_CREATED
    else:
        response.status_code = status.HTTP_200_OK

    return transaction


@app.get(
    "/transactions/{transaction_id}/recommendation"
)
def get_transaction_recommendation(
    transaction_id: str,
    db: Session = Depends(get_db),
):
    recommendation = (
        db.query(Recommendation)
        .filter(
            Recommendation.transaction_id
            == transaction_id
        )
        .first()
    )

    if not recommendation:
        return {
            "transaction_id": transaction_id,
            "status": "PENDING",
            "recommendation": None,
        }

    return {
        "transaction_id": transaction_id,
        "status": "READY",
        "recommendation":
            recommendation.recommendation,
        "model_version":
            recommendation.model_version,
    }