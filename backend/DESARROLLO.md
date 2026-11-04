# Desarrollo local del backend

Guía para trabajar con el backend desde la consola. Todo corre en Docker, también en local. La API y el worker ejecutan **el código de su imagen**. En modo desarrollo, **Docker Compose Watch** copia dentro de los contenedores cada fichero que guardas, así que los cambios se aplican sin reconstruir a mano.

## 0. Primera vez

```bash
cp .env.example .env     # o `make env`; opcional: sin .env se usa .env.example (con aviso)
make lock                # genera backend/uv.lock (solo la primera vez o al cambiar dependencias)
```

## 1. Desplegar en modo desarrollo (actualización automática)

```bash
make dev
# equivale a: docker compose up --build --watch postgres redis migrate api worker otel-collector jaeger
```

Construye las imágenes, aplica las migraciones, levanta los servicios y se queda vigilando los ficheros. La salida de la API y del worker se ve en la misma consola. `Ctrl+C` para todo.

Qué pasa al guardar un fichero:

| Cambias | Qué hace Compose Watch | Tiempo aproximado |
|---------|------------------------|-------------------|
| Código de `backend/` (`app/`, `alembic/`...) | Lo copia en la **API**; `uvicorn --reload` la reinicia | 1-2 s |
| Código de `backend/app/` | Lo copia en el **worker** y **reinicia el contenedor** (Celery no recarga código) | unos segundos (vuelve a cargar el modelo de embeddings); si hay una tarea en curso, espera a que termine |
| `backend/pyproject.toml` o `backend/uv.lock` | **Reconstruye** la imagen y recrea el contenedor | lo que tarde el `build` |

El worker se para de forma ordenada: al recibir la señal de parada, Celery termina la tarea en curso antes de salir. Docker le da hasta **3 minutos** (`stop_grace_period`), lo que tarda en el peor caso un documento con todos los reintentos del LLM. Sin tareas, se para en unos 3 s. Si aun así se agotara el tiempo, la tarea no se pierde: vuelve a la cola y se procesa de nuevo (`acks_late`).

Los **prompts** del LLM están en `backend/app/ai/prompts/**/*.txt`. Se cargan al arrancar cada proceso, así que al guardar uno Compose Watch reinicia la API y el worker, y el cambio se aplica en unos segundos.

Lo que **no** se aplica solo:

- **Una migración nueva** (`alembic/versions/`) se copia, pero hay que aplicarla: `make migrate`.
- **Un cambio en `.env`** necesita recrear los contenedores: `docker compose up -d api worker` (o parar `make dev` y volver a lanzarlo).
- **`tests/`** no se copia a la API ni al worker: los tests se ejecutan con su propio servicio (sección 3).

Para dejar los servicios en segundo plano y vigilar en otra terminal:

```bash
docker compose up -d --build postgres redis migrate api worker otel-collector jaeger
docker compose watch api worker      # vigila los ficheros; Ctrl+C deja de vigilar, los servicios siguen
docker compose logs -f api worker    # en otra terminal, para ver la salida
```

## 2. Desplegar sin actualización automática

```bash
make up-backend     # backend + infraestructura + trazas, con la salida en la consola
make up             # todo el stack
```

Los contenedores ejecutan exactamente el código de la imagen. Para aplicar un cambio, hay que reconstruirla: vuelve a lanzar el comando (incluye `--build`) o usa `docker compose up -d --build api worker`.

## 3. Ejecutar los tests

El servicio `tests` se construye con la imagen de test y **monta la carpeta `backend/`**: siempre prueba el código actual, incluido `tests/`, sin reconstruir. La imagen solo se reconstruye si cambian las dependencias.

```bash
make test           # todos (unitarios + integración)
make test-unit      # solo unitarios
make lint           # ruff check + formato

docker compose --profile test run --rm tests pytest -k chunker -v -s   # uno concreto
```

- `-v`: muestra cada test por su nombre.
- `-s`: muestra los `print` y los logs.

Los tests usan el `postgres` y el `redis` de compose, con una base de datos de test separada (`faro_test`, ver DECISIONS.md, sección 8). **No lances dos ejecuciones de tests a la vez**: comparten esa base de datos y se borran los datos entre sí.

## 4. Terminal dentro del contenedor

```bash
docker compose exec api bash               # entrar en la API ya levantada
docker compose run --rm api bash           # terminal en un contenedor desechable
```

Dentro del contenedor:

```bash
python -c "from app.ai.ingestion.chunker import split_text; print(split_text('hola mundo ' * 200, 100, 20))"
python                                     # REPL con todas las dependencias instaladas
```

## 5. Logs y pruebas de la API

```bash
docker compose logs -f api worker          # seguir la salida en vivo
curl -F "file=@poliza.pdf;type=application/pdf" localhost:8000/documents
curl -s localhost:8000/ask -H 'content-type: application/json' \
     -d '{"question": "necesito las facturas subidas hoy"}'
```

- Documentación interactiva de FastAPI para probar los endpoints desde el navegador: <http://localhost:8000/docs>
- Trazas: <http://localhost:16686> (Jaeger, servicios `faro-api` y `faro-worker`).

## 6. Atajos con Make

```bash
make help         # lista de comandos
make dev          # backend con actualización automática (Compose Watch)
make up-backend   # backend sin actualización automática
make logs         # logs de api y worker
make shell        # terminal en un contenedor de la API
make migrate      # aplicar migraciones (reconstruye la imagen de migraciones si hace falta)
make test         # todos los tests (unitarios + integración)
make test-unit    # solo unitarios
make lint         # ruff check + formato
make format       # aplicar formato
make down         # parar el stack
make clean        # parar y borrar volúmenes (BD, ficheros, caché del modelo)
```

## 7. Entorno local opcional (editor, ruff y tests unitarios)

La aplicación se ejecuta siempre con Docker. Este entorno sirve para que el editor tenga autocompletado y para lanzar `ruff` y los tests unitarios sin contenedores. Todo queda dentro del proyecto (`backend/.tools/` y `backend/.venv/`, ignorados por git y fuera de las imágenes) y no toca el Python del sistema.

**Crearlo** (una vez; `uv` se descarga en `backend/.tools/bin`):

```bash
cd backend
mkdir -p .tools/bin
curl -LsSf https://astral.sh/uv/0.5.11/install.sh | env UV_INSTALL_DIR=.tools/bin UV_NO_MODIFY_PATH=1 sh
export UV_PYTHON_INSTALL_DIR=$PWD/.tools/python UV_CACHE_DIR=$PWD/.tools/cache
.tools/bin/uv python install 3.12
.tools/bin/uv sync --frozen          # dependencias + grupo dev, sin PyTorch ni Docling
```

**Usarlo:**

```bash
cd backend
source .venv/bin/activate
ruff check . && ruff format --check .   # linter y formato
pytest tests/unit -q                    # unitarios (no necesitan BD ni Redis)
deactivate
```

En VS Code, selecciona el intérprete `backend/.venv/bin/python`. Los tests de integración se ejecutan con Docker (sección 3), porque necesitan PostgreSQL y Redis.

**Borrarlo:** `rm -rf backend/.venv backend/.tools`.
