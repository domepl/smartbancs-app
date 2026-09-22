from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Account, Transaction
from app.schemas import TransactionCreate


def process_transaction(
    db: Session,
    request: TransactionCreate,
):
    if request.source_account == request.destination_account:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Source and destination accounts must be different.",
        )

    try:
        # 1. Localizar ambas cuentas.
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

        # 2. Bloquear siempre en el mismo orden.
        #
        # Esto ayuda a prevenir race conditions y reduce
        # el riesgo de deadlocks.
        locked_accounts = {}

        for account_id in sorted(account_ids.values()):
            account = db.execute(
                select(Account)
                .where(Account.id == account_id)
                .with_for_update()
            ).scalar_one()

            locked_accounts[account.account_number] = account

        source_account = locked_accounts[
            request.source_account
        ]

        destination_account = locked_accounts[
            request.destination_account
        ]

        # 3. Validar moneda.
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

        # 4. Validar saldo.
        if source_account.balance < request.amount:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Insufficient funds.",
            )

        # 5. Actualizar saldos.
        source_account.balance -= request.amount
        destination_account.balance += request.amount

        # 6. Registrar la transferencia.
        transaction_id = str(uuid4())

        transaction = Transaction(
            id=transaction_id,

            # En el siguiente punto lo reemplazaremos por
            # una clave enviada por el cliente.
            idempotency_key=f"AUTO-{uuid4()}",

            source_account_id=source_account.id,
            destination_account_id=destination_account.id,

            amount=request.amount,
            currency=request.currency,
            status="COMPLETED",
        )

        db.add(transaction)

        # 7. Confirmar todo junto.
        db.commit()

        db.refresh(transaction)

        return {
            "transaction_id": transaction.id,
            "source_account": source_account.account_number,
            "destination_account": destination_account.account_number,
            "amount": transaction.amount,
            "currency": transaction.currency,
            "status": transaction.status,
            "created_at": transaction.created_at,
        }

    except HTTPException:
        db.rollback()
        raise

    except Exception as error:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Transaction processing failed: {str(error)}",
        )