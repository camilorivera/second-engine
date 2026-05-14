#!/usr/bin/env bash
set -e

echo "Running Trivy security scan..."

# Scan filesystem for secrets and misconfig
docker run --rm -v "$(pwd):/scan" \
  aquasec/trivy:latest fs /scan \
  --scanners secret,misconfig \
  --exit-code 1 \
  --severity HIGH,CRITICAL \
  --quiet \
  2>&1 || { echo "Trivy found HIGH/CRITICAL issues. Commit blocked."; exit 1; }

# Scan Python dependencies
docker run --rm -v "$(pwd)/worker:/scan" \
  aquasec/trivy:latest fs /scan \
  --exit-code 1 \
  --severity HIGH,CRITICAL \
  --quiet \
  2>&1 || { echo "Trivy found vulnerable Python dependencies. Commit blocked."; exit 1; }

echo "Trivy scan passed."
