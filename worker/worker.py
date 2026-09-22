import json
import os
import time
from uuid import uuid4

import httpx
from dotenv import load_dotenv
from sqlalchemy import select

from app.database import SessionLocal
from app.models import (
    OutboxEvent,
    Recommendation,
)


load_dotenv()


BANCS_SERVICE_URL = os.getenv(
    "BANCS_SERVICE_URL",
    "http://localhost:8002",
)

AI_SERVICE_URL = os.getenv(
    "AI_SERVICE_URL",
    "http://localhost:8001",
)


POLL_INTERVAL_SECONDS = 5
MAX_RETRIES = 3


def get_events_to_process(db):
    return db.execute(
        select(OutboxEvent)
        .where(
            OutboxEvent.status.in_(
                [
                    "PENDING",
                    "BANCS_SYNCED",
                ]
            )
        )
        .order_by(
            OutboxEvent.created_at.asc()
        )
        .limit(10)
    ).scalars().all()


def get_payload(event):
    payload = event.payload

    if isinstance(payload, str):
        payload = json.loads(payload)

    return payload


def send_to_bancs(event):
    payload = get_payload(event)

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


def send_to_ai(event):
    payload = get_payload(event)

    ai_payload = {
        "transaction_id": payload[
            "transaction_id"
        ],
        "source_account": payload[
            "source_account"
        ],
        "destination_account": payload[
            "destination_account"
        ],
        "amount": float(
            payload["amount"]
        ),
        "currency": payload[
            "currency"
        ],
    }

    response = httpx.post(
        f"{AI_SERVICE_URL}/recommendations",
        json=ai_payload,
        timeout=5.0,
    )

    response.raise_for_status()

    return response.json()


def process_bancs(db, event):
    print(
        f"[WORKER] Sending transaction "
        f"{event.transaction_id} to Bancs"
    )

    try:
        result = send_to_bancs(event)

        event.status = "BANCS_SYNCED"

        # Los reintentos de Bancs ya terminaron.
        event.retry_count = 0

        db.commit()

        print(
            f"[WORKER] Bancs accepted transaction "
            f"{event.transaction_id}"
        )

        print(
            f"[WORKER] Bancs reference: "
            f"{result.get('legacy_reference')}"
        )

    except Exception as error:
        db.rollback()

        event = db.get(
            OutboxEvent,
            event.id,
        )

        event.retry_count += 1

        if event.retry_count >= MAX_RETRIES:
            event.status = "FAILED"

        db.commit()

        print(
            f"[WORKER] Bancs error "
            f"for transaction "
            f"{event.transaction_id}: "
            f"{error}"
        )


def process_ai(db, event):
    print(
        f"[WORKER] Requesting AI recommendation "
        f"for transaction "
        f"{event.transaction_id}"
    )

    try:
        # Evita crear una recomendación duplicada
        # si el worker vuelve a procesar el evento.
        existing_recommendation = db.execute(
            select(Recommendation).where(
                Recommendation.transaction_id
                == event.transaction_id
            )
        ).scalar_one_or_none()

        if existing_recommendation:
            event.status = "PROCESSED"
            event.retry_count = 0
            db.commit()

            print(
                f"[WORKER] Recommendation already "
                f"exists for transaction "
                f"{event.transaction_id}"
            )

            return

        result = send_to_ai(event)

        recommendation = Recommendation(
            id=str(uuid4()),
            transaction_id=event.transaction_id,
            recommendation=result[
                "recommendation"
            ],
            model_version=result[
                "model_version"
            ],
        )

        db.add(recommendation)

        event.status = "PROCESSED"
        event.retry_count = 0

        db.commit()

        print(
            f"[WORKER] AI recommendation saved "
            f"for transaction "
            f"{event.transaction_id}"
        )

    except Exception as error:
        db.rollback()

        event = db.get(
            OutboxEvent,
            event.id,
        )

        event.retry_count += 1

        if event.retry_count >= MAX_RETRIES:
            event.status = "FAILED"

        db.commit()

        print(
            f"[WORKER] AI error "
            f"for transaction "
            f"{event.transaction_id}: "
            f"{error}"
        )


def process_event(db, event):
    if event.status == "PENDING":
        process_bancs(
            db,
            event,
        )

    elif event.status == "BANCS_SYNCED":
        process_ai(
            db,
            event,
        )


def run_worker():
    print(
        "[WORKER] SmartBancs worker started"
    )

    while True:
        db = SessionLocal()

        try:
            events = get_events_to_process(
                db
            )

            if not events:
                print(
                    "[WORKER] No events to process"
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