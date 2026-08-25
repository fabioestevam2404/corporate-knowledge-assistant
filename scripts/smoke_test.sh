#!/usr/bin/env bash
# Real smoke test against a live stack (local docker compose, staging, or
# production) — /health -> /health/ready -> /auth/login -> /retrieve -> /ask,
# in the order the roadmap's own smoke-test gate expects. Exits non-zero on
# the first failure, printing the actual HTTP status/body so a CI log or a
# terminal shows exactly what failed.
#
# Usage:
#   BASE_URL=http://127.0.0.1:8010 SMOKE_USERNAME=... SMOKE_PASSWORD=... ./scripts/smoke_test.sh
#
# SMOKE_USERNAME/SMOKE_PASSWORD must be real credentials for an already-seeded
# user (see scripts/seed_users.py) — never hardcoded here.

set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8010}"
SMOKE_USERNAME="${SMOKE_USERNAME:?Set SMOKE_USERNAME to a real, already-seeded user}"
SMOKE_PASSWORD="${SMOKE_PASSWORD:?Set SMOKE_PASSWORD to the real password for that user}"

fail() {
  echo "SMOKE TEST FAILED: $1" >&2
  exit 1
}

# Usage: check <name> <method> <path> [expect_field] -- <extra curl args...>
# Prints the response body to stdout on success (nothing else on stdout).
check() {
  local name="$1" method="$2" path="$3" expect_field="$4"
  shift 4
  [[ "${1:-}" == "--" ]] && shift
  local response status body
  response=$(curl -sS -m 30 -w '\n%{http_code}' -X "$method" "$BASE_URL$path" "$@") \
    || fail "$name: curl itself failed"
  status=$(echo "$response" | tail -n1)
  body=$(echo "$response" | sed '$d')

  if [[ "$status" != "200" ]]; then
    fail "$name: expected HTTP 200, got $status. Body: $body"
  fi
  if [[ -n "$expect_field" ]] && ! echo "$body" | grep -q "\"$expect_field\""; then
    fail "$name: response missing expected field '$expect_field'. Body: $body"
  fi
  echo "OK  $name ($status)" >&2
  echo "$body"
}

echo "Smoke test against $BASE_URL" >&2
echo "---" >&2

check "GET /health" GET "/health" "status" >/dev/null
check "GET /health/ready" GET "/health/ready" "status" >/dev/null

login_body=$(check "POST /auth/login" POST "/auth/login" "access_token" -- \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"$SMOKE_USERNAME\",\"password\":\"$SMOKE_PASSWORD\"}")
TOKEN=$(echo "$login_body" | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
[[ -n "$TOKEN" ]] || fail "POST /auth/login: could not extract access_token"

check "POST /retrieve" POST "/retrieve" "results" -- \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"remote work policy","top_k":3}' >/dev/null

check "POST /ask" POST "/ask" "answer" -- \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"How many days per week can employees work remotely?"}' >/dev/null

echo "---" >&2
echo "Smoke test passed: all endpoints responded correctly." >&2
