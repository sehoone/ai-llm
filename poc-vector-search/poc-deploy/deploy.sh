#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ── 색상 출력 ────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()    { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*" >&2; exit 1; }

# ── .env 확인 ────────────────────────────────────────────────
if [[ ! -f .env ]]; then
  warn ".env 파일이 없습니다. .env.example 을 복사합니다."
  cp .env.example .env
  error "poc-deploy/.env 파일에서 AZURE_OPENAI_* 등 필수 값을 채운 뒤 다시 실행하세요."
fi

# Azure OpenAI 필수 값 체크
# shellcheck source=.env
source .env
if [[ -z "${AZURE_OPENAI_API_KEY:-}" || "$AZURE_OPENAI_API_KEY" == your-azure-openai-api-key ]]; then
  error "AZURE_OPENAI_API_KEY 가 설정되지 않았습니다. poc-deploy/.env 파일을 확인하세요."
fi
if [[ -z "${AZURE_OPENAI_ENDPOINT:-}" || "$AZURE_OPENAI_ENDPOINT" == https://your-resource.openai.azure.com ]]; then
  error "AZURE_OPENAI_ENDPOINT 가 설정되지 않았습니다. poc-deploy/.env 파일을 확인하세요."
fi

# ── 커맨드 파싱 ──────────────────────────────────────────────
CMD="${1:-up}"

case "$CMD" in
  up)
    info "전체 스택 빌드 & 시작..."
    docker compose --env-file .env up -d --build
    info ""
    info "서비스가 시작되었습니다."
    info "  접속 URL : http://localhost:${NGINX_PORT:-80}"
    info "  로그인   : admin@poc.com / admin1234"
    ;;
  down)
    info "스택 종료 (볼륨 유지)..."
    docker compose down
    ;;
  restart)
    info "스택 재시작..."
    docker compose down
    docker compose --env-file .env up -d --build
    ;;
  logs)
    SERVICE="${2:-}"
    if [[ -n "$SERVICE" ]]; then
      docker compose logs -f "$SERVICE"
    else
      docker compose logs -f
    fi
    ;;
  init-db)
    info "init.sql 을 실행합니다..."
    docker exec -i poc-postgres psql \
      -U "${POSTGRES_USER:-postgres}" \
      -d "${POSTGRES_DB:-poc_vector}" \
      < init.sql
    info "DB 초기화 완료."
    ;;
  ps)
    docker compose ps
    ;;
  clean)
    warn "볼륨 포함 완전 삭제합니다. 계속하시겠습니까? (y/N)"
    read -r answer
    if [[ "$answer" =~ ^[Yy]$ ]]; then
      docker compose down -v
      info "삭제 완료."
    else
      info "취소했습니다."
    fi
    ;;
  *)
    echo "사용법: $0 {up|down|restart|logs [service]|ps|init-db|clean}"
    exit 1
    ;;
esac
