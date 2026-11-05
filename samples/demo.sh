#!/usr/bin/env bash
# Demo de punta a punta: sube los PDF de samples/pdfs/, espera a que se procesen
# y lanza cada pregunta de samples/questions.json contra su documento
# (POST /documents/{id}/ask, con el PDF de su campo "document"), comparando si
# responde (o no) con lo esperado.
#
# La subida es idempotente: un PDF ya subido devuelve su id sin procesarse de
# nuevo, así que la demo se puede repetir sin duplicar documentos.
#
# Requisitos: el stack levantado (make up o make dev), curl y jq.
#
# Uso:
#   samples/demo.sh                 # subir (o reutilizar), esperar y preguntar
#   samples/demo.sh --only q1,q25   # solo esas preguntas
#
# Variables:
#   API_URL      URL de la API (por defecto http://localhost:8000)
#   ASK_PAUSE    segundos entre preguntas (por defecto 7: el límite es 10/minuto)
#   WAIT_TIMEOUT segundos máximos esperando a que se procese cada documento (600)
#   SETTLE_SECONDS pausa tras procesar todos, antes de la primera pregunta (10)
set -euo pipefail

API_URL="${API_URL:-http://localhost:8000}"
ASK_PAUSE="${ASK_PAUSE:-7}"
WAIT_TIMEOUT="${WAIT_TIMEOUT:-600}"
SETTLE_SECONDS="${SETTLE_SECONDS:-10}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PDF_DIR="$HERE/pdfs"
QUESTIONS="$HERE/questions.json"

only=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --only) only="${2:?--only necesita una lista de ids, p. ej. q1,q2}"; shift ;;
    -h|--help) sed -n '2,21p' "$0"; exit 0 ;;
    *) echo "Opción desconocida: $1" >&2; exit 2 ;;
  esac
  shift
done

for tool in curl jq; do
  command -v "$tool" >/dev/null || { echo "Falta $tool: instálalo para ejecutar la demo." >&2; exit 1; }
done
curl -fsS "$API_URL/health" >/dev/null 2>&1 || {
  echo "La API no responde en $API_URL. Levanta el stack con 'make up' o 'make dev'." >&2
  exit 1
}
[[ -f "$QUESTIONS" ]] || { echo "No existe $QUESTIONS: genera el lote con generate_samples.py." >&2; exit 1; }

bold=$'\e[1m'; green=$'\e[32m'; red=$'\e[31m'; dim=$'\e[2m'; reset=$'\e[0m'

