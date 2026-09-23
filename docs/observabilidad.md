# Observabilidad

SmartBancs implementa una observabilidad básica utilizando registros de la aplicación,
identificadores de correlación y métricas compatibles con Prometheus.

## Registros (Logs)

La API registra:

- inicio de transacción;
- finalización de transacción;
- fallos en transacciones;
- errores de base de datos.

El Worker registra:

- sincronización con Bancs;
- llamadas a IA;
- fallos de procesamiento.

## ID de correlación

Cada solicitud HTTP recibe un `X-Correlation-ID`.

El identificador puede propagarse a través de:

API -> Outbox -> Worker -> Bancs -> IA

## Métricas

La API expone:

GET /metrics

Métricas principales de la aplicación:

- smartbancs_transactions_total
- smartbancs_transactions_success_total
- smartbancs_transactions_failed_total
- smartbancs_transaction_duration_seconds
- smartbancs_database_errors_total

## Investigación de incidentes

Comandos de diagnóstico útiles para MariaDB:

SHOW FULL PROCESSLIST;

SELECT *
FROM information_schema.INNODB_TRX;

SHOW ENGINE INNODB STATUS;