#!/bin/bash

# deploy step
echo "** deploy start **"
# 1. 소스 배포
echo "** 1. deploy spa build file **"
cd /home/spa_jenkins
cp -r dist/* /home/web/spa

# 2. 삭제하지 않을 파일 목록 생성(기존파일을 제거하기 위해). 빌드할때 만든 filelist.txt를 사용
echo "** 2. make dont delete file list **"
cd /home/spa/assets
sed -e 's/^/\.\//' filelist.txt > dontdel.txt

# 3. 삭제하지 않을 파일 and 파일수정일이 6개월이 지난 파일 삭제 및 빌드 파일 삭제
echo "** 3. delete spa pre build file **"
find . -type f -not -path './images/*' -mtime +180 -print | grep -Fxvf dontdel.txt | xargs -r -d'\n' rm
rm -rf /home/spa_jenkins/dist/*

echo "** deploy end **"