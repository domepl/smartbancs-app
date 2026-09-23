from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.database import SessionLocal
from app.models import Account
from app.schemas import TransactionCreate
from app.services import process_transaction


def test_successful_transaction(
    test_accounts,
):
    db = SessionLocal()

    try:
        request = TransactionCreate(
            source_account=test_accounts[
                "source_number"
            ],
            destination_account=test_accounts[
                "destination_number"
            ],
            amount=100,
            currency="USD",
        )

        transaction, created = process_transaction(
            db=db,
            request=request,
            idempotency_key=f"TEST-{uuid4()}",
        )

        assert created is True
        assert transaction["status"] == "COMPLETED"

        db.expire_all()

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

        assert float(source.balance) == 900.0
        assert float(destination.balance) == 600.0

    finally:
        db.close()


def test_insufficient_funds(
    test_accounts,
):
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

        source.balance = 50
        db.commit()

        request = TransactionCreate(
            source_account=test_accounts[
                "source_number"
            ],
            destination_account=test_accounts[
                "destination_number"
            ],
            amount=100,
            currency="USD",
        )

        with pytest.raises(
            HTTPException
        ) as exception:
            process_transaction(
                db=db,
                request=request,
                idempotency_key=f"TEST-{uuid4()}",
            )

        assert exception.value.status_code == 409
        assert (
            exception.value.detail
            == "Insufficient funds."
        )

        db.expire_all()

        source = (
            db.query(Account)
            .filter(
                Account.account_number
                == test_accounts["source_number"]
            )
            .first()
        )

        assert float(source.balance) == 50.0

    finally:
        db.close()


def test_transaction_idempotency(
    test_accounts,
):
    db = SessionLocal()

    try:
        idempotency_key = (
            f"TEST-IDEMPOTENCY-{uuid4()}"
        )

        request = TransactionCreate(
            source_account=test_accounts[
                "source_number"
            ],
            destination_account=test_accounts[
                "destination_number"
            ],
            amount=50,
            currency="USD",
        )

        first_transaction, first_created = (
            process_transaction(
                db=db,
                request=request,
                idempotency_key=idempotency_key,
            )
        )

        second_transaction, second_created = (
            process_transaction(
                db=db,
                request=request,
                idempotency_key=idempotency_key,
            )
        )

        assert first_created is True
        assert second_created is False

        assert (
            first_transaction["transaction_id"]
            ==
            second_transaction["transaction_id"]
        )

        db.expire_all()

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

        assert float(source.balance) == 950.0
        assert float(destination.balance) == 550.0

    finally:
        db.close()