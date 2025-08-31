#!/bin/bash

echo "FastMCP 프로젝트 설정 (uv 사용)을 시작합니다..."

# uv가 설치되어 있는지 확인
if ! command -v uv &> /dev/null; then
    echo "uv가 설치되어 있지 않습니다. uv를 설치합니다..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    if [ $? -ne 0 ]; then
        echo "오류: uv 설치에 실패했습니다."
        echo "수동으로 설치하세요: https://docs.astral.sh/uv/getting-started/installation/"
        exit 1
    fi
    echo "uv가 성공적으로 설치되었습니다."
    # PATH 업데이트
    export PATH="$HOME/.cargo/bin:$PATH"
fi

echo "uv 버전을 확인합니다..."
uv --version

echo "가상환경을 생성하고 패키지를 설치합니다..."
uv sync
if [ $? -ne 0 ]; then
    echo "오류: 패키지 설치에 실패했습니다."
    exit 1
fi

echo ""
echo "===== 설치 완료 ====="
echo "uv를 사용하여 가상환경과 패키지가 설치되었습니다."
echo ""
echo "사용법:"
echo "1. 가상환경에서 명령 실행: uv run python integrated_server.py"
echo "2. 테스트 실행: uv run python test_tools.py"
echo "3. 쉘 활성화: uv shell"
echo "4. 패키지 추가: uv add package-name"
echo "5. 개발 패키지 추가: uv add --dev package-name"
echo ""
echo "설치된 패키지 목록:"
uv tree
echo ""
