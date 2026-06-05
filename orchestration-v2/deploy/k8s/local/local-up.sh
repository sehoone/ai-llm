#!/bin/bash
# 로컬 K8s 환경 기동 스크립트
#
# Usage:
#   ./local-up.sh [options]
#
# Options:
#   --skip-build           이미지 빌드 건너뜀 (이미 빌드된 경우)
#   --with-keycloak        Keycloak 함께 기동
#   --with-observability   Prometheus + Grafana + cAdvisor 함께 기동
#   --storageclass <name>  StorageClass 수동 지정 (기본: 자동 감지)
#
# 코어 서비스 (항상 기동): postgres, redis, clickhouse, minio, platform, orchestrator, admin-front, langfuse
# 선택 서비스:             keycloak (--with-keycloak), observability (--with-observability)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
K8S_DIR="$(dirname "$SCRIPT_DIR")"
ROOT_DIR="$(dirname "$(dirname "$K8S_DIR")")"
NAMESPACE="llm-platform"
PF_PID_FILE="/tmp/llm-k8s-pf.pids"

SKIP_BUILD=false
WITH_KEYCLOAK=false
WITH_OBSERVABILITY=false
STORAGECLASS=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-build)          SKIP_BUILD=true ;;
    --with-keycloak)       WITH_KEYCLOAK=true ;;
    --with-observability)  WITH_OBSERVABILITY=true ;;
    --storageclass)        STORAGECLASS="$2"; shift ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
  shift
done

# ── K8s 도구 감지 + StorageClass 자동 설정 ──────────────────────────────
detect_tool() {
  local ctx
  ctx=$(kubectl config current-context 2>/dev/null) || {
    echo "Error: kubectl context 가 설정되지 않았습니다."
    echo "  Docker Desktop: Settings → Kubernetes → Enable Kubernetes"
    echo "  minikube: minikube start"
    exit 1
  }
  case "$ctx" in
    docker-desktop)   echo "docker-desktop" ;;
    minikube)         echo "minikube" ;;
    rancher-desktop)  echo "rancher-desktop" ;;
    k3d-*)            echo "k3d" ;;
    *)                echo "other:$ctx" ;;
  esac
}

K8S_TOOL=$(detect_tool)

if [[ -z "$STORAGECLASS" ]]; then
  case "$K8S_TOOL" in
    docker-desktop)   STORAGECLASS="hostpath" ;;
    minikube)         STORAGECLASS="standard" ;;
    rancher-desktop)  STORAGECLASS="local-path" ;;
    k3d)              STORAGECLASS="local-path" ;;
    *)
      STORAGECLASS=$(kubectl get storageclass \
        -o jsonpath='{.items[?(@.metadata.annotations.storageclass\.kubernetes\.io/is-default-class=="true")].metadata.name}' \
        2>/dev/null | awk '{print $1}')
      if [[ -z "$STORAGECLASS" ]]; then
        echo "StorageClass 를 감지할 수 없습니다."
        echo "사용 가능한 StorageClass:"
        kubectl get storageclass
        echo ""
        echo "  ./local-up.sh --storageclass <name>"
        exit 1
      fi
      ;;
  esac
fi

echo "========================================"
echo "  LLM Platform — 로컬 K8s 기동"
echo "  도구         : $K8S_TOOL"
echo "  StorageClass : $STORAGECLASS"
echo "  Namespace    : $NAMESPACE"
echo "  Keycloak     : $WITH_KEYCLOAK"
echo "  Observability: $WITH_OBSERVABILITY"
echo "========================================"
echo ""

# ── .env 파일 (없으면 로컬 기본값) ──────────────────────────────────────
ENV_FILE="$ROOT_DIR/orchestrator-server/.env.development"
if [ ! -f "$ENV_FILE" ]; then
  echo "Note: .env.development 없음 → 기본 로컬값 사용 (실제 LLM API 호출 불가)"
  ENV_FILE="/tmp/llm-k8s-local.env"
  cat > "$ENV_FILE" << 'ENVEOF'
JWT_SECRET_KEY=local-dev-jwt-secret-key-minimum-32-characters-here
POSTGRES_PASSWORD=localdev
OPENAI_API_KEY=sk-local-placeholder
ANTHROPIC_API_KEY=sk-ant-local-placeholder
LANGFUSE_SECRET_KEY=sk-lf-local-placeholder-key
LANGFUSE_PUBLIC_KEY=pk-lf-local-placeholder-key
LANGFUSE_NEXTAUTH_SECRET=local-nextauth-secret-minimum-32-characters
LANGFUSE_SALT=local-salt-value-minimum-32-characters-here
LANGFUSE_ENCRYPTION_KEY=0000000000000000000000000000000000000000000000000000000000000000
CLICKHOUSE_PASSWORD=localdev
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin
KEYCLOAK_ADMIN_USER=admin
KEYCLOAK_ADMIN_PASSWORD=admin
GRAFANA_ADMIN_PASSWORD=admin
ENVEOF
fi

# ── 헬퍼 함수 ─────────────────────────────────────────────────────────────

