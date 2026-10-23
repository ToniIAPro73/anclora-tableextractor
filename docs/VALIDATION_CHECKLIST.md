# Checklist de validación — TableExtractor

**Cambio:** se retiró el healthcheck Docker que consultaba Neon cada 30 s. El endpoint de salud de la aplicación no se modificó.
**Rama:** `development`
**Validación en desarrollo por Toni:** confirmada
**Preview del SHA publicado:** pendiente
**Promoción:** solicitada con `PROMOTE=FULL`; ejecutar después de la revisión en Preview.

## Verificación del agente

- `git diff --check`: PASS.
- Tests, lint y build: no ejecutados; no solicitados para este cambio localizado de infraestructura.
- No se consultaron ni modificaron datos de aplicación.

## Revisión de Toni

- [x] Validado en desarrollo.
- [ ] Revisar en Preview el SHA publicado y confirmar el comportamiento del despliegue.
- [ ] Tras validar Preview, ejecutar `PROMOTE=FULL`.
