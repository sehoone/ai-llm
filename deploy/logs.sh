#!/bin/bash

# Script to view logs for deployed services
# Usage: ./logs.sh [service] [environment]
#   service: all | nginx | llm-admin | app | db (default: all)
#   environment: development | staging | production (default: production)

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVICE=${1:-all}
ENV=${2:-production}

VALID_SERVICES="all nginx llm-admin app db"
if ! echo "$VALID_SERVICES" | grep -qw "$SERVICE"; then
  echo "Invalid service. Must be one of: $VALID_SERVICES"
  echo "Usage: $0 [service] [environment]"
  exit 1
fi

if [[ ! "$ENV" =~ ^(development|staging|production)$ ]]; then
  echo "Invalid environment. Must be one of: development, staging, production"
  echo "Usage: $0 [service] [environment]"
  exit 1
fi

ORCH_ENV_FILE="$SCRIPT_DIR/../orchestration/.env.$ENV"

cd "$SCRIPT_DIR"

if [ "$SERVICE" = "all" ]; then
  echo "Following logs for all services (Ctrl+C to exit)..."
  if [ -f "$ORCH_ENV_FILE" ]; then
    APP_ENV=$ENV docker compose --env-file "$ORCH_ENV_FILE" logs -f
  else
    APP_ENV=$ENV docker compose logs -f
  fi
else
  echo "Following logs for [$SERVICE] (Ctrl+C to exit)..."
  if [ -f "$ORCH_ENV_FILE" ]; then
    APP_ENV=$ENV docker compose --env-file "$ORCH_ENV_FILE" logs -f "$SERVICE"
  else
    APP_ENV=$ENV docker compose logs -f "$SERVICE"
  fi
fi
