import time
from uuid import uuid4
from app.metrics import DATABASE_ERRORS
from app.middleware.correlation_id import (
    get_correlation_id,
)
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import (
    IntegrityError,
    OperationalError,
)
from sqlalchemy.orm import Session
from app.models import (
    Account,
    OutboxEvent,
    Transaction,
)
from app.schemas import TransactionCreate


def build_transaction_response(
    db: Session,
    transaction: Transaction,
):
    source_account = db.get(
        Account,
        transaction.source_account_id,
    )

    destination_account = db.get(
        Account,
        transaction.destination_account_id,
    )

    return {
        "transaction_id": transaction.id,
        "source_account": source_account.account_number,
        "destination_account": destination_account.account_number,
        "amount": transaction.amount,
        "currency": transaction.currency,
        "status": transaction.status,
        "created_at": transaction.created_at,
    }

def create_outbox_event(
    transaction: Transaction,
    request: TransactionCreate,
):
    return OutboxEvent(
        id=str(uuid4()),
        transaction_id=transaction.id,
        event_type="TRANSACTION_COMPLETED",
        payload={
            "transaction_id": transaction.id,
            "correlation_id": get_correlation_id(),
            "source_account": request.source_account,
            "destination_account": request.destination_account,
            "amount": str(request.amount),
            "currency": request.currency,
            "status": "COMPLETED",
        },
        status="PENDING",
        retry_count=0,
    )

def process_transaction(
    db: Session,
    request: TransactionCreate,
    idempotency_key: str,
    retry_attempt: int = 1,
):
    # 1. Verificar si la petición ya fue procesada.
    existing_transaction = db.execute(
        select(Transaction).where(
            Transaction.idempotency_key == idempotency_key
        )
    ).scalar_one_or_none()

    if existing_transaction:
        source_account = db.get(
            Account,
            existing_transaction.source_account_id,
        )

        destination_account = db.get(
            Account,
            existing_transaction.destination_account_id,
        )

        same_request = (
            source_account.account_number
            == request.source_account
            and destination_account.account_number
            == request.destination_account
            and existing_transaction.amount
            == request.amount
            and existing_transaction.currency
            == request.currency
        )

        if not same_request:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Idempotency-Key was already used "
                    "for a different transaction."
                ),
            )

        return (
            build_transaction_response(
                db,
                existing_transaction,
            ),
            False,
        )

    # La cuenta origen y destino no pueden ser iguales.
    if request.source_account == request.destination_account:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Source and destination accounts "
                "must be different."
            ),
        )

    try:
        # 2. Buscar Y bloquear las dos cuentas en una sola consulta.
        #
        # IMPORTANTE:
        # Antes hacíamos:
        # SELECT normal -> SELECT FOR UPDATE
        #
        # Bajo concurrencia MariaDB podía devolver error 1020:
        # "Record has changed since last read".
        #
        # Ahora las cuentas se leen directamente con FOR UPDATE.
        accounts = db.execute(
            select(Account)
            .where(
                Account.account_number.in_(
                    [
                        request.source_account,
                        request.destination_account,
                    ]
                )
            )
            .order_by(Account.id)
            .with_for_update()
        ).scalars().all()

        if len(accounts) != 2:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="One or both accounts were not found.",
            )

        # 3. Crear diccionario con las cuentas ya bloqueadas.
        locked_accounts = {
            account.account_number: account
            for account in accounts
        }

        source_account = locked_accounts[
            request.source_account
        ]

        destination_account = locked_accounts[
            request.destination_account
        ]

        # 4. Validar moneda.
        if source_account.currency != request.currency:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Source account currency does not "
                    "match transaction currency."
                ),
            )

        if destination_account.currency != request.currency:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Destination account currency does not "
                    "match transaction currency."
                ),
            )

        # 5. Validar saldo.
        if source_account.balance < request.amount:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Insufficient funds.",
            )

        # 6. Actualizar saldos.
        source_account.balance -= request.amount
        destination_account.balance += request.amount

        # 7. Registrar transferencia.
        transaction = Transaction(
            id=str(uuid4()),
            idempotency_key=idempotency_key,
            source_account_id=source_account.id,
            destination_account_id=destination_account.id,
            amount=request.amount,
            currency=request.currency,
            status="COMPLETED",
        )

        db.add(transaction)

        # Fuerza el INSERT de la transacción antes
        # de crear el evento Outbox.
        db.flush()

        # 8. Crear evento Outbox.
        outbox_event = create_outbox_event(
            transaction=transaction,
            request=request,
        )

        db.add(outbox_event)

        # 9. Confirmar toda la operación atómicamente.
        db.commit()

        db.refresh(transaction)

        return (
            build_transaction_response(
                db,
                transaction,
            ),
            True,
        )

    except IntegrityError as error:
        # Puede ocurrir si dos solicitudes con la misma
        # Idempotency-Key llegan al mismo tiempo.
        db.rollback()

        DATABASE_ERRORS.inc()

        existing_transaction = db.execute(
            select(Transaction).where(
                Transaction.idempotency_key
                == idempotency_key
            )
        ).scalar_one_or_none()

        if existing_transaction:
            return (
                build_transaction_response(
                    db,
                    existing_transaction,
                ),
                False,
            )

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Duplicate transaction detected.",
        )

    except OperationalError as error:
        db.rollback()

        DATABASE_ERRORS.inc()

        error_code = None

        if (
            hasattr(error.orig, "args")
            and error.orig.args
        ):
            error_code = error.orig.args[0]

        print(
            f"\n[DATABASE OPERATIONAL ERROR] "
            f"code={error_code} "
            f"attempt={retry_attempt} "
            f"error={error.orig}"
        )

        # Errores transitorios de concurrencia en MariaDB.
        retriable_errors = {
            1020,  # Record changed since last read
            1205,  # Lock wait timeout
            1213,  # Deadlock
        }

        max_retries = 5

        if (
            error_code in retriable_errors
            and retry_attempt < max_retries
        ):
            wait_time = 0.05 * retry_attempt

            print(
                f"[DB RETRY] "
                f"error={error_code} "
                f"next_attempt={retry_attempt + 1} "
                f"waiting={wait_time:.2f}s"
            )

            time.sleep(wait_time)

            return process_transaction(
                db=db,
                request=request,
                idempotency_key=idempotency_key,
                retry_attempt=retry_attempt + 1,
            )

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Database concurrency error "
                f"after {retry_attempt} attempts. "
                f"Error {error_code}: {error.orig}"
            ),
        )

    except HTTPException:
        db.rollback()
        raise

    except Exception as error:
        db.rollback()

        DATABASE_ERRORS.inc()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Transaction processing failed: "
                f"{str(error)}"
            ),
        )