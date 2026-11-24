#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# Smoke test: calls every product-app endpoint and checks the HTTP status code.
# Creates one product, updates it, deletes it again, and tests the error cases.
#
#   ./scripts/smoke-test.sh                                  # local Docker Compose
#   ./scripts/smoke-test.sh http://<alb-dns-name>            # on AWS, through the ALB
#
# Exit code 0 = every check passed, 1 = at least one check failed.
# -----------------------------------------------------------------------------
B=${1:-http://localhost:8080}
H='Content-Type: application/json'
FAILED=0

# call <label> <expected-status> <curl arguments...>
call() {
  local label=$1 expected=$2; shift 2
  local out code body result
  out=$(curl -s -w $'\n%{http_code}' "$@")
  code=${out##*$'\n'}
  body=${out%$'\n'*}
  if [ "$code" = "$expected" ]; then result=PASS; else result=FAIL; FAILED=1; fi
  printf '%-4s %-30s expected %s, got %s\n' "$result" "$label" "$expected" "$code"
  [ -n "$body" ] && printf '     %s\n' "$(echo "$body" | cut -c1-200)"
}

echo "Testing $B"
call "Health check"            200 "$B/actuator/health"
call "Swagger UI page"         200 -o /dev/null "$B/swagger-ui/index.html"
call "OpenAPI JSON"            200 -o /dev/null "$B/v3/api-docs"

# Create a product and remember its id for the next calls
CREATED=$(curl -s -w $'\n%{http_code}' -X POST "$B/api/products" -H "$H" \
  -d '{"name":"Smoke Test Mouse","description":"Created by smoke-test.sh","price":25.50,"quantity":10}')
CODE=${CREATED##*$'\n'}; BODY=${CREATED%$'\n'*}
ID=$(echo "$BODY" | grep -o '"id":[0-9]*' | cut -d: -f2)
if [ "$CODE" = "201" ] && [ -n "$ID" ]; then
  printf '%-4s %-30s expected 201, got %s (id=%s)
' PASS "Create product" "$CODE" "$ID"
else
  printf '%-4s %-30s expected 201, got %s
     %s
' FAIL "Create product" "$CODE" "$BODY"
  exit 1   # the remaining checks need the new product's id
fi

call "Get all products"        200 "$B/api/products"
call "Get product by id"       200 "$B/api/products/$ID"
call "Update product"          200 -X PUT "$B/api/products/$ID" -H "$H" -d '{"name":"Smoke Test Mouse v2","price":29.99,"quantity":8}'
call "Create invalid product"  400 -X POST "$B/api/products" -H "$H" -d '{"name":"","price":-1,"quantity":-5}'
call "Malformed JSON"          400 -X POST "$B/api/products" -H "$H" -d '{"name":'
call "Non-numeric id"          400 "$B/api/products/abc"
call "Delete product"          204 -X DELETE "$B/api/products/$ID"
call "Get deleted product"     404 "$B/api/products/$ID"

if [ $FAILED -eq 0 ]; then echo "ALL CHECKS PASSED"; else echo "SOME CHECKS FAILED"; fi
exit $FAILED
