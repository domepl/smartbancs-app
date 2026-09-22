from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Account, Transaction
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


def process_transaction(
    db: Session,
    request: TransactionCreate,
    idempotency_key: str,
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
            and
            destination_account.account_number
            == request.destination_account
            and
            existing_transaction.amount
            == request.amount
            and
            existing_transaction.currency
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

    if request.source_account == request.destination_account:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Source and destination accounts must be different.",
        )

    try:
        # 2. Buscar las cuentas involucradas.
        result = db.execute(
            select(
                Account.id,
                Account.account_number,
            ).where(
                Account.account_number.in_(
                    [
                        request.source_account,
                        request.destination_account,
                    ]
                )
            )
        )

        account_rows = result.all()

        if len(account_rows) != 2:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="One or both accounts were not found.",
            )

        account_ids = {
            row.account_number: row.id
            for row in account_rows
        }

        # 3. Bloquear las cuentas siempre en el mismo orden.
        locked_accounts = {}

        for account_id in sorted(account_ids.values()):
            account = db.execute(
                select(Account)
                .where(Account.id == account_id)
                .with_for_update()
            ).scalar_one()

            locked_accounts[
                account.account_number
            ] = account

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
                detail="Source account currency does not match transaction currency.",
            )

        if destination_account.currency != request.currency:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Destination account currency does not match transaction currency.",
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

        # 8. Confirmar operación.
        db.commit()
        db.refresh(transaction)

        return (
            build_transaction_response(
                db,
                transaction,
            ),
            True,
        )

    except IntegrityError:
        # Puede ocurrir si dos solicitudes con la misma
        # Idempotency-Key llegan exactamente al mismo tiempo.
        db.rollback()

        existing_transaction = db.execute(
            select(Transaction).where(
                Transaction.idempotency_key == idempotency_key
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

    except HTTPException:
        db.rollback()
        raise

    except Exception as error:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Transaction processing failed: {str(error)}",
        )