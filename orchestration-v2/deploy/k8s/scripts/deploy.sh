#!/bin/bash
# K8s 전체 배포 스크립트
# Usage: ./deploy.sh [environment] [--skip-operators] [--registry <registry>] [--tag <tag>]
#
# environment: staging | production (default: staging)
# --skip-operators : CloudNativePG operator 설치 건너뜀 (이미 설치된 경우)
# --registry       : 이미지 레지스트리 주소 (default: your-registry.io/llm-platform)
# --tag            : 이미지 태그 (default: latest)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
K8S_DIR="$(dirname "$SCRIPT_DIR")"
ROOT_DIR="$(dirname "$(dirname "$K8S_DIR")")"

ENV=${1:-staging}
SKIP_OPERATORS=false
REGISTRY=${REGISTRY:-your-registry.io/llm-platform}
TAG=${TAG:-latest}

# ── 인수 파싱 ─────────────────────────────────────────────────────────────
shift || true
while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-operators) SKIP_OPERATORS=true ;;
    --registry) REGISTRY="$2"; shift ;;
    --tag)      TAG="$2";      shift ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
  shift
done

# ── 환경 검증 ─────────────────────────────────────────────────────────────
if [[ ! "$ENV" =~ ^(staging|production)$ ]]; then
  echo "Invalid environment. Must be: staging | production"
  echo "Usage: $0 [staging|production] [options]"
  exit 1
fi

NAMESPACE="llm-platform"
[[ "$ENV" == "staging" ]] && NAMESPACE="llm-platform-staging"

ENV_FILE="$ROOT_DIR/orchestrator-server/.env.$ENV"
if [ ! -f "$ENV_FILE" ]; then
  echo "Error: env file not found: $ENV_FILE"
  exit 1
fi

export REGISTRY TAG

# ── 사전 요구사항 확인 ────────────────────────────────────────────────────
for cmd in kubectl envsubst; do
  if ! command -v "$cmd" &>/dev/null; then
    echo "Error: '$cmd' is not installed"
    [[ "$cmd" == "envsubst" ]] && echo "  Install: brew install gettext  (macOS) | apt install gettext-base (Ubuntu)"
    exit 1
  fi
done

echo "========================================"
echo "  LLM Platform — K8s Deploy"
echo "  Environment : $ENV"
echo "  Namespace   : $NAMESPACE"
echo "  Registry    : $REGISTRY"
echo "  Tag         : $TAG"
echo "========================================"
echo ""

# ── 헬퍼 함수 ────────────────────────────────────────────────────────────
apply_dir() {
  local dir="$K8S_DIR/$1"
  echo "--> $1"
  # REGISTRY, TAG 변수 치환 후 적용
  find "$dir" -name "*.yaml" | sort | while read -r f; do
    envsubst '${REGISTRY} ${TAG}' < "$f" | kubectl apply -f - -n "$NAMESPACE" 2>/dev/null \
      || envsubst '${REGISTRY} ${TAG}' < "$f" | kubectl apply -f -
  done
}

wait_deploy() {
  kubectl rollout status deployment/"$1" -n "$NAMESPACE" --timeout=300s
}

wait_sts() {
  kubectl rollout status statefulset/"$1" -n "$NAMESPACE" --timeout=300s || true
}

# ── 1. CloudNativePG 오퍼레이터 설치 ─────────────────────────────────────
if [[ "$SKIP_OPERATORS" == "false" ]]; then
  echo "==> [1/9] Installing CloudNativePG operator..."
  kubectl apply --server-side -f \
    https://raw.githubusercontent.com/cloudnative-pg/cloudnative-pg/release-1.22/releases/cnpg-1.22.0.yaml
  kubectl wait --for=condition=Available deployment/cnpg-controller-manager \
    -n cnpg-system --timeout=120s
else
  echo "==> [1/9] Skipping operator install"
fi

# NGINX Ingress Controller 설치 (없는 경우)
if ! kubectl get deployment ingress-nginx-controller -n ingress-nginx &>/dev/null; then
  echo "     Installing NGINX Ingress Controller..."
  kubectl apply -f \
    https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.10.1/deploy/static/provider/cloud/deploy.yaml
fi

