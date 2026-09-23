# Post-mortem de incidente simulado

## Incidente

Pico de tráfico de transacciones quincenales que provoca una latencia grave en la API y errores en la base de datos.

## Estado

Incidente simulado para el desafío técnico de SmartBancs.

## Resumen

Durante un periodo simulado de alto tráfico, la plataforma de transacciones experimenta un aumento en los tiempos de respuesta y errores relacionados con la base de datos.

La investigación principal se centra en la presión sobre las conexiones a la base de datos, el bloqueo de transacciones y el comportamiento de la concurrencia.

## Impacto en el cliente

Los posibles efectos visibles para el cliente incluyen:

- retraso en las respuestas de las transferencias;
- respuestas de error HTTP;
- intentos de transferencia fallidos temporalmente.

El diseño debe garantizar que las solicitudes fallidas no produzcan actualizaciones parciales del saldo.

## Detección

El incidente se detectaría mediante:

- aumento de la latencia de las transacciones;
- aumento de las métricas de transacciones fallidas;
- métricas de errores de la base de datos;
- registros (logs) de la aplicación;
- monitoreo operativo.

## Cronología

T+00 min:
El monitoreo detecta un aumento en la latencia de las transacciones.

T+02 min:
La tasa de error de las transacciones comienza a aumentar.

T+05 min:
Comienza la investigación sobre conexiones y bloqueos en la base de datos.

T+10 min:
Se identifican transacciones bloqueadas o de larga duración.

T+15 min:
Se aplican medidas de mitigación para el tráfico y la base de datos.

T+25 min:
La latencia de las transacciones comienza a normalizarse.

T+35 min:
La tasa de error se estabiliza y comienza la validación de la recuperación.

Los tiempos indicados son ilustrativos para el escenario simulado.

## Hipótesis sobre la causa raíz

Las áreas técnicas con mayor probabilidad de investigación son:

- exceso de transacciones concurrentes en la base de datos;
- contención de bloqueos en cuentas con acceso frecuente;
- capacidad insuficiente de conexiones a la base de datos;
- consultas lentas o ineficientes;
- transacciones que permanecen abiertas más tiempo del necesario.

Un post-mortem real debe identificar la causa raíz verificada utilizando evidencia del entorno de producción antes de asignar una causa definitiva.

## Factores contribuyentes

Los posibles factores contribuyentes incluyen:

- aumento repentino del tráfico;
- capacidad limitada de conexiones a la base de datos;
- pruebas de carga insuficientes;
- umbrales de alerta inadecuados;
- alta concurrencia sobre los mismos registros de cuenta.

## Lo que funcionó

El diseño de SmartBancs incluye varios controles destinados a proteger la consistencia financiera:

- transacciones de base de datos ACID;
- bloqueo a nivel de fila;
- reversión (rollback) ante fallos;
- idempotencia;
- integración asíncrona con Bancs;
- procesamiento asíncrono mediante IA; - identificadores de correlación;
- métricas de transacciones.

## Acciones correctivas

Las medidas preventivas recomendadas incluyen:

- pruebas de carga y estrés;
- optimización de consultas a la base de datos;
- ajuste del grupo de conexiones (*connection pool*);
- estrategia de reintento para errores de bloqueo transitorios;
- monitoreo de interbloqueos (*deadlocks*);
- planificación de la capacidad de la base de datos;
- alertas sobre latencia y saturación del grupo de conexiones;
- manuales de procedimientos operativos (*runbooks*);
- simulacros periódicos de incidentes.

## Lecciones aprendidas

La coherencia financiera debe preservarse durante los eventos de escalado.

Las dependencias externas (sistemas bancarios e IA) deben mantenerse fuera de la ruta crítica de la transacción.

Las pruebas de rendimiento deben contemplar tanto un alto volumen de transacciones como la contención sobre los mismos registros financieros.