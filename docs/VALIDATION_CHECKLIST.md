# Checklist de validación — auditoría de puertos locales: scripts de arranque cubiertos

**Alcance:** tras auditar los scripts de arranque de todos los repos, se cubren los que seguían sin liberar su puerto (`preview`, scripts auxiliares de `dev`, `start` de los frontends CRA, `dev:log`) con la llamada a `anclora-infrastructure/scripts/free-port.mjs`, que se omite si el repo hermano no existe. Los frontends CRA liberan solo el puerto del frontend para no matar un backend hermano. En `anclora-visionflow` los scripts `dev:log` y `dev:ps` pasan del 3000 al puerto del registro (3027). En `anclora-impulso` el `BASE_URL` por defecto de Playwright pasa de 3000 a 3008, porque su `dev` ya sirve en el puerto del registro. No cambia código de la aplicación.

## Comprobaciones ejecutadas

| Comprobación | Resultado |
| --- | --- |
| `package.json` válido tras el cambio | PASS |
| Tests de las herramientas (`anclora-infrastructure`) | PASS — 13 tests |
| Ruta relativa a `free-port.mjs` desde `frontend/` | PASS |

## Verificación visual

No aplica: solo scripts de arranque y configuración de tests.

## Promoción

No solicitada en este cambio.
