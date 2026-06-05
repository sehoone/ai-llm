#!/bin/bash
# MinIO 버킷 초기화 — Langfuse 가 필요로 하는 버킷 생성 (최초 1회)
# Usage: ./init-minio.sh <namespace>
set -euo pipefail

NAMESPACE=${1:-llm-platform}

echo "Waiting for MinIO to be ready..."
kubectl rollout status statefulset/minio -n "$NAMESPACE" --timeout=120s

# MinIO pod 에서 mc 클라이언트로 버킷 생성
MINIO_POD=$(kubectl get pod -n "$NAMESPACE" -l app.kubernetes.io/name=minio -o jsonpath='{.items[0].metadata.name}')

echo "Using pod: $MINIO_POD"

kubectl exec -n "$NAMESPACE" "$MINIO_POD" -- sh -c '
  mc alias set local http://localhost:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" --quiet
  for bucket in langfuse-events langfuse-media langfuse-exports; do
    if mc ls local/"$bucket" > /dev/null 2>&1; then
      echo "  bucket already exists: $bucket"
    else
      mc mb local/"$bucket" --quiet
      echo "  created: $bucket"
    fi
  done
'

echo "MinIO buckets initialized."
