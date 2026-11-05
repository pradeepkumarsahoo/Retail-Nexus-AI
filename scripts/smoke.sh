#!/usr/bin/env bash
# Author: Pradeep Sahoo — Retail Nexus AI
# Hit a few endpoints to confirm the stack is up.
set -euo pipefail
HOST="${HOST:-http://localhost:8000}"

echo "> health"
curl -sS "$HOST/api/v1/health" | head -c 400; echo

echo "> login"
TOKEN=$(curl -sS -X POST "$HOST/api/v1/auth/token" -d "username=demo-admin&password=demo" | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
AUTH="Authorization: Bearer $TOKEN"

echo "> dashboard"
curl -sS -H "$AUTH" "$HOST/api/v1/dashboard/summary" | head -c 400; echo

echo "> detect"
curl -sS -X POST -H "$AUTH" "$HOST/api/v1/exceptions/detect" | head -c 400; echo

echo "> list exceptions"
curl -sS -H "$AUTH" "$HOST/api/v1/exceptions?limit=3" | head -c 400; echo
