# Diseño técnico de SmartBancs

## 1. Descripción general

SmartBancs es una plataforma de transacciones financieras de prueba de concepto,
diseñada para demostrar el procesamiento seguro de transacciones, la integración
asíncrona con una plataforma bancaria heredada (*legacy*) y recomendaciones de IA
no bloqueantes.

El MVP se centra en los siguientes requisitos:

- transferencias financieras con bajo tiempo de respuesta;
- consistencia de transacciones y control de concurrencia;
- procesamiento de transacciones idempotente;
- integración asíncrona con el sistema bancario heredado (Bancs);
- recomendaciones de IA asíncronas;
- procesamiento ETL;
- observabilidad;
- pruebas automatizadas;
- despliegue en contenedores.

El proyecto se ha simplificado intencionadamente para un desafío técnico y
no representa una plataforma bancaria lista para producción.

---

## 2. Stack tecnológico

La solución utiliza:

- Python 3.11
- FastAPI
- SQLAlchemy 2
- MariaDB 11 / InnoDB
- PyMySQL
- HTTPX
- Pandas
- Prometheus Client
- Pytest
- Docker
- Docker Compose

### Decisiones tecnológicas

Se seleccionó FastAPI porque ofrece un framework web ligero y preparado para
operaciones asíncronas, documentación OpenAPI automática e inyección de
dependencias sencilla.

Se eligió MariaDB con InnoDB por su soporte para transacciones ACID,
bloqueo a nivel de fila y consistencia transaccional.

SQLAlchemy proporciona abstracción de base de datos, gestión de sesiones y
control explícito de transacciones.

Docker Compose permite iniciar todo el MVP mediante un único comando.

---

## 3. Componentes principales

La solución consta de cinco componentes principales en tiempo de ejecución:

1. API de transacciones
2. MariaDB
3. Worker de Outbox
4. Servicio simulado (mock) de Bancs
5. Servicio de recomendaciones de IA

El proceso ETL se ejecuta de forma independiente cuando es necesario.

---

## 4. Procesamiento de transacciones

Una transferencia financiera sigue estos pasos:

1. Validar la clave de idempotencia (*Idempotency-Key*).
2. Validar las cuentas de origen y destino.
3. Bloquear las cuentas implicadas mediante `SELECT ... FOR UPDATE`.
4. Validar la moneda.
5. Validar el saldo disponible.
6. Actualizar ambos saldos.
7. Insertar el registro de la transacción.
8. Insertar un evento en la tabla *Outbox*.
9. Confirmar (*commit*) la transacción de base de datos.
10. Devolver la respuesta al cliente.

La transacción y el evento *Outbox* se persisten dentro de la misma
transacción de base de datos. Esto evita que el sistema realice una operación financiera sin
registrar también el evento que deberá procesarse posteriormente de forma asíncrona.

---

## 5. Control de concurrencia

Las filas de las cuentas se bloquean utilizando:

SELECT ... FOR UPDATE

Las cuentas se ordenan según su identificador de base de datos antes de realizar el bloqueo.

Esto reduce las condiciones de carrera cuando varias solicitudes intentan modificar
la misma cuenta simultáneamente.

La prueba automatizada de concurrencia ejecuta múltiples transacciones simultáneas
sobre la misma cuenta de origen y verifica que el
saldo no pueda volverse negativo.

---

## 6. Idempotencia

Los clientes deben enviar:

Idempotency-Key

La clave se almacena junto con la transacción y cuenta con una restricción de unicidad (UNIQUE).

Si se envía nuevamente la misma solicitud con la misma clave, SmartBancs devuelve
la transacción creada anteriormente en lugar de ejecutar la transferencia
de nuevo.

Si se reutiliza la misma clave para datos de transacción diferentes, la API devuelve
un error HTTP 409 Conflict.

---

## 7. Procesamiento asíncrono

SmartBancs no realiza llamadas síncronas a Bancs ni al servicio de IA durante la
transferencia financiera.

En su lugar:

API de transacciones
->
Transacción en MariaDB + Outbox
->
Respuesta HTTP
->
Worker (proceso en segundo plano)
->
Bancs
->
IA

Por lo tanto, la transacción del cliente no se ve bloqueada por la disponibilidad o
la latencia de la plataforma heredada Bancs o del servicio de IA.

---

## 8. Integración con Bancs

La integración con Bancs se implementa mediante un *Worker* de tipo *Outbox*.

El *worker* lee periódicamente los eventos pendientes y los envía al
servicio simulado (*mock*) de Bancs.

Este patrón protege a Bancs de recibir el mismo volumen de tráfico que
la API pública de transacciones.

Se detallan aspectos adicionales en:

docs/bancs-integration.md

---

## 9. Inteligencia Artificial

El MVP incluye un servicio independiente de recomendación basado en IA.

La implementación actual es una simulación funcional que utiliza reglas
deterministas. No se presenta como un modelo de aprendizaje automático entrenado.

El servicio demuestra el requisito arquitectónico de que la IA debe ejecutarse
fuera de la ruta crítica de la transacción financiera.

Se detallan consideraciones adicionales sobre el ciclo de vida en producción en:

docs/ai-lifecycle.md

---

## 10. Observabilidad

La API proporciona:

- registros de la aplicación;
- registros de éxito y fallo de transacciones;
- identificadores de correlación;
- métricas de errores de base de datos; - contadores de transacciones;
- métricas de latencia de transacciones;
- endpoint `/metrics` compatible con Prometheus.

Se puede propagar un identificador de correlación a través de:

API -> Outbox -> Worker -> Bancs -> AI

Consulte:

docs/observability.md

---

## 11. ETL

El componente ETL lee datos de transacciones sin procesar utilizando Pandas.

Realiza las siguientes operaciones:

- eliminación de duplicados;
- normalización de espacios en blanco;
- normalización de divisas;
- conversión numérica;
- filtrado de importes no válidos;
- normalización de fechas;
- filtrado de valores faltantes.

El conjunto de datos depurado se genera de forma independiente a la API de transacciones.

---

## 12. Despliegue
El entorno de ejecución completo se puede iniciar con:

docker compose up --build

El despliegue incluye:

- MariaDB
- API de transacciones
- Worker (procesador de tareas)
- Mock de Bancs (simulación del sistema bancario)
- Servicio de IA

Se utiliza el mecanismo de descubrimiento de servicios de Docker para la comunicación entre contenedores.

---

## 13. Pruebas

El proyecto incluye pruebas automatizadas para:

- transacciones exitosas;
- fondos insuficientes;
- idempotencia;
- procesamiento concurrente de transacciones.

Las pruebas se ejecutan con:

pytest -v

---

## 14. Gestión de incidentes

El escenario de incidente del desafío está documentado en:

docs/incident-response.md

El análisis *post-mortem* simulado correspondiente está documentado en:

docs/postmortem.md

---

## 15. Limitaciones

Este proyecto es un MVP (Producto Mínimo Viable).

Los siguientes componentes se han simplificado intencionadamente:

- Bancs está representado por un servicio simulado (*mock*);
- la IA está representada por un simulacro funcional;
- no se han implementado la autenticación ni la autorización;
- no se ha implementado una gestión de secretos de nivel de producción;
- no se incluye infraestructura de mensajería distribuida;
- no se han desplegado el servidor Prometheus ni Grafana;
- no se realizan pruebas de rendimiento a gran escala (como 10.000 TPS).

Estos componentes requerirían infraestructura y controles operativos adicionales
en un entorno bancario de producción.