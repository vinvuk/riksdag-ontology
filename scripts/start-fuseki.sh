#!/usr/bin/env bash
# =============================================================================
# Start Fuseki with the Riksdag dataset configuration
# =============================================================================
#
# Usage:
#   ./scripts/start-fuseki.sh          # Start on default port 3030
#   PORT=3040 ./scripts/start-fuseki.sh # Start on custom port
# =============================================================================

set -euo pipefail

cd "$(dirname "$0")/.."

JAVA="/opt/homebrew/opt/openjdk@21/bin/java"
FUSEKI_JAR="tools/fuseki/fuseki-server.jar"
PORT="${PORT:-3030}"

if [ ! -f "$FUSEKI_JAR" ]; then
    echo "Fuseki not found at $FUSEKI_JAR"
    echo "Run 'make setup' to download it."
    exit 1
fi

if ! "$JAVA" -version &>/dev/null; then
    echo "Java not found. Install with: brew install openjdk@21"
    exit 1
fi

# Create database directory
mkdir -p run/databases/riksdag

echo "Starting Fuseki on port ${PORT}..."
echo "  SPARQL endpoint: http://localhost:${PORT}/riksdag/query"
echo "  Web UI:          http://localhost:${PORT}/"
echo ""

exec "$JAVA" -jar "$FUSEKI_JAR" \
    --config=config/fuseki-config.ttl \
    --port="$PORT"
