#!/bin/bash
set -e

# Script to deploy all services (nginx + admin-front + orchestrator-server + db + monitoring)

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENV=${1:-production}

# Validate environment
if [[ ! "$ENV" =~ ^(development|staging|production)$ ]]; then
  echo "Invalid environment. Must be one of: development, staging, production"
  echo "Usage: $0 [environment]"
  exit 1
fi

# Check orchestrator-server env file
ORCH_ENV_FILE="$SCRIPT_DIR/../orchestrator-server/.env.$ENV"
if [ ! -f "$ORCH_ENV_FILE" ]; then
  echo "Error: $ORCH_ENV_FILE not found."
  echo "Please create the env file before deploying."
  exit 1
fi

# Check admin-front env file
ADMIN_ENV_FILE="$SCRIPT_DIR/../admin-front/.env.production"
if [ ! -f "$ADMIN_ENV_FILE" ]; then
  echo "Error: $ADMIN_ENV_FILE not found."
  echo "Please create the env file before deploying."
  exit 1
fi

# platform-server는 orchestrator-server env 파일을 공유 (JWT_SECRET_KEY, POSTGRES_* 동일)
# 별도 env 파일이 있으면 우선 사용
PLATFORM_ENV_FILE="$SCRIPT_DIR/../platform-server/.env.$ENV"
if [ ! -f "$PLATFORM_ENV_FILE" ]; then
  echo "Note: $PLATFORM_ENV_FILE not found — platform-server will use orchestrator-server env file."
fi

echo "Deploying all services for [$ENV] environment..."
echo "  - Frontend      : http://localhost:8060"
echo "  - Platform API  : http://localhost:8060/api/v1/auth|users|api-keys|llm-resources"
echo "  - Orchestrator  : http://localhost:8060/api (LLM/RAG/Workflow)"
echo "  - Langfuse      : http://localhost:8067"
echo "  - Prometheus    : http://localhost:8063"
echo "  - Grafana       : http://localhost:8064"
echo "  - cAdvisor      : http://localhost:8065"

cd "$SCRIPT_DIR"

APP_ENV=$ENV docker compose --env-file "$ORCH_ENV_FILE" up -d --build

echo ""
echo "All services started successfully."
echo "  - Langfuse 초기 설정: http://localhost:8067 에서 계정 생성 후"
echo "    API Keys 메뉴에서 Public/Secret key를 .env.$ENV에 입력하세요."
echo "  - Grafana 초기 로그인: http://localhost:8064 (admin / \${GRAFANA_ADMIN_PASSWORD:-admin})"
echo "    LLM Inference Latency 대시보드가 자동으로 프로비저닝됩니다."
echo "  docker compose -f $SCRIPT_DIR/docker-compose.yml ps"
