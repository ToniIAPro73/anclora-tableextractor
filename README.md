# Anclora TableExtract

**Extracción estructurada de tablas desde PDF hacia Excel, CSV y JSON — con validación por IA y trazabilidad total.**

[![Estado](https://img.shields.io/badge/estado-en%20desarrollo-blue)]()
[![Licencia](https://img.shields.io/badge/licencia-propietaria-lightgrey)]()
[![Stack](https://img.shields.io/badge/stack-Python%20%7C%20FastAPI%20%7C%20React-informational)]()

Parte del ecosistema [Anclora Group](https://group.anclora.com).

---

## Descripción

Anclora TableExtract resuelve el "último 20%" de la extracción de tablas desde documentos PDF: tablas multipágina, celdas fusionadas y escaneados de baja calidad, donde las herramientas genéricas fallan.

El sistema combina un modelo de visión/layout para detectar la estructura de la tabla, un LLM acotado para inferir encabezados, y una capa 100% determinista para normalizar fechas, decimales y unidades. Cada celda exportada incluye un score de confianza y trazabilidad a su página de origen.

## Características principales

- **Extracción híbrida**: detección nativa de texto + fallback a OCR para páginas escaneadas.
- **Score de confianza por celda**: revisión dirigida solo a lo dudoso, no a todo el documento.
- **Normalización determinista**: fechas, decimales y unidades procesados sin intervención de IA, garantizando resultados reproducibles.
- **Exportación múltiple**: `.xlsx`, `.csv` y `.json`, con metadatos de página de origen.
- **Interfaz bilingüe** (ES / EN) con selector de tema claro / oscuro / sistema.
- **Flujo sin fricción**: arrastra el archivo → revisa las excepciones → descarga. Sin chat como punto de entrada.

## Arquitectura

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Frontend   │────▶│   API (FastAPI)   │────▶│  Pipeline de     │
│   React      │     │                   │     │  extracción      │
└─────────────┘     └──────────────────┘     └─────────────────┘
                                                        │
                              ┌─────────────────────────┼─────────────────────────┐
                     ▼                         ▼                         ▼
                     Detección de tablas      Inferencia de columnas    Normalización
                     (visión / layout)         (LLM acotado)            (determinista, Python)
```

Principio de diseño: **IA para interpretar ambigüedad, motor determinista para ejecutar y validar, intervención humana solo ante baja confianza.**

### Integraciones independientes

- **Autenticación:** Google OAuth/OIDC directo con scopes mínimos (`openid email profile`) y sesiones HttpOnly persistidas en PostgreSQL.
- **Inferencia de columnas:** adaptador opcional para una API OpenAI-compatible (`LLM_PROVIDER=openai`); sin proveedor configurado o ante cualquier error se usa el fallback determinista.
- **PDF y thumbnails:** PostgreSQL `BYTEA` por defecto, con adaptador S3-compatible opcional (`OBJECT_STORAGE_BACKEND=s3`). Las miniaturas se generan bajo demanda desde el PDF persistido.
- **Google Sheets:** flujo OAuth independiente del login, solicitado sólo al exportar.

La aplicación no requiere infraestructura privada, paquetes propietarios ni tooling de un proveedor de agentes de desarrollo.

## Stack técnico

| Capa | Tecnología |
|---|---|
| Backend | Python · FastAPI |
| Frontend | React |
| Base de datos | PostgreSQL / Neon |
| ORM / migraciones | SQLAlchemy 2.x / Alembic |
| Detección de tablas | Modelo de visión/layout + OCR |
| Validación de esquema | Pydantic / JSON Schema |
| Normalización | Python determinista (sin LLM) |

## Estructura del proyecto

```
anclora-tableextractor/
├── backend/          # API, pipeline de extracción, lógica de negocio
├── frontend/          # Interfaz React (carga, revisión, exportación)
├── tests/              # Suite de pruebas
└── README.md
```

## Puesta en marcha local

### Requisitos previos

- Python 3.11+
- Node.js 18+ y Yarn
- Acceso a la base de datos Neon de producción (el runtime local es deliberadamente production-backed)

### Instalación

```bash
# Backend
cd backend
pip install -r requirements.txt

# Frontend
cd ../frontend
yarn install
```

### Variables de entorno

Copia `backend/.env.example` a `backend/.env.local` y `frontend/.env.example` a `frontend/.env.local`. Los archivos locales están ignorados por Git y deben tener permisos `0600`.

Variables mínimas del backend:

```
APP_ENV=development
DATABASE_URL=
DATABASE_URL_UNPOOLED=
DATABASE_TARGET=production
ALLOW_PRODUCTION_MIGRATIONS=false
FRONTEND_URL=http://localhost:3000
CORS_ORIGINS=http://localhost:3000
QA_USER_EMAIL=qa.tableextract@anclora.local
LOCAL_QA_LOGIN_ENABLED=false
LOCAL_QA_LOGIN_TOKEN=
GOOGLE_AUTH_CLIENT_ID=
GOOGLE_AUTH_CLIENT_SECRET=
GOOGLE_AUTH_REDIRECT_URI=http://localhost:8000/api/auth/google/callback
LLM_PROVIDER=disabled
LLM_API_KEY=
LLM_BASE_URL=
LLM_MODEL=gpt-4o-mini
OBJECT_STORAGE_BACKEND=database
DATABASE_PDF_MAX_BYTES=15000000
```

El entorno local puede apuntar deliberadamente a Neon producción. Todas las pruebas y sesiones locales deben utilizar exclusivamente el usuario QA dedicado (`QA_USER_EMAIL`); no se deben usar cuentas personales o de clientes.

## Migraciones y QA

Desde `backend/`, consulta el estado con `alembic current` y `alembic history`. Las migraciones contra producción están bloqueadas por defecto; para una ejecución explícita y revisada:

```bash
ALLOW_PRODUCTION_MIGRATIONS=true alembic upgrade head
python -m scripts.seed_qa_user
python -m scripts.cleanup_qa_data              # dry-run
python -m scripts.cleanup_qa_data --execute    # solo datos del usuario QA
```

El endpoint local `POST /api/dev/login` sólo existe con `APP_ENV=development`, `LOCAL_QA_LOGIN_ENABLED=true`, petición desde localhost y la cabecera `X-Local-QA-Token` correcta. Usa la misma tabla de sesiones que el login normal.

### Ejecución

```bash
# Backend
cd backend
uvicorn server:app --reload

# Frontend
cd frontend
yarn start
```

## Roadmap

- [x] Fase 0 — Validación de demanda
- [ ] Fase 1 — MVP: pipeline de extracción + revisión por excepción
- [ ] Fase 2 — Piloto pagado con clientes reales
- [ ] Fase 3 — Especialización vertical (tarifas de proveedores, licitaciones, extractos)

## Licencia

Software propietario. Todos los derechos reservados © Anclora Group.

## Contacto

Antonio Ballesteros Alonso — Anclora Group — [group.anclora.com](https://group.anclora.com)
