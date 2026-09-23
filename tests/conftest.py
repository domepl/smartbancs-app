import pytest

from app.database import SessionLocal
from app.models import Account


TEST_SOURCE = "900001"
TEST_DESTINATION = "900002"


def get_or_create_account(
    db,
    account_number,
    customer_name,
):
    account = (
        db.query(Account)
        .filter(
            Account.account_number == account_number
        )
        .first()
    )

    if account is None:
        account = Account(
            account_number=account_number,
            customer_name=customer_name,
            balance=0,
            currency="USD",
        )

        db.add(account)
        db.commit()
        db.refresh(account)

    return account


@pytest.fixture
def test_accounts():
    db = SessionLocal()

    try:
        source = get_or_create_account(
            db,
            TEST_SOURCE,
            "Test Account A",
        )

        destination = get_or_create_account(
            db,
            TEST_DESTINATION,
            "Test Account B",
        )

        source.balance = 1000
        destination.balance = 500

        db.commit()

        return {
            "source_number": TEST_SOURCE,
            "destination_number": TEST_DESTINATION,
            "source_id": source.id,
            "destination_id": destination.id,
        }

    finally:
        db.close()