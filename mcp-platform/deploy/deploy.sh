#!/bin/bash
# deploy.sh — mcp-platform 통합 배포 헬퍼
# NEXT_PUBLIC_API_URL 을 admin-front/.env.production 에 자동으로 기록한 뒤
# docker compose 명령을 실행합니다.
#
# 사용법:
#   ./deploy.sh up -d --build     # 전체 스택 빌드 & 기동
#   ./deploy.sh down               # 중지 (볼륨 유지)
#   ./deploy.sh down -v            # 중지 + 볼륨 삭제
#   ./deploy.sh logs -f            # 전체 로그
#   ./deploy.sh ps                 # 컨테이너 상태

set -e
cd "$(dirname "$0")"

if [ ! -f .env ]; then
  echo "Error: .env 파일이 없습니다."
  echo "       cp .env.example .env  후 값을 채워주세요."
  exit 1
fi

# .env 로드 (공백/특수문자 포함 값 안전 처리)
set -a
# shellcheck source=/dev/null
source .env
set +a

# NEXT_PUBLIC_API_URL 검증
if [ -z "$NEXT_PUBLIC_API_URL" ] || [ "$NEXT_PUBLIC_API_URL" = "http://YOUR_SERVER_IP" ]; then
  echo "Warning: .env 의 NEXT_PUBLIC_API_URL 이 설정되지 않았습니다."
  echo "         Nginx 경유 주소를 입력하세요 (예: http://192.168.1.100)"
  read -rp "NEXT_PUBLIC_API_URL: " NEXT_PUBLIC_API_URL
fi

# admin-front/.env.production 생성
ADMIN_ENV="../admin-front/.env.production"
echo "→ $ADMIN_ENV 업데이트"
cat > "$ADMIN_ENV" <<EOF
NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
EOF

echo "→ docker compose $*"
exec docker compose "$@"
