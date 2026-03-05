#!/bin/bash
set -e

# Script to stop all deployed services

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENV=${1:-production}

# Validate environment
if [[ ! "$ENV" =~ ^(development|staging|production)$ ]]; then
  echo "Invalid environment. Must be one of: development, staging, production"
  echo "Usage: $0 [environment]"
  exit 1
fi

ORCH_ENV_FILE="$SCRIPT_DIR/../orchestration/.env.$ENV"

echo "Stopping all services..."

cd "$SCRIPT_DIR"

if [ -f "$ORCH_ENV_FILE" ]; then
  APP_ENV=$ENV docker compose --env-file "$ORCH_ENV_FILE" down
else
  APP_ENV=$ENV docker compose down
fi

echo "All services stopped."
