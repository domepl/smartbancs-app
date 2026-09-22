from datetime import datetime, timezone
from uuid import uuid4

from fastapi import FastAPI
from pydantic import BaseModel


app = FastAPI(
    title="Mock Bancs",
    description="Simulated legacy Bancs core for SmartBancs MVP",
    version="1.0.0",
)


class BancsTransaction(BaseModel):
    transaction_id: str
    source_account: str
    destination_account: str
    amount: str
    currency: str


@app.get("/health")
def health():
    return {
        "status": "UP",
        "service": "mock-bancs",
    }


@app.post("/legacy/transactions")
def receive_transaction(
    transaction: BancsTransaction,
):
    return {
        "status": "ACCEPTED",
        "legacy_reference": f"BANCS-{uuid4().hex[:10].upper()}",
        "transaction_id": transaction.transaction_id,
        "processed_at": datetime.now(
            timezone.utc
        ).isoformat(),
    }