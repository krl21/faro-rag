# faro-rag

Portal de consulta de pólizas y facturas con RAG para **Seguros Faro del Sur** (aseguradora ficticia): ingesta asíncrona de PDF, citas verificables (documento y página) y trazabilidad de punta a punta con OpenTelemetry.

## Requisitos

- Docker y Docker Compose (todo el proyecto se ejecuta en contenedores, también en local).

## Arranque

```bash
make up          # levanta todo; sin .env usa los valores de .env.example (y lo avisa)
make dev         # lo mismo con recarga en caliente (backend y frontend en :5173)
```

| Servicio | URL |
|----------|-----|
| Interfaz web | <http://localhost:3000> (`make up`) · <http://localhost:5173> (`make dev`) |
| API (Swagger) | <http://localhost:8000/docs> |
| Trazas (Jaeger) | <http://localhost:16686> |

La primera vez la API y el worker descargan el modelo de embeddings (~470 MB) a un volumen de caché.

Guías de desarrollo: [`backend/DESARROLLO.md`](backend/DESARROLLO.md) y [`frontend/DESARROLLO.md`](frontend/DESARROLLO.md).

## Arquitectura

```
            POST /documents                         Celery task (Redis broker)
 Cliente ─────────────────────► API FastAPI ───────────────────────────► Worker Celery
    │                              │  guarda PDF (volumen)                   │ extrae texto por página (pypdf | Docling)
    │      GET /documents/{id}     │  registro "pending"                     │ clasificación (PDF completo al LLM); "desconocido" termina aquí
    ├─────────────────────────────►│                                         │ chunking (1000/150) + embeddings (solo pólizas y facturas)
    │      POST /ask               │                                         │ extracción de campos (LLM + Pydantic)
    └─────────────────────────────►│ búsqueda híbrida + LLM + citas          ▼
                                   └────────────► PostgreSQL + pgvector ◄────┘
 API y worker ── OTLP ──► OpenTelemetry Collector ──► Jaeger
```

- **API** (`backend/app/api`): subida con validación de tipo y tamaño, deduplicación por SHA-256, consulta de estado y campos, `/ask` con límite de tasa.
- **Worker** (`backend/app/worker`, `services/document_processor.py`): pipeline idempotente con reintentos y backoff.
- **IA** (`backend/app/ai`): proveedores intercambiables por configuración (`providers/`), ingesta (`ingestion/`), extracción de campos (`extraction/`) y RAG (`rag/`).
- **Datos** (`backend/app/db`): SQLAlchemy 2.0, migraciones con Alembic.
- **Frontend** (`frontend/`): React + TypeScript + Vite, TanStack Query para el polling. En producción nginx sirve la SPA y hace de proxy de `/api` hacia la API (sin CORS ni URL en el código); en desarrollo lo hace Vite.

Las decisiones y sus trade-offs están en [`DECISIONS.md`](DECISIONS.md).

## API

| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/documents` | Sube un PDF. `202` con el id; `200` + `duplicate: true` si ya existía; si existía y había fallado, se reintenta (`202`). |
| `GET` | `/documents` | Lista con estado (`pending`, `processing`, `done`, `failed`). |
| `GET` | `/documents/{id}` | Estado, campos extraídos (valor, confianza, página, tipo de valor, si es editable, valor original) y errores. |
| `PATCH` | `/documents/{id}/fields/{name}` | El usuario corrige o rellena un campo (`edited`); se valida como la salida del LLM y se reindexa para los filtros. |
| `POST` | `/documents/{id}/ask` | Pregunta sobre un único documento, opcionalmente en un rango de páginas, sin interpretar filtros. |
| `POST` | `/ask` | Pregunta dentro de una conversación (`conversation_id`). La convierte en filtros (tipo, fechas, importe, valores a incluir o excluir): si solo hay filtros, lista documentos sin LLM; si no, responde con citas `[n]` usando solo los documentos filtrados. Devuelve los filtros aplicados. |
| `GET` | `/conversations/{id}` | Historial de la conversación. |
| `GET` | `/health`, `/health/ready` | Salud del proceso y de BD, Redis y worker. |

## Variables de entorno

Todas están documentadas en [`.env.example`](.env.example). Para personalizarlas, crea `.env` (`make env`): sus valores prevalecen sobre los del ejemplo. Si no existe `.env`, se usa `.env.example` y el servicio `env-check` lo avisa en la salida de Compose; si no existe ninguno de los dos, Compose da error. Las principales:

| Variable | Por defecto | Descripción |
|----------|-------------|-------------|
| `LLM_PROVIDER` | `fake` | `fake` o `litellm` |
| `LLM_MODEL`, `LLM_API_KEY` | — | Modelo LiteLLM con entrada PDF (p. ej. `gemini/gemini-2.5-flash`) y clave |
| `EMBEDDING_PROVIDER` | `sentence_transformers` | `sentence_transformers`, `litellm` o `fake` |
| `EMBEDDING_MODEL`, `EMBEDDING_DIM` | multilingual MiniLM, `384` | La dimensión debe coincidir con el modelo |
| `PDF_EXTRACTOR` | `pypdf` | `pypdf` o `docling` |
| `LLM_DOCUMENT_INPUT` | `pdf` | Qué recibe el LLM al clasificar y extraer: `pdf` (adjunto completo) o `text` (texto con marcas de página) |
| `CHUNK_SIZE`, `CHUNK_OVERLAP` | `1000`, `150` | Chunking por caracteres |
| `MAX_UPLOAD_MB`, `MAX_PAGES` | `20`, `200` | Límites de los PDF |
| `ASK_RATE_LIMIT` | `10/minute` | Límite de tasa por IP en `/ask` |
| `TIMEZONE` | `America/Toronto` | Zona horaria para "hoy", "ayer"... |
| `CHAT_CONTEXT_TURNS` | `3` | Intercambios anteriores usados como contexto |

## Pruebas

```bash
make test        # unitarios + integración (PostgreSQL y Redis reales de compose, LLM falso)
make test-unit   # solo unitarios
make lint        # ruff
make test-web    # frontend: Vitest + Testing Library + MSW
make lint-web    # frontend: tsc, ESLint y Prettier
```

Ninguna prueba llama a un LLM real.

## Qué está hecho

- Backend completo: subida, procesamiento asíncrono, extracción de campos, RAG con citas, trazas, logs correlacionados y pruebas.

## Qué no está hecho

- Captura de traza.

## Limitaciones conocidas

- Sin autenticación.
- Sin OCR con el extractor por defecto: los PDF escaneados fallan con `no_extractable_text` (Docling está disponible como alternativa).
- Si el proceso cae justo entre guardar el documento y encolar la tarea, el documento puede quedar `pending` (no hay patrón *outbox*).
- Cambiar a un modelo de embeddings de otra dimensión obliga a recrear la tabla `chunks` y reprocesar.
