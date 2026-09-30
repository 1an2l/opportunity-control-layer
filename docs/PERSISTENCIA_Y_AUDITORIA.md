# Persistencia y auditoría

SQLite conserva cuentas, oportunidades, contactos, señales, evidencia, hipótesis,
incógnitas, alternativas, propuestas, aprobaciones, decisiones, next actions y borradores.

Las claves foráneas impiden registros huérfanos. Una aprobación referencia una alternativa
de la misma oportunidad. Las referencias de una propuesta se validan en aplicación
antes de guardarse; sus listas de IDs se conservan como JSON en columnas específicas.

## Duplicados

- Identificadores repetidos: HTTP 409 mediante restricciones UNIQUE.
- Evidencia: también se rechaza la misma afirmación y fuente, ignorando mayúsculas
  y espacios exteriores, aunque cambie el ID.
- Señales: también se rechaza la combinación exacta oportunidad/título/fuente/fecha.
- No se afirma deduplicación semántica: textos diferentes que narran el mismo hecho
  todavía requieren revisión humana.

## Historial

`audit_events.sequence` preserva el orden de inserción. Los eventos incluyen actor,
fecha UTC, objeto/caso, tipo, resultado, etapa anterior/siguiente cuando corresponda
y explicación. Los triggers rechazan UPDATE y DELETE sobre la tabla de eventos.

La protección se aplica a operaciones normales sobre SQLite. Un administrador con
acceso al archivo puede eliminar triggers o reemplazar la base; no es almacenamiento
WORM ni una firma criptográfica.

## Recuperación

Se confirma una operación completa o ninguna parte. Las pruebas inyectan fallas en
auditoría y verifican que no queden aprobación, decisión o etapa parciales; luego
repiten la solicitud con éxito.

Para respaldar un entorno local, detener el servidor y copiar su archivo de base a una
ubicación privada. No incluir bases ni respaldos en la entrega. Para restaurar, ejecutar
el programa con la ruta de una copia válida; no borrar la base anterior.
El esquema se crea de forma aditiva y no reinserta el seed en una base con cuentas.
No existe todavía un sistema de migraciones versionadas para producción.
