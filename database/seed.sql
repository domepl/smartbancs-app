USE smartbancs;

INSERT IGNORE INTO accounts (
    id,
    account_number,
    customer_name,
    balance,
    currency
)
VALUES
(
    1,
    '100001',
    'Cliente Demo 1',
    1000.00,
    'USD'
),
(
    2,
    '100002',
    'Cliente Demo 2',
    500.00,
    'USD'
),
(
    3,
    '100003',
    'Cliente Demo 3',
    200.00,
    'USD'
);