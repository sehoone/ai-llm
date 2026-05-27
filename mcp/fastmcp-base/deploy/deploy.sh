#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

TARGET="prd"
MODE="https"
MONITORING=false

usage() {
    cat <<EOF
사용법: $(basename "$0") [prd|stg] [http|https] [--monitoring] [-h]

  prd         프로덕션 배포 (.env.prd, docker-compose.prd.yml) [기본값]
  stg      스테이징 배포 (.env.stg, docker-compose.stg.yml)

  http         HTTP 모드 배포 (포트 80, SSL 불필요)
  https        HTTPS 모드 배포 (포트 443, 인증서 필요) [기본값]
  --monitoring 모니터링 스택 포함 (Loki + Promtail + Grafana)
  -h, --help   도움말 표시

예시:
  $(basename "$0") prd https
  $(basename "$0") prd https --monitoring
  $(basename "$0") stg http
  $(basename "$0") stg https --monitoring
EOF
    exit 1
}

for arg in "$@"; do
    case "$arg" in
        prd|stg) TARGET="$arg" ;;
        http|https) MODE="$arg" ;;
        --monitoring) MONITORING=true ;;
        -h|--help) usage ;;
        *) echo "알 수 없는 옵션: $arg"; usage ;;
    esac
done

# 환경별 설정
if [ "$TARGET" = "stg" ]; then
    ENV_FILE=".env.stg"
    COMPOSE_OVERRIDE="docker-compose.stg.yml"
else
    ENV_FILE=".env.prd"
    COMPOSE_OVERRIDE="docker-compose.prd.yml"
fi

# env 파일 확인
if [ ! -f "$ENV_FILE" ]; then
    echo "오류: deploy/$ENV_FILE 파일이 없습니다."
    echo "  cp .env.example $ENV_FILE 후 필수 항목을 수정하세요."
    exit 1
fi

# HTTPS 모드: SSL 인증서 존재 확인
if [ "$MODE" = "https" ]; then
    if [ ! -f ssl/cert.pem ] || [ ! -f ssl/key.pem ]; then
        cat <<EOF

HTTP 모드로 배포하려면: $(basename "$0") $TARGET http
EOF
        exit 1
    fi
fi

# --env-file: compose 파일 내 ${VAR} 치환에 사용 (DOMAIN, POSTGRES_PASSWORD 등)
# env_file in compose override: 컨테이너 내부로 주입
export NGINX_MODE="$MODE"

COMPOSE_CMD="docker compose --env-file $ENV_FILE -f docker-compose.yml -f $COMPOSE_OVERRIDE"
PROFILES=""
if $MONITORING; then
    PROFILES="--profile monitoring"
fi

DOMAIN_VAL=$(grep "^DOMAIN=" "$ENV_FILE" 2>/dev/null | cut -d= -f2 | tr -d ' ')
DOMAIN_VAL="${DOMAIN_VAL:-your-domain.com}"

echo "=============================="
echo " 배포 시작"
echo "=============================="
echo "  환경:     $TARGET"
echo "  환경파일: $ENV_FILE"
echo "  모드:     $MODE"
echo "  도메인:   $DOMAIN_VAL"
echo "  모니터링: $MONITORING"
echo "=============================="
echo ""

$COMPOSE_CMD $PROFILES up -d --build

echo ""
echo "=============================="
echo " 배포 완료"
echo "=============================="
if [ "$MODE" = "https" ]; then
    echo "  MCP:    https://$DOMAIN_VAL/mcp"
    echo "  Health: https://$DOMAIN_VAL/health"
else
    echo "  MCP:    http://$DOMAIN_VAL/mcp"
    echo "  Health: http://$DOMAIN_VAL/health"
fi
if $MONITORING; then
    GRAFANA_PORT=$(grep "^GRAFANA_PORT=" "$ENV_FILE" 2>/dev/null | cut -d= -f2 | tr -d ' ')
    echo "  Grafana: http://$DOMAIN_VAL:${GRAFANA_PORT:-3000}"
fi
echo "=============================="
