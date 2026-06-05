#!/bin/bash
# K8s 서비스 로그 조회
# Usage: ./logs.sh [service] [environment]
#
# service     : all | platform | orchestrator | admin-front | postgres | redis
#               clickhouse | minio | keycloak | langfuse | prometheus | grafana | cadvisor
# environment : staging | production (default: staging)
set -euo pipefail

SERVICE=${1:-all}
ENV=${2:-staging}

VALID_SERVICES="all platform orchestrator admin-front postgres redis clickhouse minio keycloak langfuse prometheus grafana cadvisor"
if ! echo "$VALID_SERVICES" | grep -qw "$SERVICE"; then
  echo "Invalid service. Must be one of: $VALID_SERVICES"
  echo "Usage: $0 [service] [environment]"
  exit 1
fi

if [[ ! "$ENV" =~ ^(staging|production)$ ]]; then
  echo "Invalid environment. Must be: staging | production"
  exit 1
fi

NAMESPACE="llm-platform"
[[ "$ENV" == "staging" ]] && NAMESPACE="llm-platform-staging"

# service → label selector 매핑
label_selector() {
  case "$1" in
    platform)      echo "app.kubernetes.io/name=platform" ;;
    orchestrator)  echo "app.kubernetes.io/name=orchestrator" ;;
    admin-front)   echo "app.kubernetes.io/name=admin-front" ;;
    postgres)      echo "cnpg.io/cluster=postgres-ha" ;;
    redis)         echo "app.kubernetes.io/name=redis" ;;
    clickhouse)    echo "app.kubernetes.io/name=clickhouse" ;;
    minio)         echo "app.kubernetes.io/name=minio" ;;
    keycloak)      echo "app.kubernetes.io/name=keycloak" ;;
    langfuse)      echo "app.kubernetes.io/name=langfuse" ;;
    prometheus)    echo "app.kubernetes.io/name=prometheus" ;;
    grafana)       echo "app.kubernetes.io/name=grafana" ;;
    cadvisor)      echo "app.kubernetes.io/name=cadvisor" ;;
  esac
}

if [[ "$SERVICE" == "all" ]]; then
  echo "Following logs for all services in [$NAMESPACE] (Ctrl+C to exit)..."
  kubectl logs -f -n "$NAMESPACE" \
    --selector="app.kubernetes.io/part-of=llm-platform" \
    --max-log-requests=20 \
    --prefix=true
else
  SELECTOR=$(label_selector "$SERVICE")
  echo "Following logs for [$SERVICE] in [$NAMESPACE] (Ctrl+C to exit)..."
  kubectl logs -f -n "$NAMESPACE" \
    --selector="$SELECTOR" \
    --max-log-requests=5 \
    --prefix=true
fi
