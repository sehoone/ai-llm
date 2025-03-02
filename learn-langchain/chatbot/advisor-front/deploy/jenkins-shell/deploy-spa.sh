#!/bin/bash

# deploy step
echo "** deploy start **"

REMOTE_USER="user" # 원격 서버 사용자 이름
REMOTE_HOST="111.111.111.111" # 원격 서버 IP 주소 또는 도메인
REMOTE_DIR="/path/to/remote/directory" # 원격 서버의 배포 디렉토리
LOCAL_BUILD_DIR="/path/to/local/build/directory" # 로컬 빌드 디렉토리
SSH_KEY_PATH="~/sshtest/id_rsa" # SSH 키 경로

# 1. 소스 배포
echo "** 1. deploy spa build file **"
# 빌드된 파일을 원격 서버로 업로드
scp -i $SSH_KEY_PATH -r $LOCAL_BUILD_DIR/* $REMOTE_USER@$REMOTE_HOST:$REMOTE_DIR

# 2. 원격 서버에서 배포 실행
ssh -i $SSH_KEY_PATH $REMOTE_USER@$REMOTE_HOST << 'EOF'
  cd /web/spa_jenkins
  cp -r dist/* /web/spa
  # 3. 삭제하지 않을 파일 and 파일수정일이 7일이 지난 파일 삭제 및 빌드 파일 삭제
  find . -type f -not -path './images/*' -mtime +7 -print | grep -Fxvf dontdel.txt | xargs -r -d'\n' rm
  rm -rf /web/spa_jenkins/dist/*
EOF

echo "** deploy end **"