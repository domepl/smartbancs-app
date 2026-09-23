from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from fastapi import HTTPException

from app.database import SessionLocal
from app.models import Account
from app.schemas import TransactionCreate
from app.services import process_transaction


def execute_transfer(
    source_account,
    destination_account,
):
    db = SessionLocal()

    try:
        request = TransactionCreate(
            source_account=source_account,
            destination_account=destination_account,
            amount=20,
            currency="USD",
        )

        process_transaction(
            db=db,
            request=request,
            idempotency_key=(
                f"CONCURRENT-{uuid4()}"
            ),
        )

        return "SUCCESS"

    except HTTPException as error:
        if (
            error.status_code == 409
            and error.detail == "Insufficient funds."
        ):
            return "INSUFFICIENT_FUNDS"

        print(
            f"\nHTTP ERROR: "
            f"status={error.status_code} "
            f"detail={error.detail}"
        )

        return f"HTTP_ERROR_{error.status_code}"

    except Exception as error:
        print(
            f"\nUNEXPECTED ERROR: "
            f"{type(error).__name__}: {error}"
        )

        return "ERROR"

    finally:
        db.close()


def test_concurrent_transactions(
    test_accounts,
):
    # Preparar saldo exacto para la prueba.
    db = SessionLocal()

    try:
        source = (
            db.query(Account)
            .filter(
                Account.account_number
                == test_accounts["source_number"]
            )
            .first()
        )

        destination = (
            db.query(Account)
            .filter(
                Account.account_number
                == test_accounts[
                    "destination_number"
                ]
            )
            .first()
        )

        source.balance = 100
        destination.balance = 0

        db.commit()

    finally:
        db.close()

    # Lanzar 10 transferencias simultáneas de $20.
    with ThreadPoolExecutor(
        max_workers=10
    ) as executor:

        futures = [
            executor.submit(
                execute_transfer,
                test_accounts["source_number"],
                test_accounts[
                    "destination_number"
                ],
            )
            for _ in range(10)
        ]

        results = [
            future.result()
            for future in futures
        ]

    success_count = results.count(
        "SUCCESS"
    )

    insufficient_count = results.count(
        "INSUFFICIENT_FUNDS"
    )

    print("\nRESULTS:", results)
    print("SUCCESS:", success_count)
    print(
        "INSUFFICIENT:",
        insufficient_count,
    )

    # Verificar saldos finales.
    db = SessionLocal()

    try:
        source = (
            db.query(Account)
            .filter(
                Account.account_number
                == test_accounts["source_number"]
            )
            .first()
        )

        destination = (
            db.query(Account)
            .filter(
                Account.account_number
                == test_accounts[
                    "destination_number"
                ]
            )
            .first()
        )

        print(
            "SOURCE BALANCE:",
            float(source.balance),
        )

        print(
            "DESTINATION BALANCE:",
            float(destination.balance),
        )

        assert success_count == 5
        assert insufficient_count == 5

        assert float(source.balance) == 0.0
        assert float(destination.balance) == 100.0

    finally:
        db.close()