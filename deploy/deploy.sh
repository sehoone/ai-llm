#!/bin/bash
set -e

# Script to deploy all services (nginx + llm-admin + orchestration + db)

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENV=${1:-production}

# Validate environment
if [[ ! "$ENV" =~ ^(development|staging|production)$ ]]; then
  echo "Invalid environment. Must be one of: development, staging, production"
  echo "Usage: $0 [environment]"
  exit 1
fi

# Check orchestration env file
ORCH_ENV_FILE="$SCRIPT_DIR/../orchestration/.env.$ENV"
if [ ! -f "$ORCH_ENV_FILE" ]; then
  echo "Error: $ORCH_ENV_FILE not found."
  echo "Please create the env file before deploying."
  exit 1
fi

# Check admin env file
ADMIN_ENV_FILE="$SCRIPT_DIR/../admin/llm-admin/.env.production"
if [ ! -f "$ADMIN_ENV_FILE" ]; then
  echo "Error: $ADMIN_ENV_FILE not found."
  echo "Please create the env file before deploying."
  exit 1
fi

echo "Deploying all services for [$ENV] environment..."
echo "  - Frontend    : http://localhost:8060"
echo "  - API server  : http://localhost:8060/api"
echo "  - Langfuse    : http://localhost:8067"

cd "$SCRIPT_DIR"

APP_ENV=$ENV docker compose --env-file "$ORCH_ENV_FILE" up -d --build

echo ""
echo "All services started successfully."
echo "  - Langfuse 초기 설정: http://localhost:8067 에서 계정 생성 후"
echo "    API Keys 메뉴에서 Public/Secret key를 .env.production에 입력하세요."
echo "  docker compose -f $SCRIPT_DIR/docker-compose.yml ps"
