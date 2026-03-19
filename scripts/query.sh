#!/usr/bin/env bash
# =============================================================================
# Run a SPARQL query against the Fuseki endpoint
# =============================================================================
#
# Usage:
#   ./scripts/query.sh tests/sparql/05-party-size.rq
#   ./scripts/query.sh tests/sparql/07-graph-stats.rq table
#   ./scripts/query.sh "SELECT (COUNT(*) AS ?c) WHERE { ?s ?p ?o }"
# =============================================================================

set -euo pipefail

FUSEKI_URL="${FUSEKI_URL:-http://localhost:3030}"
DATASET="riksdag"
INPUT="$1"
FORMAT="${2:-table}"

# Determine if input is a file or inline query
if [ -f "$INPUT" ]; then
    QUERY=$(cat "$INPUT")
    echo "Query: $INPUT"
else
    QUERY="$INPUT"
fi

echo "---"

if [ "$FORMAT" = "table" ]; then
    curl -s "${FUSEKI_URL}/${DATASET}/query" \
        -H "Accept: text/tab-separated-values" \
        --data-urlencode "query=${QUERY}" | column -t -s $'\t'
elif [ "$FORMAT" = "json" ]; then
    curl -s "${FUSEKI_URL}/${DATASET}/query" \
        -H "Accept: application/sparql-results+json" \
        --data-urlencode "query=${QUERY}" | python3 -m json.tool
else
    curl -s "${FUSEKI_URL}/${DATASET}/query" \
        -H "Accept: text/tab-separated-values" \
        --data-urlencode "query=${QUERY}"
fi
