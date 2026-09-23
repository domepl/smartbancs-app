from prometheus_client import Counter, Histogram


TRANSACTIONS_TOTAL = Counter(
    "smartbancs_transactions_total",
    "Total number of transaction requests",
)


TRANSACTIONS_SUCCESS = Counter(
    "smartbancs_transactions_success_total",
    "Total number of successful transactions",
)


TRANSACTIONS_FAILED = Counter(
    "smartbancs_transactions_failed_total",
    "Total number of failed transactions",
)


TRANSACTION_DURATION = Histogram(
    "smartbancs_transaction_duration_seconds",
    "Transaction processing duration in seconds",
)


DATABASE_ERRORS = Counter(
    "smartbancs_database_errors_total",
    "Total number of database errors",
)