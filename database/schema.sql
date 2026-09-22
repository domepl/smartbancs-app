CREATE DATABASE IF NOT EXISTS smartbancs
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

USE smartbancs;


CREATE TABLE IF NOT EXISTS accounts (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    account_number VARCHAR(30) NOT NULL UNIQUE,
    customer_name VARCHAR(100) NOT NULL,
    balance DECIMAL(18,2) NOT NULL DEFAULT 0.00,
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL
        DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT chk_account_balance
        CHECK (balance >= 0)
) ENGINE=InnoDB;


CREATE TABLE IF NOT EXISTS transactions (
    id CHAR(36) PRIMARY KEY,
    idempotency_key VARCHAR(100) NOT NULL UNIQUE,

    source_account_id BIGINT NOT NULL,
    destination_account_id BIGINT NOT NULL,

    amount DECIMAL(18,2) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    status VARCHAR(20) NOT NULL,

    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_transaction_source
        FOREIGN KEY (source_account_id)
        REFERENCES accounts(id),

    CONSTRAINT fk_transaction_destination
        FOREIGN KEY (destination_account_id)
        REFERENCES accounts(id),

    CONSTRAINT chk_transaction_amount
        CHECK (amount > 0),

    CONSTRAINT chk_different_accounts
        CHECK (source_account_id <> destination_account_id)
) ENGINE=InnoDB;


CREATE TABLE IF NOT EXISTS outbox_events (
    id CHAR(36) PRIMARY KEY,
    transaction_id CHAR(36) NOT NULL,

    event_type VARCHAR(50) NOT NULL,
    payload JSON NOT NULL,

    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    retry_count INT NOT NULL DEFAULT 0,

    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    processed_at DATETIME NULL,

    CONSTRAINT fk_outbox_transaction
        FOREIGN KEY (transaction_id)
        REFERENCES transactions(id)
) ENGINE=InnoDB;


CREATE TABLE IF NOT EXISTS recommendations (
    id CHAR(36) PRIMARY KEY,
    transaction_id CHAR(36) NOT NULL,

    recommendation TEXT NOT NULL,
    model_version VARCHAR(30) NOT NULL DEFAULT 'mock-v1',

    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_recommendation_transaction
        FOREIGN KEY (transaction_id)
        REFERENCES transactions(id)
) ENGINE=InnoDB;


CREATE INDEX idx_transactions_source
ON transactions(source_account_id);


CREATE INDEX idx_transactions_destination
ON transactions(destination_account_id);


CREATE INDEX idx_transactions_created_at
ON transactions(created_at);


CREATE INDEX idx_outbox_status
ON outbox_events(status);