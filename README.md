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

## Stack técnico

| Capa | Tecnología |
|---|---|
| Backend | Python · FastAPI |
| Frontend | React |
| Base de datos | MongoDB |
| Detección de tablas | Modelo de visión/layout + OCR |
| Validación de esquema | Pydantic / JSON Schema |
| Normalización | Python determinista (sin LLM) |

## Estructura del proyecto

```
anclora-tableextractor/
├── backend/          # API, pipeline de extracción, lógica de negocio
├── frontend/          # Interfaz React (carga, revisión, exportación)
├── .emergent/         # Configuración del entorno de build
├── tests/              # Suite de pruebas
└── README.md
```

## Puesta en marcha local

### Requisitos previos

- Python 3.11+
- Node.js 18+ y Yarn
- MongoDB (local o instancia remota)

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

Crea un archivo `.env` en `backend/` con las credenciales necesarias (no incluidas en el repositorio por seguridad):

```
MONGO_URL=
DB_NAME=
LLM_API_KEY=
```

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