# --- 1. Subir los PDF y esperar a que terminen ---------------------------------
# PDF name -> document id, as JSON (macOS ships bash 3.2, without associative arrays).
doc_ids='{}'
{
  shopt -s nullglob
  pdfs=("$PDF_DIR"/*.pdf)
  [[ ${#pdfs[@]} -gt 0 ]] || { echo "No hay PDF en $PDF_DIR: genera el lote con generate_samples.py." >&2; exit 1; }

  echo "${bold}1. Subida de ${#pdfs[@]} documentos${reset}"
  ids=()
  for pdf in "${pdfs[@]}"; do
    name="$(basename "$pdf")"
    response="$(curl -sS -w '\n%{http_code}' -F "file=@$pdf;type=application/pdf" "$API_URL/documents")"
    code="${response##*$'\n'}"
    body="${response%$'\n'*}"
    if [[ "$code" == 200 || "$code" == 202 ]]; then
      id="$(jq -r '.id' <<<"$body")"
      ids+=("$id|$name")
      doc_ids="$(jq --arg k "$name" --arg v "$id" '.[$k] = $v' <<<"$doc_ids")"
      if [[ "$code" == 200 ]]; then note="ya existía"
      elif [[ "$(jq -r '.duplicate // false' <<<"$body")" == true ]]; then note="había fallado: encolado de nuevo"
      else note="encolado"; fi
      printf '   %-38s %s (%s)\n' "$name" "$id" "$note"
    else
      printf '   %-38s %srechazado al subir:%s %s\n' "$name" "$red" "$reset" "$(jq -r '.error.message // .' <<<"$body")"
    fi
  done

  echo
  echo "${bold}2. Procesamiento${reset} ${dim}(el primer documento tarda más: Docling descarga sus modelos)${reset}"
  for entry in "${ids[@]}"; do
    id="${entry%%|*}"; name="${entry#*|}"
    waited=0
    while :; do
      detail="$(curl -fsS "$API_URL/documents/$id")"
      status="$(jq -r '.status' <<<"$detail")"
      [[ "$status" == done || "$status" == failed ]] && break
      if (( waited >= WAIT_TIMEOUT )); then status="sin terminar tras ${WAIT_TIMEOUT}s"; break; fi
      sleep 3; waited=$((waited + 3))
    done
    if [[ "$status" == done ]]; then
      printf '   %-38s %sdone%s  tipo=%s páginas=%s campos=%s datos=%s\n' "$name" "$green" "$reset" \
        "$(jq -r '.document_type' <<<"$detail")" "$(jq -r '.page_count' <<<"$detail")" \
        "$(jq -r '[.fields[] | select(.status == "ok" or .status == "edited")] | length' <<<"$detail")" \
        "$(jq -r '.facts | length' <<<"$detail")"
    else
      printf '   %-38s %s%s%s %s\n' "$name" "$red" "$status" "$reset" "$(jq -r '.error.code // ""' <<<"$detail")"
    fi
  done
  echo
  echo "${dim}Espero ${SETTLE_SECONDS} s antes de preguntar, para que todo quede guardado.${reset}"
  sleep "$SETTLE_SECONDS"
  echo
}

# --- 3. Preguntas ----------------------------------------------------------------
filter='.[]'
if [[ -n "$only" ]]; then
  filter=".[] | select(.id as \$id | \"$only\" | split(\",\") | index(\$id))"
fi
total="$(jq "[$filter] | length" "$QUESTIONS")"
echo "${bold}3. Preguntas ($total), cada una sobre su documento${reset} ${dim}(${ASK_PAUSE}s entre preguntas por el límite de la API)${reset}"

ask() {  # $1 = document id, $2 = JSON body; prints the response body, retrying once on 429.
  local response code
  for attempt in 1 2; do
    response="$(curl -sS -w '\n%{http_code}' -H 'content-type: application/json' -d "$2" "$API_URL/documents/$1/ask")"
    code="${response##*$'\n'}"
    if [[ "$code" == 429 && "$attempt" == 1 ]]; then
      echo "   ${dim}límite de preguntas alcanzado: espero 60 s${reset}" >&2
      sleep 60
      continue
    fi
    printf '%s' "${response%$'\n'*}"
    return
  done
}

ok=0; n=0
while IFS= read -r item; do
  n=$((n + 1))
  qid="$(jq -r '.id' <<<"$item")"
  question="$(jq -r '.question' <<<"$item")"
  answerable="$(jq -r '.answerable' <<<"$item")"
  document="$(jq -r '.document' <<<"$item")"
  doc_id="$(jq -r --arg k "$document" '.[$k] // empty' <<<"$doc_ids")"
  if [[ -z "$doc_id" ]]; then
    echo; echo "${bold}[$qid]${reset} $question  [${red}SIN DOCUMENTO${reset}] ${dim}$document no está en $PDF_DIR${reset}"
    continue
  fi
  body="$(ask "$doc_id" "$(jq -n --arg q "$question" '{question: $q}')")"
  # A document that is not ready (it failed) gets a 409: that is "no answer" too.
  answered="$(jq -r '.answered // false' <<<"$body")"

  if [[ "$answered" == "$answerable" ]]; then ok=$((ok + 1)); mark="${green}OK${reset}"; else mark="${red}DISTINTO${reset}"; fi
  echo
  echo "${bold}[$qid]${reset} $question  [$mark]"
  echo "   documento: $document"
  [[ -n "$(jq -r '.purpose // empty' <<<"$item")" ]] && echo "   ${dim}caso: $(jq -r '.purpose' <<<"$item")${reset}"
  echo "   esperado:  $(jq -r '.expected' <<<"$item")"
  echo "   fuentes:   $(jq -r 'if (.sources | length) == 0 then "ninguna" else [.sources[] | "\(.document) pág. \(.page)"] | join(", ") end' <<<"$item")"
  echo "   respuesta: $(jq -r '
    if .answer then .answer
    elif .error.code == "document_not_ready" then "(el documento no está disponible: no terminó de procesarse o falló)"
    elif .error.code then "(error de la API: \(.error.code))"
    else "sin respuesta" end' <<<"$body")"
  citations="$(jq -r '[.citations[]? | "[\(.marker)] \(.filename)\(if .page then " pág. \(.page)" else "" end)"] | join(", ")' <<<"$body")"
  [[ -n "$citations" ]] && echo "   citas:     $citations"

  (( n < total )) && sleep "$ASK_PAUSE"
done < <(jq -c "$filter" "$QUESTIONS")

echo
echo "${bold}Resultado:${reset} $ok de $total preguntas se comportan como se esperaba (responder o decir que no hay información)."
echo "${dim}Las trazas de cada subida y pregunta están en Jaeger: http://localhost:16686 (servicios faro-api y faro-worker).${reset}"
