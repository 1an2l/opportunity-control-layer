# Permisos y operación segura

## Matriz de capacidades HTTP

| Capacidad | Lectura local | Editor | Revisor |
|---|---:|---:|---:|
| Consultar expedientes, brief y eventos | Sí | Sí | Sí |
| Capturar y planear trabajo interno | No | Sí | Sí |
| Cambiar etapas no finales / pausar | No | Sí | Sí |
| Aprobar o rechazar decisión final | No | No | Sí |
| Ejecutar acciones externas | No | No | No |

El servidor emite tokens secretos independientes al arrancar. Se entregan sólo en
la terminal del operador y caducan al reiniciar. El actor se toma del token, no de
un campo JSON manipulable. El revisor debe enviar `confirmed: true`, motivo, opción
y propuesta vigente para aprobar. El token no sustituye esa confirmación.

El servidor sólo se enlaza a localhost. Valida Host, rechaza Origin ajeno en escritura,
exige JSON y limita cuerpos a 256 KiB. No sirve archivos arbitrarios: sólo recursos
web en una lista explícita. No hay conectores ni credenciales productivas.

## Frontera de confianza

Los GET son legibles por cualquier proceso local que pueda acceder al puerto. Los
tokens son capacidades de sandbox, no autenticación multiusuario/SSO. Quien controla
la terminal, el código o la base tiene control administrativo: no usar datos sensibles
o productivos en esta versión. La API en proceso y los servicios Python son interfaces
internas confiables; la autorización de peticiones se aplica en el adaptador HTTP.

No se registra el valor de los tokens. La UI los mantiene en memoria, no en localStorage.
Evitar mostrar la terminal con claves durante una grabación; reiniciar después de ella.

## Antes de conectar producción

Aprobación escrita de alcance, ambiente y datos; autenticación y autorización corporativa;
gestión de secretos; TLS; aislamiento de red; políticas de retención y respaldo probado;
migraciones; concurrencia y monitoreo; auditoría resistente a manipulación; evaluación
del proveedor de IA; revisión de seguridad independiente y autorización por herramienta.

Nada de lo anterior habilita automáticamente email, CRM, compras, calendario u outbound.
Durante este sprint siguen bloqueados incluso con una decisión interna aprobada.
