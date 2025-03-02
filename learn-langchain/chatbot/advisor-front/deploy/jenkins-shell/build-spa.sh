#!/bin/bash

echo "** build start **"
# set node binary
echo "** set node binary **"
export PATH=/home/spa/download/node-v20.11.1-linux-x64-glibc-217/bin:$PATH

# build step
# 1. build project
echo "** 1. install and build project **"
pnpm install --no-frozen-lockfile
pnpm build-only:dev

# 2. dist 디렉토리 내부의 파일 목록을 filelist.txt에 저장. deploy 할때 해당 파일만 남기고 삭제하기위함
# echo "** 2. make file list for delete pre build file **"
# ls dist/assets | grep -v 'images' > dist/assets/filelist.txt

echo "** build end **"