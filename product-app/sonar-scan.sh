#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# sonar-scan.sh - same as sonar-scan.cmd, for Git Bash (and Linux/macOS).
#     ./sonar-scan.sh                -> mvn clean verify sonar:sonar
#     ./sonar-scan.sh sonar:sonar    -> any Maven arguments you pass instead
#
# Reads SONAR_TOKEN from the .env file next to this script. The token is
# exported only inside this script, never put on the Maven command line.
# -----------------------------------------------------------------------------
set -euo pipefail

# Work in the folder this script lives in (product-app)
cd "$(dirname "$0")"

# 1. Read the line SONAR_TOKEN=... from .env (strip Windows line ends and quotes)
token=""
if [ -f .env ]; then
  token=$(grep -E '^SONAR_TOKEN=' .env | tail -n 1 | cut -d= -f2- | tr -d "\r\"'" || true)
fi

# 2. A token from .env wins; an empty value keeps a SONAR_TOKEN set elsewhere
if [ -n "$token" ]; then
  export SONAR_TOKEN="$token"
fi
if [ -z "${SONAR_TOKEN:-}" ]; then
  echo "ERROR: SONAR_TOKEN is empty. Paste your token into $(pwd)/.env as SONAR_TOKEN=sqa_..." >&2
  exit 1
fi

# 3. Run Maven: the default goals, or the arguments you passed
if [ $# -eq 0 ]; then
  set -- clean verify sonar:sonar
fi
exec mvn "$@"
