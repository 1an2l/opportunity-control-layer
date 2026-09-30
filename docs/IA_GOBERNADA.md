# Límite de IA y declaración de uso

## En el producto

`ai/local.py` implementa un **simulador determinista**, no un modelo generativo ni una
llamada de IA real. Resume registros y muestra la primera alternativa ordenada por ID.
Esa selección no es evaluación, puntuación ni recomendación comercial.

`POST .../ai-draft` guarda la salida íntegra y el evento `AI_DRAFT_GENERATED`.
El brief permite inspeccionarla después de recargar o reiniciar. La salida declara
proveedor lógico, modo, versión, limitaciones y revisión humana obligatoria.

El borrador no crea evidencia, propuestas aprobadas, etapas ni autorizaciones. La
persona debe redactar una propuesta trazable; después, un revisor distinto en términos
de permiso puede confirmar la decisión. La demo puede ser operada por una sola persona
usando capacidades separadas; no se afirma segregación corporativa de identidades.

## Para integrar un modelo de sandbox

Se requiere confirmar la expectativa de evaluación, el proveedor, las credenciales
autorizadas y qué datos pueden salir del entorno. Habría que incorporar validación
estructurada de salida, timeouts, manejo de fallas, límites de costo, redacción de
información sensible y evaluaciones. No se conectó ningún proveedor en esta entrega.

Cualquier integración futura debe conservar las mismas barreras: proponer no aprueba;
aprobar no ejecuta. El modelo no recibe claves de revisor ni herramientas productivas.

## En el desarrollo

Se utilizó asistencia de IA para implementar, documentar y revisar el software. Las
capacidades declaradas se contrastan con pruebas automatizadas y un recorrido de
navegador. Los fixtures están marcados como sintéticos; no se presentan inferencias
generadas como hechos de las organizaciones.
