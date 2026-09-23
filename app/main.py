from fastapi import (
    Depends,
    FastAPI,
    Header,
    Response,
    status,
)
from fastapi.responses import Response as FastAPIResponse
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    generate_latest,
)
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from time import perf_counter

from app.database import engine, get_db
from app.logger import get_logger,configure_logging
from app.metrics import (
    TRANSACTION_DURATION,
    TRANSACTIONS_FAILED,
    TRANSACTIONS_SUCCESS,
    TRANSACTIONS_TOTAL,
)
from app.middleware.correlation_id import (
    correlation_id_middleware,
    get_correlation_id,
)
from app.models import (
    Account,
    Recommendation,
)

from app.schemas import (
    TransactionCreate,
    TransactionResponse,
)
from app.services import process_transaction

configure_logging()

logger = get_logger(
    "smartbancs.api"
)

app = FastAPI(
    title="SmartBancs API",
    description="MVP API para Smartbancs",
    version="1.0.0",
)

app.middleware("http")(
    correlation_id_middleware
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
    TRANSACTIONS_TOTAL.inc()

    start_time = perf_counter()

    correlation_id = get_correlation_id()

    logger.info(
        "transaction_started "
        f"correlation_id={correlation_id} "
        f"idempotency_key={idempotency_key} "
        f"source={request.source_account} "
        f"destination={request.destination_account} "
        f"amount={request.amount}"
    )

    try:
        transaction, created = (
            process_transaction(
                db=db,
                request=request,
                idempotency_key=idempotency_key,
            )
        )

        TRANSACTIONS_SUCCESS.inc()

        if created:
            response.status_code = (
                status.HTTP_201_CREATED
            )
        else:
            response.status_code = (
                status.HTTP_200_OK
            )

        duration = (
            perf_counter()
            - start_time
        )

        TRANSACTION_DURATION.observe(
            duration
        )

        logger.info(
            "transaction_completed "
            f"correlation_id={correlation_id} "
            f"transaction_id="
            f"{transaction['transaction_id']} "
            f"duration_seconds="
            f"{duration:.4f}"
        )

        return transaction

    except Exception as error:
        TRANSACTIONS_FAILED.inc()

        duration = (
            perf_counter()
            - start_time
        )

        TRANSACTION_DURATION.observe(
            duration
        )

        logger.error(
            "transaction_failed "
            f"correlation_id={correlation_id} "
            f"duration_seconds="
            f"{duration:.4f} "
            f"error={error}"
        )

        raise


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


@app.get("/metrics")
def metrics():
    return FastAPIResponse(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )