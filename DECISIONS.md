# Decisiones técnicas

- [Decisiones técnicas](#decisiones-técnicas)
  - [1. Troceo y recuperación](#1-troceo-y-recuperación)
  - [2. Idempotencia y consistencia](#2-idempotencia-y-consistencia)
  - [3. Campos de baja confianza](#3-campos-de-baja-confianza)
  - [4. Uso de IA generativa](#4-uso-de-ia-generativa)
  - [5. Respuestas del chat](#5-respuestas-del-chat)
  - [6. Filtros en el chat](#6-filtros-en-el-chat)
  - [7. Datos extraídos: campos fijos y datos libres](#7-datos-extraídos-campos-fijos-y-datos-libres)
  - [8. Procesamiento y fallos](#8-procesamiento-y-fallos)
  - [9. Proveedores y prompts](#9-proveedores-y-prompts)
  - [10. Observabilidad](#10-observabilidad)
  - [11. Seguridad](#11-seguridad)
  - [12. Pruebas y CI](#12-pruebas-y-ci)
  - [13. Frontend](#13-frontend)
  - [14. Otras decisiones](#14-otras-decisiones)

## 1. Troceo y recuperación

**Problema.** Recuperar el fragmento correcto para cada pregunta, citar una página exacta y decidir cuándo no hay evidencia, sin inventar.

**Decisión.**
- **Troceo por caracteres:** 1000 con 150 de solapamiento, cortando en el último espacio. Ningún fragmento cruza páginas: cada uno tiene una sola página que citar.
- **Tablas por filas enteras.** Las líneas `| a | b |` del Markdown de Docling se trocean aparte: ninguna fila se parte, y cada fragmento repite la cabecera de la tabla y el título de sección que la precede. Una fila más larga que el tamaño definido va entera en su propio fragmento.
- **Búsqueda híbrida:** vectorial (pgvector, coseno, índice HNSW) y de texto completo de PostgreSQL (`tsvector` en español, `websearch_to_tsquery`, índice GIN), combinadas con *Reciprocal Rank Fusion* (`RETRIEVAL_RRF_K=60`). El texto completo encuentra lo que los embeddings recuperan mal (números de póliza, importes, matrículas); RRF combina rankings sin normalizar puntuaciones de escalas distintas.
- **Evidencia.** Un fragmento cuenta si su similitud es ≥ `RETRIEVAL_MIN_SIMILARITY` (0.35) o si contiene todas las palabras de la pregunta. Sin evidencia no se llama al LLM y se responde "No hay información suficiente para responder.". Si el LLM no encuentra respuesta en las fuentes, devuelve un texto fijo y se responde lo mismo; una respuesta sin ninguna cita válida se descarta.
- **Raíces, no lemas.** El texto completo usa el stemmer de español de PostgreSQL ("renovación" y "renovó" → `renov`). Falla con verbos irregulares ("hizo" / "hacer"), pero la búsqueda vectorial ya cubre el significado y el texto completo aporta sobre todo en identificadores, que el stemming no altera.

**Descartado.**
- Contar por tokens: depende del tokenizador de cada modelo y el proveedor es intercambiable.
- Búsqueda solo vectorial: falla con identificadores exactos.
- Lematizar (`simplemma`, `spaCy` o un diccionario Hunspell en PostgreSQL): dependencia nueva o imagen de PostgreSQL propia, migración y reindexado, para una mejora marginal.

**Consecuencias.** La configuración `'spanish'` está en la columna generada `tsv` y en `TS_CONFIG` (`app/db/repositories/chunks.py`); si cambia una sin la otra, la búsqueda deja de encontrar resultados sin dar error.

## 2. Idempotencia y consistencia

**Problema.** Evitar duplicados y estados a medias si el worker muere, la tarea se reintenta o Redis falla.

**Decisión.**
- **Subidas duplicadas:** el documento se identifica por el SHA-256 de su contenido (columna única, que también resuelve dos subidas simultáneas). Subir el mismo fichero devuelve el existente con `duplicate: true`.
- **Guardado atómico:** fragmentos, campos y datos libres se reemplazan (borrar + insertar) en una sola transacción junto con el paso a `done`. Reprocesar o reintentar nunca duplica, y una restricción única (documento, página, índice) lo garantiza también en la base de datos. Si el worker muere a mitad, no se confirma nada y quedan los datos anteriores.
- **Entrega:** `acks_late`, `reject_on_worker_lost` y `prefetch_multiplier=1`. La tarea se confirma al terminar y se reencola si el worker muere; al ser idempotente, repetirla es inocuo. El `visibility_timeout` de Redis (1 h) supera la tarea más larga.
- **Orden:** la tarea se encola después de confirmar el registro, para que el worker siempre lo encuentre.
- **Redis caído al encolar:** el documento queda `failed` con `queue_unavailable`, la API responde `503` y el fallo queda en el log (`ERROR`) y en la traza. Volver a subir el mismo PDF lo reencola (`202`). Esto vale para cualquier `failed`: un error permanente simplemente vuelve a fallar igual.

**Descartado.** Patrón *outbox* o un proceso que reencole los `pending` antiguos: cubre todos los casos, pero añade otro componente y lógica de concurrencia.

**Limitación.** Si el proceso cae justo entre el commit y el encolado, el documento queda `pending`.

## 3. Campos de baja confianza

**Problema.** Qué hacer con un campo que el LLM extrae con poca seguridad: rechazarlo, marcarlo para revisión o dejarlo pasar.

**Decisión.**
- **No se rechaza ningún campo por su confianza.** Se guarda y se marca para revisión humana. En la UI, un campo `ok` con confianza `low` aparece como **"Por revisar"**, con borde ámbar y el aviso "Confianza baja: revisa antes de usar"; `medium` y `high` se muestran como correctos con su etiqueta.
- **Confianza como etiqueta** (`low`, `medium`, `high`), sin número: un LLM no da probabilidades calibradas, y un 0,87 aparentaría una precisión que no tiene.
- **Estados del campo:**

  | `status` | Cuándo | `value` | `confidence` | `error` |
  |---|---|---|---|---|
  | `ok` | Valor válido | el valor | la del LLM | `null` |
  | `not_found` | El documento no lo contiene | `null` | `null` | `null` |
  | `failed` | Valor inválido tras los reintentos | `null` | `null` | explícito |
  | `edited` | El usuario lo corrigió o lo rellenó | el del usuario | `null` | `null` |

  Un campo ausente no es un error ni se reintenta: reintentar no hace aparecer el dato.
- **Página de origen.** El LLM indica la página de cada valor, para que el usuario lo compruebe. Una página imposible (0, texto o mayor que el total) se descarta (`null`) en vez de reintentar.
- **Corrección por el usuario.** `PATCH /documents/{id}/fields/{name}` valida el valor con el mismo tipo Pydantic que la salida del LLM. El campo pasa a `edited`, `original_value` guarda el valor del LLM la primera vez y se recalculan sus columnas de filtro en la misma transacción. También se rellenan los `not_found` y `failed`. `DELETE` borra el campo (los filtros y el chat dejan de usarlo).
- **`document_type`** no se edita ni se borra: decide qué campos corresponden al documento.

**Limitación.** Reprocesar un documento sustituye sus campos: se pierden las ediciones y los borrados.

## 4. Uso de IA generativa

Se usó un asistente de IA (Claude Code) en todas las fases del desarrollo. El asistente generó el código; la validación de los requisitos, las decisiones de arquitectura y la verificación del resultado fueron responsabilidad del autor.

**Proceso.**
1. **Requisitos.** El asistente los extrajo del enunciado y se validaron antes de diseñar.
2. **Arquitectura.** Se partió de una propuesta del asistente y se modificó lo que no estaba claro o admitía una solución mejor, por ejemplo las dependencias entre módulos.
3. **Especificaciones.** Antes de generar código se concretaron, requisito a requisito, las funciones y los comportamientos esperados.
4. **Ambigüedades.** Se pidió al asistente una lista de los puntos confusos de cada petición, para resolverlos antes de implementarlos.
5. **Código y pruebas.** Con los tests ya avanzados, los flujos se probaron a mano y se corrigieron los comportamientos basados en suposiciones del asistente y no en lo especificado.

**Backend.** Las salidas de los endpoints se validaron manualmente.

**Frontend.** El código de `frontend/` lo generó el asistente a partir del diseño y de los requisitos definidos por el autor: vistas, paleta, polling, política de confianza, edición de campos y chat por documento. Para cada vista se especificaron su tipo, sus componentes y su comportamiento, y el asistente las conectó a los endpoints del backend para cubrir los requisitos funcionales ya revisados.

**Celery.** Era una tecnología nueva para el autor. Como el procesamiento de un documento puede tardar, se definió el comportamiento que debía tener el trabajo en segundo plano y el asistente implementó la parte de Celery a partir de esa definición.

**OpenTelemetry.** Se definieron las funciones y los momentos del flujo que debían quedar trazados, y el asistente ajustó la instrumentación a esa lista. En varios flujos se comprobó en Jaeger que las trazas estaban completas y contenían la información requerida.

## 5. Respuestas del chat

**Problema.** Responder solo con lo que dicen los documentos, citar cada afirmación y no perder una respuesta útil por una parte sin información.

**Decisión.**
- **Fuentes numeradas.** El LLM recibe cada fuente entre etiquetas (`<dato>` para un campo o dato extraído, `<fragmento>` para texto), con su número, documento y página, y debe terminar cada afirmación con su cita `[n]`.
- **Comprobación posterior en el backend:** se eliminan las citas a fuentes que no existen y se renumeran por orden de aparición (`[1]`, `[2]`…): con `n` citas, ningún marcador supera `n`. Es un paso del backend, no del LLM.
- **Respuestas parciales.** Si la pregunta pide varias cosas, el LLM responde las que tienen fuente y escribe "No aparece en la documentación." en las demás, solo si hay otra parte respondida. Si no puede responder nada, devuelve un texto fijo (`NO_EVIDENCE`) y se muestra "No hay información suficiente para responder.".
- **Preguntas sobre un documento** (`POST /documents/{id}/ask`): no se interpretan filtros, porque con el documento elegido sobran o se contradicen. El LLM recibe los campos extraídos del documento, sus `RETRIEVAL_FACTS_TOP_K` (15) datos libres más relacionados con la pregunta y los fragmentos de la búsqueda híbrida, opcionalmente en un rango de páginas. Así responde comprobaciones ("corrígeme si la factura es de 2003") aunque ningún fragmento supere el umbral. Un documento que no está `done` da `409`.
- **Conversaciones:** tabla `conversations` con los mensajes en una columna JSONB. El añadido es atómico (`messages = messages || :nuevos`), así que dos preguntas simultáneas no coexisten.

**Descartado.** Una tabla con una fila por mensaje: más normalizada, pero el historial siempre se lee completo.

**Resultado** con el dataset de `samples/` y Claude Haiku 4.5: 24 de 27 preguntas correctas. En las otras 3 (q13, q21 y q24), el dato está en el documento, pero el sistema responde que no hay información: no inventa. La causa está pendiente de analizar.

## 6. Filtros en el chat

**Problema.** Peticiones como "las facturas guardadas ayer", "las pólizas A, B y C" o "todas menos la póliza S" no se resuelven con similitud: hay que filtrar por campos y respetar las negaciones, con el mínimo de llamadas al LLM.

**Decisión.**
- **La pregunta se convierte en filtros** que se aplican en SQL antes de buscar: tipo de documento, fecha de subida, fecha del documento, importe y valores a incluir o excluir. Los campos admitidos son una lista cerrada validada con Pydantic, y los valores van siempre como parámetros: el LLM nunca decide el SQL.
- **Reglas primero.** `app/ai/query/` resuelve sin LLM tipos, fechas relativas y explícitas, importes ("más de", "entre"), identificadores con etiqueta o reconocibles por su forma (póliza, NIF, matrícula) y negaciones ("no", "excepto", "salvo").
- **LLM solo si queda algo sin resolver** (una negación sin objetivo claro, "el trimestre pasado", un nombre de persona o empresa, "¿y la de B?"), con los 3 últimos intercambios como contexto (`CHAT_CONTEXT_TURNS`). Si responde algo inválido tras los reintentos, se usan los filtros de las reglas.
- **Solo filtros, sin pregunta** ("las facturas de ayer"): se devuelve la lista de documentos sin búsqueda ni respuesta del LLM.
- **El cliente puede enviar los filtros** y la respuesta devuelve los aplicados, para mostrarlos y corregirlos.
- **Interpretación:**
  - "Subidas" o "guardadas" usan la fecha de subida; "emitidas" o "vigentes", la del documento. Sin verbo, lo relativo ("ayer") se refiere a la subida y las fechas de calendario, al documento.
  - Fecha del documento: el solapamiento de la vigencia (póliza) o la fecha de emisión (factura).
  - Identificadores comparados tras normalizar (`fw-23` = `FW 23`); titulares por coincidencia parcial ("Pérez" encuentra "Juan Pérez García").
  - "Hoy" y "ayer" en `TIMEZONE` (`America/Toronto`), con nombre IANA para que el horario de verano se aplique solo.

**Descartado.**
- Pedir siempre los filtros al LLM: más robusto con cualquier redacción, pero una llamada más por pregunta.
- Solo reglas: no resuelven nombres ni referencias al historial.

**Limitación.** El filtro por emisor (`emisor`) está admitido, pero ningún prompt de extracción obtiene el emisor, así que no encuentra nada.

## 7. Datos extraídos: campos fijos y datos libres

**Problema.** Pólizas y facturas dan casi toda su información como etiquetas junto a valores, en tablas o en líneas. Extraer solo una lista fija de campos dejaba el resto (VIN, forma de pago, líneas de la factura, base imponible…) en los fragmentos, donde la búsqueda por similitud encuentra mal un dato concreto. Además, el LLM a veces se saltaba un campo que sí estaba.

**Decisión.**
- **Campos fijos** por tipo, extraídos por el LLM y validados con Pydantic: póliza (número, vigencia, coberturas), factura (importe, fecha, número de póliza) y, en ambos, titular, NIF y matrícula. Son pocos a propósito: cada campo cuesta tokens en cada extracción.
- **Datos libres, extraídos con Docling sin LLM** (`app/ai/ingestion/fact_parsing.py`): deterministas, gratis, con su página y sin inventar.
  - Tablas verticales (etiqueta y valor por fila): un dato por fila.
  - Tablas horizontales (etiquetas en la cabecera y una fila de valores): un dato por columna.
  - Tablas de registros (cabecera y varias filas): un dato por fila con todas sus columnas, para que cada fila se entienda y se cite sola.
  - Fuera de tablas: `Etiqueta: valor`, una etiqueta seguida de su valor en la línea siguiente, `Base imponible 33.465,00 €` y `… N.º código`. Se descarta la prosa con dos puntos (etiqueta de más de 6 palabras o valor de más de 150 caracteres).
- **Una sola tabla, `extracted_fields`**, con pares `(label, value)` y el booleano `is_predefined`:
  - `true`: campo fijo (`label` = `invoice_amount`…), único por documento, con columnas tipadas para filtrar.
  - `false`: dato libre (`label` tal como aparece, puede repetirse), con página, posición en la tabla y `embedding`. Una fila de tabla se guarda como lista de `{column, value}` para conservar el orden de sus columnas, que un objeto JSONB no mantiene.
- **Columnas de filtro en la misma fila** que el valor: `text_value` (identificadores y nombres normalizados; B-tree e índice trigram para `LIKE '%…%'`), `number_value` + `currency` y `date_from` / `date_to`, cada una con su índice. Se rellenan en la misma transacción que el valor, al procesar y al editar.
- **Uso de los datos libres:**
  - Ayudan a la extracción: el prompt de los campos fijos incluye la lista de datos detectados, para que el LLM no se salte un valor.
  - En las preguntas sobre un documento, entran los 15 más relacionados con la pregunta (unos 250 tokens), elegidos por similitud y por palabras (basta una en común: es un solo documento).
  - En el chat general compiten con los fragmentos por los mismos `RETRIEVAL_TOP_K` puestos y con las mismas reglas de evidencia (todas las palabras: con una sola, casi cualquier factura coincidiría).
  - El usuario puede editarlos y borrarlos (`PATCH` y `DELETE /documents/{id}/facts/{fact_id}`); al editar se guarda el original y se recalcula el vector.
- **Documentos que no son pólizas ni facturas** (`unknown`): el worker clasifica antes de trocear y, si es `unknown`, se detiene, así que no se gastan embeddings ni la segunda llamada al LLM. El documento queda `done`, aparece en la lista y queda fuera del chat (`409 document_not_queryable`). Cualquier tipo que devuelva el clasificador fuera de póliza o factura se guarda como `unknown`.

**Descartado.**
- Pedir al LLM todos los pares del documento: respuesta larga y cara, y más riesgo de saltarse o inventar datos.
- Un registro por celda de tabla: `Importe: 1.280,00 €` no diría de qué concepto es.
- Filtrar sobre el JSON (`value->>'amount'`), con índices de expresión o con una columna JSONB en `documents`: sin índice útil para rangos y búsquedas parciales, y la normalización tendría que repetirse en SQL.
- Una base de datos documental: encajaría con el esquema flexible, pero PostgreSQL da en un solo almacén documentos, vectores, texto completo, filtros y conversaciones.

**Limitaciones.**
- Si el LLM clasifica mal una póliza o una factura como `unknown`, queda fuera del chat y el usuario no puede corregir el tipo.
- Un PDF con varios documentos dentro recibe un solo tipo.

## 8. Procesamiento y fallos

**Problema.** Extraer bien tablas y pares "campo: valor", tratar PDF corruptos, escaneados o demasiado grandes y sobrevivir a fallos del proveedor.

**Decisión.**
- **Solo Docling** para extraer el texto: entiende la maquetación y las tablas, y hace OCR. Se eliminó pypdf, que devuelve el texto seguido sin saber qué valor va en cada columna, y con él la variable `PDF_EXTRACTOR`: dos extractores eran dos comportamientos que probar.
  - Antes de convertir, pypdfium2 cuenta las páginas: un PDF corrupto, cifrado o de más de `MAX_PAGES` páginas se rechaza en milisegundos.
  - El conversor se crea una vez por proceso del worker, no en cada documento.
  - Solo la imagen del worker lleva Docling; la API no extrae texto.
- **El LLM recibe el PDF completo en las dos llamadas** (clasificar y extraer), como adjunto con LiteLLM: ve todas las páginas, con tablas y maquetación. Clasificar con los primeros 12 000 caracteres fallaba con portadas largas y, si el tipo salía mal, casi todos los campos quedaban `not_found` sin error visible. `LLM_DOCUMENT_INPUT=text` envía el texto con marcas `[Página n]` para modelos sin entrada PDF; un único punto (`build_document_message`) decide qué se envía.
- **Errores permanentes**, sin reintento y con código en la API y la UI: `corrupt_pdf`, `no_extractable_text`, `too_many_pages`. Tipo y tamaño se validan al subir (`415`, `413`) por la firma `%PDF-`, no solo por la extensión.
- **Errores transitorios** (proveedor o base de datos): la tarea se reintenta con backoff exponencial y jitter (3 reintentos, de 5 s a 60 s). Al agotarse, el documento queda `failed`.
- **Respuestas inválidas del LLM:** se reenvían al modelo con el error de validación (esperas de 2 y 6 s, 3 intentos). Cada campo se valida por separado: uno inválido no invalida los demás.
- **Timeouts:** 20 s por llamada al LLM y 10 s por llamada de embeddings remota.

**Descartado.**
- Una sola llamada que clasifique y extraiga: un JSON inválido obliga a repetirlo todo.
- Clasificar con una muestra del texto, o reclasificar con el PDF solo si la confianza es baja: heurístico o tardío.

**Consecuencias.**
- Docling tarda de segundos a decenas de segundos por documento en CPU y descarga sus modelos la primera vez; cada proceso del worker (`WORKER_CONCURRENCY`) carga su copia.
- El PDF se envía dos veces por documento (y en cada reintento) y se cobra por página.
- Con `LLM_DOCUMENT_INPUT=pdf`, el modelo debe aceptar PDF. Al arrancar, el worker lo comprueba con el mapa de modelos de LiteLLM y avisa si no.

## 9. Proveedores y prompts

**Problema.** Cambiar de proveedor de LLM o de embeddings sin tocar código, probar sin llamar a un modelo real y mantener los prompts legibles.

**Decisión.**
- **Interfaces propias** (`LLMProvider`, `EmbeddingProvider`) elegidas por variable de entorno: LLM `litellm` o `fake`; embeddings `sentence_transformers` (local, multilingüe, 384 dimensiones), `litellm` o `fake`. Con LiteLLM se cambia a Gemini, OpenAI, Claude… solo con `LLM_MODEL`.
- **Proveedor falso determinista** (expresiones regulares y embeddings por *hashing* de palabras): la demo y los tests funcionan sin red ni clave.
- Un envoltorio (`Traced*Provider`) añade el span a cualquier implementación, también a la falsa.
- **Dimensión del vector:** al arrancar, la API y el worker comprueban que coinciden proveedor, configuración y base de datos.
- **Prompts en `backend/app/ai/prompts/`**, un `.txt` por mensaje completo, cargados una vez por proceso. El código solo elige el fichero y rellena valores (`$nombre`, con `string.Template`, porque los prompts tienen ejemplos JSON con llaves). Si falta un valor, falla en lugar de enviar un `$campo` vacío. Un test comprueba que los bloques repetidos (reglas de seguridad, de los campos) son idénticos en todos los ficheros.

## 10. Observabilidad

**Problema.** Seguir una petición desde HTTP hasta la tarea Celery y la llamada al LLM, con datos útiles y sin exponer contenido.

**Decisión.**
- OpenTelemetry con exportador OTLP → Collector → Jaeger. La aplicación no depende de Jaeger: otro destino solo cambia la configuración del Collector.
- Instrumentación automática de FastAPI, SQLAlchemy, Redis y Celery. La de Celery propaga el contexto en las cabeceras de la tarea, así que **una sola traza** cruza la petición, la tarea y las llamadas al LLM. En el worker se inicializa en cada proceso hijo (`worker_process_init`).
- Spans propios por paso (`ingest.extract_text`, `extract.classify`, `ingest.chunk`, `ingest.embed`, `extract.fields`, `rag.answer`, `llm.complete`…) con atributos como `document.id`, `pdf.pages`, `chunks.count`, `rag.fragments`, `rag.citations`, `llm.latency_ms` y `gen_ai.usage.input_tokens` / `output_tokens`. Las trazas no guardan texto de documentos, preguntas ni claves.
- Logs JSON con `trace_id` y `span_id`: `INFO` con ids, contadores y duraciones; `DEBUG` añade el contenido.
- `/health/ready` comprueba base de datos, Redis y worker (`ping` a través del broker) y devuelve `503` con el detalle si algo falla.

**Consecuencia.** `sqlalchemy<2.1`: la instrumentación de OpenTelemetry aún no admite la 2.1 (no genera spans de SQL).

## 11. Seguridad

**Decisión.**
- **Subida:** extensión, MIME, firma `%PDF-` y tamaño (`MAX_UPLOAD_MB`). El fichero se guarda con su hash como nombre.
- **Secretos:** ninguno en el repositorio; `.env` está ignorado y solo se versiona `.env.example`.
- **Límite de tasa** en `/ask` y `/documents/{id}/ask` (`slowapi`, contadores en Redis, por IP).
- **Prompt injection desde los PDF:**
  - el contenido va entre etiquetas (`<documento>`, `<fragmento>`, `<dato>`) y se neutralizan las que aparezcan dentro, para que no pueda cerrarlas;
  - el prompt de sistema ordena tratarlo solo como datos e ignorar sus instrucciones;
  - la salida de la extracción se valida con Pydantic;
  - solo se aceptan citas a fuentes realmente enviadas;
  - el LLM no tiene herramientas: el daño posible se limita a una respuesta incorrecta.

**Limitaciones.**
- Con `LLM_DOCUMENT_INPUT=pdf` no se pueden neutralizar etiquetas dentro del fichero, porque se envía sin modificar; quedan las demás medidas.
- Sin autenticación: el enunciado no la pide.

## 12. Pruebas y CI

**Problema.** Probar la API y la tarea Celery con PostgreSQL real y el LLM falso, igual en local que en CI.

**Decisión.**
- **Servicio `tests` en Compose**, con la imagen del backend, conectado a `postgres` y `redis` por la red de Compose y a una base de datos propia (`faro_test`). Monta `backend/`, así que prueba siempre el código actual. El CI usa el mismo servicio.
- Los tests no instalan Docling ni PyTorch: un extractor de prueba (`tests/fixtures/text_layer_extractor.py`) lee la capa de texto de los PDF de prueba con el mismo contrato.
- **CI** con dos jobs: backend (ruff y pytest en el servicio `tests`) y frontend (tipos, lint, formato, tests y build).

**Descartado.** testcontainers: con pytest dentro de un contenedor obliga a montar el socket de Docker, complica la red y da a los tests control total sobre el daemon.

**Consecuencia.** Las pruebas comparten `faro_test`: no se pueden lanzar dos ejecuciones a la vez.

## 13. Frontend

**Decisión.**
- **Stack:** React 18 + TypeScript + Vite, TanStack Query (datos, caché y polling) y CSS Modules. Sin router: el menú cambia la vista sin recargar.
- **Polling** solo mientras algún documento está `pending` o `processing`: `GET /documents` cada 3 s, que se detiene cuando todos están `done` o `failed`; la vista de campos aplica la misma regla a `GET /documents/{id}`. La regla es una función pura con pruebas (`lib/polling.ts`).
- **Chat por documento:** la UI obliga a elegir un documento procesado y usa `POST /documents/{id}/ask`. Las respuestas son más predecibles y hay menos casos que probar; `POST /ask`, con filtros sobre todos los documentos, sigue disponible en la API.
- **Errores visibles:** cada `code` de la API se traduce a un texto en español; una respuesta sin evidencia se muestra en un bloque propio, distinta de una respuesta normal.
- **Edición:** el editor de cada campo lo decide el `value_type` que envía la API, sin duplicar la lista de campos del backend.
- **Sin URL ni claves en el código:** la SPA llama a `/api` en su origen; hacen de proxy nginx en producción y Vite en desarrollo.
- **Pruebas:** Vitest, Testing Library y MSW, que simula la API a nivel de red.

**Descartado.** Un `setInterval` propio para el polling: limpieza, peticiones solapadas y caché entre vistas a mano.

## 14. Otras decisiones

- **`POST /documents`** responde `202` cuando se encola trabajo (documento nuevo o duplicado fallido que se reintenta) y `200` cuando es un duplicado sin trabajo pendiente. Se descartó `409`: un duplicado no es un error del cliente.
- **Idioma:** código, campos y mensajes de la API en inglés; prompts y respuestas del chat en español, porque los documentos están en español.
- **SQLAlchemy síncrono**, compartido por la API y el worker (Celery es síncrono); los endpoints con base de datos son `def` y FastAPI los ejecuta en un pool de hilos.

---

Este documento está en español porque sus lectores principales son hispanohablantes.
