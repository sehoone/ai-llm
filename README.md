# ai-llm

1. python 설치. 3.12.7
https://www.python.org/downloads/windows/

2. 가상환경 생성(for windows)
    - 명령어 실행
        ```sh
        python -m venv venv
        ```
2. 가상환경 활성화
    - 명령어 실행
        ```sh
        .\venv\Scripts\activate
        ```
3. 라이브러리 install
    - 명령어 실행
        ```sh
        pip install -r requirements.txt
        ```
4. 가상환경 비활성화
    - 명령어 실행
        ```sh
        deactivate
        ```

## Windows 환경에서 pyenv 설치 방법

1. Git for Windows 설치
   - [Git for Windows 다운로드](https://gitforwindows.org/)

2. pyenv-win 설치
   - PowerShell 또는 명령 프롬프트를 관리자 권한으로 실행
   - 다음 명령어 실행:
     ```sh
     git clone https://github.com/pyenv-win/pyenv-win.git $HOME/.pyenv
     ```

3. 환경 변수 설정
   - 다음 경로를 `PATH` 환경 변수에 추가:
     - `%USERPROFILE%\.pyenv\pyenv-win\bin`
     - `%USERPROFILE%\.pyenv\pyenv-win\shims`
   - PowerShell에서 다음 명령어 실행:
     ```sh
     [System.Environment]::SetEnvironmentVariable('PYENV', "$HOME\.pyenv\pyenv-win", 'User')
     [System.Environment]::SetEnvironmentVariable('PATH', "$env:PATH;$HOME\.pyenv\pyenv-win\bin;$HOME\.pyenv\pyenv-win\shims", 'User')
     ```

4. 터미널 재시작
   - 변경 사항을 적용하려면 터미널을 닫고 다시 엽니다.

5. 설치 확인
   - 다음 명령어를 실행하여 `pyenv`가 올바르게 설치되었는지 확인:
     ```sh
     pyenv --version
     ```

6. Python 버전 설치
   - `pyenv`를 사용하여 특정 Python 버전 설치 (예: Python 3.12.7):
     ```sh
     pyenv install 3.12.7
     pyenv global 3.12.7
     ```