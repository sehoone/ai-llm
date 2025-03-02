# Base Image
FROM ubuntu:latest

# 필요한 패키지 설치, cache 비우기
RUN apt-get update && \
    apt-get install -y curl sudo && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# 새로운 사용자 생성 및 비밀번호 설정
ENV USER="sehoon" \
    PASSWORD="open1404"
RUN useradd -m ${USER} && echo "${USER}:${PASSWORD}" | chpasswd && adduser ${USER} sudo && \
    sed -i "/^root/ c\root:!:18291:0:99999:7:::" /etc/shadow

# code-server 설치 및 세팅
ENV WORKINGDIR="/home/${USER}/vscode"
RUN curl -fsSL https://code-server.dev/install.sh | sh && \
    mkdir ${WORKINGDIR} && \
    su ${USER} -c "code-server --install-extension ms-python.python \
                               --install-extension ms-azuretools.vscode-docker" && \
    rm -rf ${WORKINGDIR}/.local ${WORKINGDIR}/.cache
