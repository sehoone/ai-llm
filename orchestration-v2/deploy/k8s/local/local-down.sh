#!/bin/bash
# 로컬 K8s 환경 종료 스크립트
#
# Usage:
#   ./local-down.sh            # 스케일 0 (볼륨 보존, 재기동 가능)
#   ./local-down.sh --with-data  # namespace 전체 삭제 (볼륨 포함, 초기화)
set -euo pipefail

NAMESPACE="llm-platform"
PF_PID_FILE="/tmp/llm-k8s-pf.pids"
WITH_DATA=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --with-data) WITH_DATA=true ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
  shift
done

# ── Port-forwarding 종료 ─────────────────────────────────────────────────
if [ -f "$PF_PID_FILE" ]; then
  echo "Port-forwarding 종료..."
  while read -r pid; do
    kill "$pid" 2>/dev/null && echo "  killed PID $pid" || true
  done < "$PF_PID_FILE"
  rm -f "$PF_PID_FILE"
  echo "  완료"
else
  echo "Port-forwarding PID 파일 없음 (이미 종료됨)"
fi

echo ""

if [[ "$WITH_DATA" == "true" ]]; then
  # ── 전체 삭제 (볼륨 포함) ───────────────────────────────────────────
  echo "주의: namespace '$NAMESPACE' 와 모든 PVC(데이터)를 삭제합니다."
  read -r -p "계속하려면 'yes' 입력: " confirm
  if [[ "$confirm" != "yes" ]]; then
    echo "취소됨."
    exit 0
  fi
  kubectl delete namespace "$NAMESPACE" --wait=true 2>/dev/null && \
    echo "Namespace '$NAMESPACE' 삭제 완료." || \
    echo "Namespace 가 이미 없거나 삭제 중입니다."
else
  # ── 스케일 0 (볼륨 보존) ────────────────────────────────────────────
  echo "모든 Deployment / StatefulSet 을 0 으로 스케일 다운 (볼륨 보존)..."
  kubectl scale deployment  --all -n "$NAMESPACE" --replicas=0 2>/dev/null || true
  kubectl scale statefulset --all -n "$NAMESPACE" --replicas=0 2>/dev/null || true
  echo ""
  echo "완료. 볼륨(PVC)은 그대로 남아 있습니다."
  echo ""
  echo "  재기동:     ./local-up.sh --skip-build"
  echo "  완전 삭제:  ./local-down.sh --with-data"
fi
