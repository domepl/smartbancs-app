from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.sql import func

from app.database import Base


class Account(Base):
    __tablename__ = "accounts"

    id = Column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    account_number = Column(
        String(30),
        nullable=False,
        unique=True,
    )

    customer_name = Column(
        String(100),
        nullable=False,
    )

    balance = Column(
        Numeric(18, 2),
        nullable=False,
        default=0,
    )

    currency = Column(
        String(3),
        nullable=False,
        default="USD",
    )

    created_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )

    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(
        String(36),
        primary_key=True,
    )

    idempotency_key = Column(
        String(100),
        nullable=False,
        unique=True,
    )

    source_account_id = Column(
        BigInteger,
        ForeignKey("accounts.id"),
        nullable=False,
    )

    destination_account_id = Column(
        BigInteger,
        ForeignKey("accounts.id"),
        nullable=False,
    )

    amount = Column(
        Numeric(18, 2),
        nullable=False,
    )

    currency = Column(
        String(3),
        nullable=False,
        default="USD",
    )

    status = Column(
        String(20),
        nullable=False,
    )

    created_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )


class OutboxEvent(Base):
    __tablename__ = "outbox_events"

    id = Column(
        String(36),
        primary_key=True,
    )

    transaction_id = Column(
        String(36),
        ForeignKey("transactions.id"),
        nullable=False,
    )

    event_type = Column(
        String(50),
        nullable=False,
    )

    payload = Column(
        JSON,
        nullable=False,
    )

    status = Column(
        String(20),
        nullable=False,
        default="PENDING",
    )

    retry_count = Column(
        Integer,
        nullable=False,
        default=0,
    )

    created_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )

    processed_at = Column(
        DateTime,
        nullable=True,
    )


class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(
        String(36),
        primary_key=True,
    )

    transaction_id = Column(
        String(36),
        ForeignKey("transactions.id"),
        nullable=False,
    )

    recommendation = Column(
        Text,
        nullable=False,
    )

    model_version = Column(
        String(30),
        nullable=False,
        default="mock-v1",
    )

    created_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )