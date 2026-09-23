# Observabilidad

SmartBancs implementa observabilidad básica mediante
registros estructurados, identificadores de correlación y
métricas compatibles con Prometheus.

## Registro de eventos (Logging)

La API de transacciones registra:

- el inicio de la transacción;
- transacciones exitosas;
- transacciones fallidas;
- duración del procesamiento;
- errores de base de datos.

## ID de correlación

Cada solicitud recibe un `X-Correlation-ID`.

Si el cliente no proporciona uno, SmartBancs
genera un UUID automáticamente.

El identificador se propaga a través de:

Transaction API -> Outbox -> Worker -> Bancs -> AI

Esto permite rastrear una transacción a través
de los componentes implementados.

## Métricas

La API expone:

`GET /metrics`

Métricas principales:

- smartbancs_transactions_total
- smartbancs_transactions_success_total
- smartbancs_transactions_failed_total
- smartbancs_transaction_duration_seconds
- smartbancs_database_errors_total

## Diagnóstico de incidentes

En caso de aumento de la latencia o errores de base de datos,
se pueden utilizar los siguientes comandos de MariaDB:

SHOW FULL PROCESSLIST;

SELECT * FROM information_schema.INNODB_TRX;

SHOW ENGINE INNODB STATUS;