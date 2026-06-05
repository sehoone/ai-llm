#!/bin/bash
# K8s 서비스 중지 스크립트
# Usage: ./stop.sh [environment] [--delete] [--with-data]
#
# environment : staging | production (default: staging)
# --delete    : 리소스 삭제 (scale down 만 하는 기본 동작 대신)
# --with-data : --delete 와 함께 사용 시 PVC(볼륨) 까지 삭제 (데이터 손실 주의)
set -euo pipefail

ENV=${1:-staging}
DELETE=false
WITH_DATA=false

shift || true
while [[ $# -gt 0 ]]; do
  case "$1" in
    --delete)    DELETE=true ;;
    --with-data) WITH_DATA=true ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
  shift
done

if [[ ! "$ENV" =~ ^(staging|production)$ ]]; then
  echo "Invalid environment. Must be: staging | production"
  exit 1
fi

NAMESPACE="llm-platform"
[[ "$ENV" == "staging" ]] && NAMESPACE="llm-platform-staging"

echo "========================================"
echo "  LLM Platform — K8s Stop"
echo "  Environment : $ENV"
echo "  Namespace   : $NAMESPACE"
echo "  Delete      : $DELETE"
echo "  With Data   : $WITH_DATA"
echo "========================================"

if [[ "$DELETE" == "false" ]]; then
  # ── Graceful scale down (데이터 보존) ────────────────────────────────
  echo ""
  echo "Scaling down all Deployments and StatefulSets to 0..."
  kubectl scale deployment --all -n "$NAMESPACE" --replicas=0
  kubectl scale statefulset --all -n "$NAMESPACE" --replicas=0
  echo "All services scaled to 0. Data volumes preserved."
  echo ""
  echo "To restart: kubectl scale deployment --all -n $NAMESPACE --replicas=<n>"

else
  # ── Delete resources ──────────────────────────────────────────────────
  if [[ "$WITH_DATA" == "true" ]]; then
    echo ""
    echo "WARNING: This will DELETE ALL resources including PVCs (data)."
    read -r -p "Type 'yes' to confirm: " confirm
    if [[ "$confirm" != "yes" ]]; then
      echo "Aborted."
      exit 0
    fi
    kubectl delete namespace "$NAMESPACE" --wait=true
    echo "Namespace $NAMESPACE deleted (including all PVCs)."
  else
    echo ""
    echo "Deleting all resources (PVCs preserved)..."
    # Deployment, StatefulSet, Service, Ingress, HPA, PDB 삭제 (PVC 제외)
    for resource in deployment statefulset service ingress hpa pdb configmap; do
      kubectl delete "$resource" --all -n "$NAMESPACE" 2>/dev/null || true
    done
    # CloudNativePG Cluster 삭제
    kubectl delete cluster --all -n "$NAMESPACE" 2>/dev/null || true
    echo "Resources deleted. PVCs preserved:"
    kubectl get pvc -n "$NAMESPACE" 2>/dev/null || true
  fi
fi