# ── 2. Namespace + ConfigMap ──────────────────────────────────────────────
echo ""
echo "==> [2/9] Namespace & Config..."
# namespace 이름 치환 (staging 의 경우)
sed "s/name: llm-platform/name: $NAMESPACE/g" "$K8S_DIR/namespace.yaml" | kubectl apply -f -
apply_dir "config"

# ── 3. Secrets ────────────────────────────────────────────────────────────
echo ""
echo "==> [3/9] Secrets..."
"$SCRIPT_DIR/create-secrets.sh" "$ENV_FILE" "$NAMESPACE"

# ── 4. Data Layer ─────────────────────────────────────────────────────────
echo ""
echo "==> [4/9] Data Layer (postgres, redis, clickhouse, minio)..."
apply_dir "data/postgres"
apply_dir "data/redis"
apply_dir "data/clickhouse"
apply_dir "data/minio"

echo "     Waiting for data layer (up to 5 min)..."
kubectl wait --for=condition=Ready cluster/postgres-ha -n "$NAMESPACE" --timeout=300s 2>/dev/null || \
  echo "     (CloudNativePG cluster may still be initializing)"
wait_sts redis
wait_sts clickhouse
wait_sts minio

# MinIO 버킷 초기화
"$SCRIPT_DIR/init-minio.sh" "$NAMESPACE"

# ── 5. Auth (Keycloak) ────────────────────────────────────────────────────
echo ""
echo "==> [5/9] Auth (Keycloak)..."

# realm-import.json → ConfigMap (idempotent)
REALM_FILE="$ROOT_DIR/deploy/keycloak/realm-import.json"
if [ -f "$REALM_FILE" ]; then
  kubectl create configmap keycloak-realm \
    --from-file=realm-export.json="$REALM_FILE" \
    -n "$NAMESPACE" \
    --dry-run=client -o yaml | kubectl apply -f -
fi

apply_dir "auth/keycloak"
echo "     Waiting for Keycloak (up to 5 min)..."
wait_sts keycloak

# ── 6. App Layer ──────────────────────────────────────────────────────────
echo ""
echo "==> [6/9] App Layer (platform, orchestrator, admin-front)..."
apply_dir "app/platform"
apply_dir "app/orchestrator"
apply_dir "app/admin-front"

echo "     Waiting for app pods..."
wait_deploy platform
wait_deploy orchestrator
wait_deploy admin-front

# ── 7. Langfuse ───────────────────────────────────────────────────────────
echo ""
echo "==> [7/9] Langfuse..."
apply_dir "langfuse"

# ── 8. Observability ──────────────────────────────────────────────────────
echo ""
echo "==> [8/9] Observability (Prometheus, Grafana, cAdvisor)..."

# Grafana dashboard ConfigMap — deploy/grafana 디렉터리에서 생성
GRAFANA_DASH_DIR="$ROOT_DIR/deploy/grafana"
if [ -d "$GRAFANA_DASH_DIR/dashboards" ]; then
  kubectl create configmap grafana-dashboards-provider \
    --from-file="$GRAFANA_DASH_DIR/dashboards/dashboards.yml" \
    -n "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -

  kubectl create configmap grafana-dashboards-json \
    --from-file="$GRAFANA_DASH_DIR/dashboards/json/" \
    -n "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -
fi

apply_dir "observability/prometheus"
apply_dir "observability/grafana"
apply_dir "observability/cadvisor"

# ── 9. Ingress ────────────────────────────────────────────────────────────
echo ""
echo "==> [9/9] Ingress..."
apply_dir "ingress"

# ── 완료 ─────────────────────────────────────────────────────────────────
echo ""
echo "========================================"
echo "  Deploy Complete!"
echo "========================================"
echo ""
kubectl get pods -n "$NAMESPACE"
echo ""

INGRESS_IP=$(kubectl get svc ingress-nginx-controller -n ingress-nginx \
  -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "<pending>")
echo "  Ingress IP  : $INGRESS_IP"
echo "  Langfuse UI : http://langfuse.your-domain.com  (초기 계정 생성 후 API Key 발급)"
echo "  Grafana     : http://grafana.$NAMESPACE.svc  (내부 접근)"
echo ""
echo "  ※ ingress.yaml 의 'your-domain.com' 을 실제 도메인으로 변경하세요."