# YAML 에 공통 치환을 적용한 뒤 kubectl apply
apply_patched() {
  local file="$1"
  sed \
    -e "s|storageClassName: fast-ssd|storageClassName: $STORAGECLASS|g" \
    -e "s|imagePullPolicy: Always|imagePullPolicy: IfNotPresent|g" \
    -e 's|\${REGISTRY}/platform-server:\${TAG}|platform-server:local|g' \
    -e 's|\${REGISTRY}/orchestrator-server:\${TAG}|orchestrator-server:local|g' \
    -e 's|\${REGISTRY}/admin-front:\${TAG}|admin-front:local|g' \
    "$file" | kubectl apply -f -
}

# local/overrides/ 아래 파일 적용
apply_override() {
  apply_patched "$SCRIPT_DIR/overrides/$1"
}

# ── [1] 이미지 빌드 ────────────────────────────────────────────────────────
echo "==> [1] 이미지 빌드..."
if [[ "$SKIP_BUILD" == "true" ]]; then
  echo "     건너뜀 (--skip-build)"
else
  build_image() {
    local name="$1" context="$2"
    shift 2
    echo "     $name 빌드 중..."
    if docker build -t "${name}:local" "$@" "$context" 2>&1 | tail -3; then
      echo "     ✓ ${name}:local"
    else
      echo "     ✗ ${name} 빌드 실패 — Dockerfile 경로 확인 필요"
    fi
  }

  build_image platform-server     "$ROOT_DIR/platform-server"
  build_image orchestrator-server "$ROOT_DIR/orchestrator-server"
  # admin-front: .env.production 이 있어야 NEXT_PUBLIC_* 빌드타임 주입 가능
  ADMIN_ENV_ARG=""
  [ -f "$ROOT_DIR/admin-front/.env.production" ] && ADMIN_ENV_ARG="--build-arg ENV_FILE=.env.production"
  build_image admin-front "$ROOT_DIR/admin-front" $ADMIN_ENV_ARG

  # minikube: 호스트 Docker 이미지를 minikube 내부로 로드
  if [[ "$K8S_TOOL" == "minikube" ]]; then
    echo "     minikube 이미지 로드 중..."
    minikube image load platform-server:local
    minikube image load orchestrator-server:local
    minikube image load admin-front:local
  fi
fi

# ── [2] CloudNativePG 오퍼레이터 ──────────────────────────────────────────
echo ""
echo "==> [2] CloudNativePG 오퍼레이터..."
if kubectl get deployment cnpg-controller-manager -n cnpg-system &>/dev/null 2>&1; then
  echo "     이미 설치됨"
else
  kubectl apply --server-side -f \
    https://raw.githubusercontent.com/cloudnative-pg/cloudnative-pg/release-1.22/releases/cnpg-1.22.0.yaml
  echo "     설치 완료 대기 중..."
  kubectl wait --for=condition=Available deployment/cnpg-controller-manager \
    -n cnpg-system --timeout=120s
fi

# ── [3] Namespace + ConfigMap ──────────────────────────────────────────────
echo ""
echo "==> [3] Namespace & Config..."
kubectl apply -f "$K8S_DIR/namespace.yaml"
apply_patched "$K8S_DIR/config/configmap.yaml"

# ── [4] Secrets ───────────────────────────────────────────────────────────
echo ""
echo "==> [4] Secrets..."
"$K8S_DIR/scripts/create-secrets.sh" "$ENV_FILE" "$NAMESPACE"

# ── [5] Data Layer ─────────────────────────────────────────────────────────
echo ""
echo "==> [5] Data Layer..."

# PostgreSQL — 1 instance
echo "     PostgreSQL..."
apply_override "postgres-local.yaml"

# Redis — quorum 1, replicas 1
echo "     Redis..."
apply_override "redis-local.yaml"   # ConfigMap (quorum 1)
sed \
  -e "s|storageClassName: fast-ssd|storageClassName: $STORAGECLASS|g" \
  -e "s|replicas: 3|replicas: 1|g" \
  "$K8S_DIR/data/redis/statefulset.yaml" | kubectl apply -f -
apply_patched "$K8S_DIR/data/redis/service.yaml"

# ClickHouse
echo "     ClickHouse..."
apply_patched "$K8S_DIR/data/clickhouse/configmap.yaml"
apply_patched "$K8S_DIR/data/clickhouse/statefulset.yaml"
apply_patched "$K8S_DIR/data/clickhouse/service.yaml"

# MinIO — standalone 1 pod (override)
echo "     MinIO..."
apply_override "minio-local.yaml"
apply_patched "$K8S_DIR/data/minio/service.yaml"

echo ""
echo "     데이터 레이어 준비 대기 (최대 5분)..."
kubectl wait --for=condition=Ready cluster/postgres-ha -n "$NAMESPACE" \
  --timeout=300s 2>/dev/null || echo "     (PostgreSQL 계속 초기화 중 — 앱 레이어 배포 후 완료될 수 있음)"
