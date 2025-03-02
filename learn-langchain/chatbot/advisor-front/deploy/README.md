# node 오프라인 설치방법 및 pnpm 설치방법
- 오프라인 환경에서 pnpm을 설치할떄 공식문서에서 제공되는 방법(install.sh) 으로 하면 외부 접속이 안되어 불가
- 그래도 현재 적용할려는 환경은 npm을 통해서 proxy로 외부 연결은 가능하여 아래와 같이 pnpm을 설치하려고함

### 1. 다운로드
- node 다운로드 사이트에서 prebuild 된 파일을 다운받는다. 하단에 url에서 다운로드
- url: https://nodejs.org/en/download/prebuilt-binaries

### 2. node 환경변수 추가
- .bashrc 수정. 아래 내용 추가. 1번에서 다운로드한 파일 압축을 풀고 bin 경로를 설정
- export PATH={$압축 푼 파일경로}/bin:$PATH

### 3. 환경변수 적용
- 아래처럼 적용을 하면 되는데 기존에 전역으로 설치된 node가 있으면 다시 접속해야 적용됨(되야되는거 같은데 환경마다 다른거같음)
```sh 
source .bashrc
```

### 4. pnpm 설치
- npm install -g 를 사용하여 글로벌로 설치할경우, {$압축 푼 파일경로}/lib/node_modules 에 해당 라이브러리가 설치된다.
```sh
npm install -g pnpm
```

### 5. 기타
- 라이브러리 설치경로는 아래의 명령어로 확인가능

- 환경변수 확인
```sh
npm config ls -l
```

- 라이브러리 prefix 경로 변경(리눅스 권한 이슈로 라이브러리 설치가 안될경우 경로 변경)
```sh
npm config set prefix "{$압축 푼 파일경로}/lib/node_modules"
```

- 전역 npm registry 설정
```sh
npm config set registry https://your-registry-url/
```

# SSH접속시 ID/PW없이 접속방법
- 빌드서버에서 배포 대상서버로 접속할떄, 플러그인이나 에이전트가 없을경우 SSH로 접속해서 처리해야할 수 있음
- 배포 스크립트에 ID/PW 없이 접속하는 방법에 대한 설명

### 1. 빌드서버(client)
- ssh 키 생성(ssh키가 없는경우 생성). 옵션을 통해서 디폴트 ssh키가 아닌 특정경로에도 생성가능. ex. ssh-keygen -f ~/sshtest 
```shell
ssh-keygen
```

### 2. 배포서버(배포 대상 서버)
- ssh 인증키 등록. 1번에서 생성한 공개키(id_rsa.pub) 를 해당 파일에 추가. 추가할떄는 한줄로 입력하고 추가하고 싶다면 다음라인에 추가한다
```shell
vi ~/.ssh/authorized_keys
```

### 3. SSH접속
- 1번에서 특정경로에 생성한 key 파일로 접속하고자 한다면 i옵션을 통해서 접속. ssh -i ~/sshtest/id_rsa user@111.111.111.111
```shell
ssh user@111.111.111.111
```

### 4. 파일업로드
- 원격 서버의 배포 디렉토리로 이동. scp $REMOTE_USER@$REMOTE_HOST:$REMOTE_DIR
- scp -r /path/to/local/directory username@remote_host:/path/to/remote/directory

# 젠킨스 빌드 shell

```shell
#!/bin/bash

# set node binary
export PATH=/home/pmsdev/sehoon-test/download/node-v20.12.0-linux-x64-glibc-217/bin:$PATH

# build project
cd demo-project/
pnpm install
pnpm build-only:dev
```