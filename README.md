# BridgeLytic Opportunity Control Layer

Vertical slice local: **señal → evidencia → alternativas → propuesta → decisión humana → siguiente acción**. El producto conserva fuente, procedencia, confianza y auditoría, y no ejecuta acciones externas.

## Ejecutar

Python 3.10+; el producto usa únicamente la biblioteca estándar. Desde esta carpeta:

```powershell
python -m unittest discover -v
python -m opportunity_control --database runtime/entrega.db
```

Abrir **http://127.0.0.1:8000**. No abrir el HTML directamente ni usar Live Server.
La base se crea y carga sólo cuando está vacía. Reiniciar conserva el trabajo.
Para un recorrido nuevo, elegir otra ruta de base; el seed nunca borra una existente.
Detener con `Ctrl+C`.

La terminal muestra dos claves efímeras: **editor** y **revisor**. Introducir la apropiada en
“Clave de sesión local”. Sin clave sólo se consulta. La clave de revisor permite confirmar
una decisión; la de editor no. Las claves caducan al reiniciar y no se guardan en el navegador.
No grabarlas ni compartirlas. Se puede establecer la identidad local al arrancar:

```powershell
python -m opportunity_control --database runtime/entrega.db --editor-name analista --reviewer-name revisor
```

## Recorrido reproducible

1. Seleccionar uno de los tres casos. Revisar señal, fuente, responsable y roles sanitizados.
2. Avanzar a revisión de evidencia. Comparar evidencia, hipótesis e incógnitas por separado.
3. Avanzar a opciones listas. Examinar las dos alternativas con su razón y riesgo.
4. Abrir “Redactar / versionar propuesta”. Elegir una opción, justificarla y seleccionar las referencias.
5. Solicitar `PENDING_APPROVAL`. El expediente queda congelado para revisión.
6. Con clave de revisor, seleccionar la opción final, escribir el motivo y marcar la confirmación explícita.
7. Revisar decisión, aprobador y auditoría. Simular una siguiente acción interna y comprobar el bloqueo externo.
8. Descargar el founder brief JSON. Repetir con los otros casos o crear una oportunidad vacía desde el portafolio.

Para corregir un expediente pendiente, pasarlo a `PAUSED`, agregar información y volver a revisión.
`APPROVED` y `REJECTED` son cierres finales de esta versión. No hay edición ni borrado del historial.
En esos estados, el formulario de transición se sustituye por un aviso: una aprobación
enlaza al seguimiento de acciones internas y un rechazo al historial. Next action no
es otra etapa de aprobación ni habilita ejecución externa.

## Alcance demostrado

- Cuenta, oportunidad, contacto/rol sanitizado, señal, owner, etapa y último movimiento.
- Evidencia con fuente/procedencia; estados `VERIFIED / INFERRED / UNKNOWN`.
- Hipótesis e incógnitas separadas, con confianza explícita.
- Dos o tres alternativas y propuestas versionadas con referencias a evidencia y supuestos.
- Decisión con opción, motivo, propuesta revisada, aprobación humana y fecha.
- Next action con responsable, fecha y estado: pendiente, simulada, bloqueada o cancelada.
- SQLite, transacciones, rollback y eventos append-only de cambios/rechazos asociados al caso.
- API y UI en español; permisos locales por capacidad y bloqueo de acciones externas.
- Borrador determinista persistido, sin LLM, herramientas, red ni autoridad sobre la decisión.

## Datos y dependencias

Los nombres UVA, X-Humanoid y Booster Robotics son etiquetas del alcance; el contenido
operativo del seed es **sintético**. `VERIFIED` sólo indica comprobación frente al
[fixture local](data/SEED_SOURCES.md), nunca validación comercial real.

Siguen pendientes el dataset sanitizado, el repositorio/entorno controlado, el mecanismo
de entrega y la confirmación sobre IA de sandbox. Esta versión permite evaluar el flujo
sin esos accesos; no los sustituye ni declara cerrado el sprint.

## Documentación y entregables

- [Arquitectura de una página](docs/ARQUITECTURA.svg)
- [Modelo de dominio](docs/MODELO_DE_DOMINIO.md)
- [API y ejemplos](docs/API.md)
- [Permisos, límites y operación](docs/SEGURIDAD_Y_OPERACION.md)
- [Persistencia y auditoría](docs/PERSISTENCIA_Y_AUDITORIA.md)
- [Casos de uso y transacciones](docs/CASOS_DE_USO_Y_TRANSACCIONES.md)
- [Límites de IA](docs/IA_GOBERNADA.md)
- [Matriz de aceptación y pendientes](docs/ACEPTACION.md)
- [Resultados de verificación](docs/VERIFICACION.md)
- [Deck ejecutivo: Evidence-to-Decision Vertical Slice](deliverables/BridgeLytic_Vertical_Slice.html)
- [Deck en PDF](deliverables/BridgeLytic_Vertical_Slice.pdf)
- [Arquitectura en PDF, una página](deliverables/BridgeLytic_Arquitectura.pdf)

## Organización

```text
opportunity_control/
  domain/          Entidades, estados y reglas sin SQL/HTTP
  application/     Casos de uso, comandos, brief y puertos
  infrastructure/  SQLite y traducción de objetos a filas
  api/             Permisos HTTP, contratos JSON y servidor local
  ai/              Simulador de borradores, sin LLM
  bootstrap.py     Composición
  seed.py          Fixtures reproducibles
web/               Interfaz modular
data/              Fuentes sintéticas documentadas
tests/             Dominio, persistencia, servicios, API, HTTP y vertical slice
docs/              Documentación técnica
deliverables/      Presentación ejecutiva
scripts/           Empaquetado verificable de la entrega
```

## Verificación

`python -m unittest discover -v` no necesita red, cuentas ni credenciales. Las pruebas
usan bases temporales/en memoria y no alteran la base de trabajo.

La comprobación opcional de navegador está en `tests/browser_check.py`; requiere
Playwright y Microsoft Edge instalados y se ejecuta con `python -m tests.browser_check`.
No es una dependencia de ejecución del producto.

## Límites conocidos

Sandbox local de un solo proceso, no servicio multiusuario de producción. Los tokens
demuestran permisos locales, no SSO ni identidad corporativa. El administrador del
archivo SQLite puede alterar su esquema: append-only no es una garantía criptográfica.
El promedio de confianza es descriptivo, no un ranking ni una probabilidad de negocio.
Correo, CRM, mensajería, compras y calendario permanecen desconectados incluso tras aprobar.