kubectl rollout status statefulset/redis       -n "$NAMESPACE" --timeout=180s || true
kubectl rollout status statefulset/clickhouse  -n "$NAMESPACE" --timeout=180s || true
kubectl rollout status statefulset/minio       -n "$NAMESPACE" --timeout=120s || true

"$K8S_DIR/scripts/init-minio.sh" "$NAMESPACE"

# ── [6] Keycloak (선택) ────────────────────────────────────────────────────
if [[ "$WITH_KEYCLOAK" == "true" ]]; then
  echo ""
  echo "==> [6] Keycloak..."
  REALM_FILE="$ROOT_DIR/deploy/keycloak/realm-import.json"
  if [ -f "$REALM_FILE" ]; then
    kubectl create configmap keycloak-realm \
      --from-file=realm-export.json="$REALM_FILE" \
      -n "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -
  fi
  apply_patched "$K8S_DIR/auth/keycloak/statefulset.yaml"
  apply_patched "$K8S_DIR/auth/keycloak/service.yaml"
  echo "     Keycloak 기동 대기 (최대 3분)..."
  kubectl rollout status statefulset/keycloak -n "$NAMESPACE" --timeout=180s || true
else
  echo "==> [6] Keycloak 건너뜀  (--with-keycloak 으로 활성화)"
fi

# ── [7] App Layer ──────────────────────────────────────────────────────────
echo ""
echo "==> [7] App Layer..."
for svc in platform orchestrator admin-front; do
  apply_patched "$K8S_DIR/app/$svc/deployment.yaml"
  apply_patched "$K8S_DIR/app/$svc/service.yaml"
done

echo "     앱 파드 준비 대기..."
kubectl rollout status deployment/platform     -n "$NAMESPACE" --timeout=300s
kubectl rollout status deployment/orchestrator -n "$NAMESPACE" --timeout=300s
kubectl rollout status deployment/admin-front  -n "$NAMESPACE" --timeout=300s

# ── [8] Langfuse ───────────────────────────────────────────────────────────
echo ""
echo "==> [8] Langfuse..."
apply_patched "$K8S_DIR/langfuse/deployment.yaml"
apply_patched "$K8S_DIR/langfuse/service.yaml"

# ── [9] Observability (선택) ──────────────────────────────────────────────
if [[ "$WITH_OBSERVABILITY" == "true" ]]; then
  echo ""
  echo "==> [9] Observability..."
  # Grafana dashboard ConfigMap
  GRAFANA_DIR="$ROOT_DIR/deploy/grafana"
  if [ -d "$GRAFANA_DIR/dashboards" ]; then
    kubectl create configmap grafana-dashboards-provider \
      --from-file="$GRAFANA_DIR/dashboards/dashboards.yml" \
      -n "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -
    kubectl create configmap grafana-dashboards-json \
      --from-file="$GRAFANA_DIR/dashboards/json/" \
      -n "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -
  fi
  for f in prometheus grafana cadvisor; do
    find "$K8S_DIR/observability/$f" -name "*.yaml" | sort | while read -r yaml; do
      apply_patched "$yaml"
    done
  done
else
  echo "==> [9] Observability 건너뜀  (--with-observability 으로 활성화)"
fi

# ── [10] Port-forwarding ───────────────────────────────────────────────────
echo ""
echo "==> [10] Port-forwarding 시작..."
rm -f "$PF_PID_FILE"

start_pf() {
  local svc="$1" local_port="$2" svc_port="$3"
  kubectl port-forward "svc/$svc" "${local_port}:${svc_port}" \
    -n "$NAMESPACE" >/dev/null 2>&1 &
  echo $! >> "$PF_PID_FILE"
}

start_pf admin-front  3000 3000
start_pf platform     8080 8080
start_pf orchestrator 8000 8000
start_pf langfuse     8067 3000
[[ "$WITH_KEYCLOAK" == "true" ]]       && start_pf keycloak   8068 8080
[[ "$WITH_OBSERVABILITY" == "true" ]]  && start_pf grafana    8064 3000
[[ "$WITH_OBSERVABILITY" == "true" ]]  && start_pf prometheus 8063 9090

echo ""
echo "========================================"
echo "  기동 완료!"
echo "========================================"
echo ""
echo "  Frontend      http://localhost:3000"
echo "  Platform API  http://localhost:8080/swagger-ui/index.html"
echo "  Orchestrator  http://localhost:8000/docs"
echo "  Langfuse      http://localhost:8067"
[[ "$WITH_KEYCLOAK" == "true" ]]       && echo "  Keycloak      http://localhost:8068"
[[ "$WITH_OBSERVABILITY" == "true" ]]  && echo "  Grafana       http://localhost:8064"
[[ "$WITH_OBSERVABILITY" == "true" ]]  && echo "  Prometheus    http://localhost:8063"
echo ""
echo "  파드 상태:  kubectl get pods -n $NAMESPACE"
echo "  로그:       ../scripts/logs.sh <service>"
echo "  중지:       ./local-down.sh"
echo "  완전 삭제:  ./local-down.sh --with-data"
