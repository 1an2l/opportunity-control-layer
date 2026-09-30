# Verificación de la versión local

Fecha: 29 de septiembre de 2026. Entorno comprobado: Windows, Python 3.14 y Microsoft Edge.

| Comprobación | Resultado |
|---|---|
| Suite estándar (`python -m unittest discover -v`) | 62 pruebas correctas |
| Recorrido en navegador real | Propuesta, confirmación, decisión, simulación, bloqueo 403 y auditoría |
| Estados finales en UI | Sin selector vacío; aprobado enlaza a acciones, rechazado a auditoría; al cambiar a un caso abierto se recuperan las transiciones |
| Ancho móvil de 390 px | Sin desbordamiento horizontal |
| Revisión estática de Python y formato | Sin incidencias en la ejecución de Ruff |
| Deck exportado | PDF de 8 páginas |
| Arquitectura exportada | PDF de 1 página |
| Empaquetado | Lista permitida y manifiesto SHA-256 por archivo |

Las pruebas usan SQLite en memoria o directorios temporales. No necesitan el dataset
real ni credenciales de servicios externos. El recorrido visual usa una base temporal
y cierra su servidor al terminar. No se ha desplegado ni contactado a organizaciones.

La reproducción mínima exige sólo Python 3.10+ y la biblioteca estándar. Playwright,
Edge y Ruff son herramientas opcionales de comprobación/exportación, no dependencias
para ejecutar la aplicación o la suite estándar.

Esta verificación no sustituye la revisión técnica del evaluador, una auditoría de
seguridad independiente ni la demo de 5–10 minutos que debe acompañar el handoff.
