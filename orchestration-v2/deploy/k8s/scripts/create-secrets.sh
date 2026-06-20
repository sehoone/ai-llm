#!/bin/bash
# K8s Secret 생성 — .env 파일에서 값을 읽어 kubectl 로 적용
# Usage: ./create-secrets.sh <env-file-path> <namespace>
set -euo pipefail

ENV_FILE=${1:?"Usage: $0 <env-file-path> <namespace>"}
NAMESPACE=${2:?"Usage: $0 <env-file-path> <namespace>"}

if [ ! -f "$ENV_FILE" ]; then
  echo "Error: env file not found: $ENV_FILE"
  exit 1
fi

# .env 파일 파싱 (주석·빈 줄 제외)
load_env() {
  local file="$1"
  while IFS='=' read -r key value; do
    [[ "$key" =~ ^#.*$ || -z "$key" ]] && continue
    value="${value%%#*}"       # 인라인 주석 제거
    value="${value%"${value##*[![:space:]]}"}"  # 후미 공백 제거
    value="${value#\"}"        # 따옴표 제거
    value="${value%\"}"
    value="${value#\'}"
    value="${value%\'}"
    echo "$key=$value"
  done < "$file"
}

get_val() {
  local key="$1"
  load_env "$ENV_FILE" | grep "^${key}=" | head -1 | cut -d'=' -f2-
}

echo "Creating K8s Secrets in namespace [$NAMESPACE] from [$ENV_FILE]..."

# ── app-secrets ───────────────────────────────────────────────────────────
kubectl create secret generic app-secrets \
  --namespace="$NAMESPACE" \
  --from-literal=JWT_SECRET_KEY="$(get_val JWT_SECRET_KEY)" \
  --from-literal=POSTGRES_PASSWORD="$(get_val POSTGRES_PASSWORD)" \
  --from-literal=OPENAI_API_KEY="$(get_val OPENAI_API_KEY)" \
  --from-literal=ANTHROPIC_API_KEY="$(get_val ANTHROPIC_API_KEY)" \
  --from-literal=LANGFUSE_SECRET_KEY="$(get_val LANGFUSE_SECRET_KEY)" \
  --from-literal=LANGFUSE_PUBLIC_KEY="$(get_val LANGFUSE_PUBLIC_KEY)" \
  --from-literal=LANGFUSE_NEXTAUTH_SECRET="$(get_val LANGFUSE_NEXTAUTH_SECRET)" \
  --from-literal=LANGFUSE_SALT="$(get_val LANGFUSE_SALT)" \
  --from-literal=LANGFUSE_ENCRYPTION_KEY="$(get_val LANGFUSE_ENCRYPTION_KEY)" \
  --from-literal=CLICKHOUSE_PASSWORD="$(get_val CLICKHOUSE_PASSWORD)" \
  --from-literal=MINIO_ROOT_USER="$(get_val MINIO_ROOT_USER)" \
  --from-literal=MINIO_ROOT_PASSWORD="$(get_val MINIO_ROOT_PASSWORD)" \
  --from-literal=GRAFANA_ADMIN_PASSWORD="$(get_val GRAFANA_ADMIN_PASSWORD)" \
  --dry-run=client -o yaml | kubectl apply -f -

echo "  ✓ app-secrets"

# ── postgres-superuser (CloudNativePG 부트스트랩용) ────────────────────────
kubectl create secret generic postgres-superuser \
  --namespace="$NAMESPACE" \
  --from-literal=username="postgres" \
  --from-literal=password="$(get_val POSTGRES_PASSWORD)" \
  --type=kubernetes.io/basic-auth \
  --dry-run=client -o yaml | kubectl apply -f -

echo "  ✓ postgres-superuser"
echo "Secrets created successfully."
