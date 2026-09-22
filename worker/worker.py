import json
import os
import time

import httpx
from dotenv import load_dotenv
from sqlalchemy import select

from app.database import SessionLocal
from app.models import OutboxEvent


load_dotenv()


BANCS_SERVICE_URL = os.getenv(
    "BANCS_SERVICE_URL",
    "http://localhost:8002",
)

POLL_INTERVAL_SECONDS = 5
MAX_RETRIES = 3


def get_pending_events(db):
    return db.execute(
        select(OutboxEvent)
        .where(
            OutboxEvent.status == "PENDING"
        )
        .order_by(
            OutboxEvent.created_at.asc()
        )
        .limit(10)
    ).scalars().all()


def send_to_bancs(event):
    payload = event.payload

    if isinstance(payload, str):
        payload = json.loads(payload)

    bancs_payload = {
        "transaction_id": payload[
            "transaction_id"
        ],
        "source_account": payload[
            "source_account"
        ],
        "destination_account": payload[
            "destination_account"
        ],
        "amount": payload[
            "amount"
        ],
        "currency": payload[
            "currency"
        ],
    }

    response = httpx.post(
        f"{BANCS_SERVICE_URL}/legacy/transactions",
        json=bancs_payload,
        timeout=5.0,
    )

    response.raise_for_status()

    return response.json()


def process_event(db, event):
    print(
        f"[WORKER] Processing event "
        f"{event.id}"
    )

    try:
        result = send_to_bancs(event)

        print(
            f"[WORKER] Bancs accepted "
            f"transaction "
            f"{event.transaction_id}"
        )

        print(
            f"[WORKER] Bancs reference: "
            f"{result.get('legacy_reference')}"
        )

        event.status = "BANCS_SYNCED"

        db.commit()

    except Exception as error:
        db.rollback()

        # Volvemos a recuperar el evento porque
        # después del rollback el estado ORM puede
        # quedar expirado.
        event = db.get(
            OutboxEvent,
            event.id,
        )

        event.retry_count += 1

        if event.retry_count >= MAX_RETRIES:
            event.status = "FAILED"

        db.commit()

        print(
            f"[WORKER] Error processing "
            f"{event.id}: {error}"
        )


def run_worker():
    print("[WORKER] SmartBancs worker started")

    while True:
        db = SessionLocal()

        try:
            events = get_pending_events(db)

            if not events:
                print(
                    "[WORKER] No pending events"
                )

            for event in events:
                process_event(
                    db,
                    event,
                )

        except Exception as error:
            print(
                f"[WORKER] Unexpected error: "
                f"{error}"
            )

        finally:
            db.close()

        time.sleep(
            POLL_INTERVAL_SECONDS
        )


if __name__ == "__main__":
    run_worker()