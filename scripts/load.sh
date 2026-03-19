#!/usr/bin/env bash
# =============================================================================
# Load ontology, vocabularies, and data into Fuseki
# =============================================================================
#
# Usage:
#   ./scripts/load.sh                        # Load ontology + sample data
#   ./scripts/load.sh data/riksdag-full.ttl  # Load ontology + custom data file
#
# Prerequisites:
#   - Fuseki running at http://localhost:3030
#   - Dataset "riksdag" created (via fuseki-config.ttl or UI)
# =============================================================================

set -euo pipefail

FUSEKI_URL="${FUSEKI_URL:-http://localhost:3030}"
DATASET="riksdag"
DATA_FILE="${1:-data/riksdag-sample.ttl}"

echo "Loading into Fuseki at ${FUSEKI_URL}/${DATASET}"
echo "================================================"

# 1. Load ontology modules into named graph
echo ""
echo "Loading ontology modules..."
for f in ontology/*.ttl; do
    echo "  ← $f"
    curl -s -X POST "${FUSEKI_URL}/${DATASET}/data?graph=https://ontology.riksdagen.se/def/" \
        -H "Content-Type: text/turtle" \
        --data-binary "@${f}"
done

# 2. Load vocabularies into named graph
echo ""
echo "Loading SKOS vocabularies..."
for f in vocabularies/*.ttl; do
    echo "  ← $f"
    curl -s -X POST "${FUSEKI_URL}/${DATASET}/data?graph=https://ontology.riksdagen.se/vocab/" \
        -H "Content-Type: text/turtle" \
        --data-binary "@${f}"
done

# 3. Load SHACL shapes into named graph
echo ""
echo "Loading SHACL shapes..."
for f in shapes/*.ttl; do
    echo "  ← $f"
    curl -s -X POST "${FUSEKI_URL}/${DATASET}/data?graph=https://ontology.riksdagen.se/shapes/" \
        -H "Content-Type: text/turtle" \
        --data-binary "@${f}"
done

# 4. Load instance data into named graph (union default graph makes it queryable)
if [ -f "$DATA_FILE" ]; then
    echo ""
    echo "Loading instance data: ${DATA_FILE} ($(du -h "$DATA_FILE" | cut -f1))"
    curl -s -X PUT "${FUSEKI_URL}/${DATASET}/data?graph=https://data.riksdagen.se/" \
        -H "Content-Type: text/turtle" \
        --data-binary "@${DATA_FILE}"
    echo "  ✓ Done"
else
    echo ""
    echo "Warning: Data file not found: ${DATA_FILE}"
    echo "Run the pipeline first: python -m pipeline.cli run --session 2024/25"
fi

# 5. Verify
echo ""
echo "Verifying..."
COUNT=$(curl -s "${FUSEKI_URL}/${DATASET}/query" \
    -H "Accept: application/sparql-results+json" \
    --data-urlencode "query=SELECT (COUNT(*) AS ?count) WHERE { ?s ?p ?o }" \
    | python3 -c "import sys,json; print(json.load(sys.stdin)['results']['bindings'][0]['count']['value'])" 2>/dev/null || echo "?")
echo "Total triples in store: ${COUNT}"
echo ""
echo "SPARQL endpoint: ${FUSEKI_URL}/${DATASET}/query"
echo "Fuseki UI:       ${FUSEKI_URL}/"
