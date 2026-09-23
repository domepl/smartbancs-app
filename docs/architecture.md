# Arquitectura de SmartBancs

## Descripción general de la arquitectura

SmartBancs separa el procesamiento síncrono de transacciones financieras de
las integraciones externas.

```mermaid
flowchart LR

C[Cliente]

API[API de transacciones<br/>FastAPI]

DB[(MariaDB)]

W[Worker de Outbox]

B[Mock Bancs]

AI[Servicio de recomendaciones con IA]

C -->|POST /transactions| API

API -->|Transacción ACID| DB

DB -->|Eventos pendientes en Outbox| W

W -->|Sincronización asíncrona| B

W -->|Solicitud asíncrona| AI

AI -->|Recomendación| W

W -->|Almacenar resultado| DB

C -->|GET recommendation| API