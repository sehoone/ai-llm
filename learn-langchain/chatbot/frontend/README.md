# vite-base
> Vue3-Vite-Base

### 1. 기본 구성 환경 
- node v20.11.1
- pnpm 9.0.6
- vite 5.1.6
- vue 3.4.21
- eslint 8.49.0

### 2. 개발 환경
- Visual Studio Code 1.87.2
- plugins: Vue - Official
- plugins: Vetur
- plugins: Vue 3 Snippets
- plugins: Vue VSCode Snippets
- plugins: ESLint
- plugins: Auto Close Tag
- plugins: Git History
- plugins: Live Server
- plugins: PowerShell

### 3. 설치
```sh
cd vite-base
pnpm install

```

### 4. project 설정
```js
// .vscode/settings.json

{  
  "eslint.workingDirectories": [
    { "mode": "auto" }
  ],
  "editor.codeActionsOnSave": {
    "source.fixAll.eslint": "explicit"
  },
  "eslint.alwaysShowStatus": true,
  "eslint.codeAction.showDocumentation": {
    "enable": true
  },
  "eslint.format.enable": true,
  "editor.tabSize": 2,
  "editor.wordWrapColumn": 100,
}
```

### 5. 서버실행
- Front Server
```sh
pnpm run dev
```

### 6. Source Structure

```
- .vscode
  - settings.json : 현재 프로젝트 내에서 사용되는 에디터 설정
├── vue-base        # root
  ├── public        # Contains static assets and index.html
  ├── src           # Source Directory
    ├── assets               # App Assets and Styles
    ├── components           # 공통 컴포넌트
    ├── globals              # global 상수
    ├── layout               # layout
    ├── plugins              # plugin
    ├── libs                 # lib
    ├── router               # router
       ├── guard             # router before/after 처리
       ├── routes            # routes
          ├── 업무           # 업무그룹별 routes 정의
    ├── service              # service
       ├── 업무              # 업무별 패키지 생성
          ├── moduls         # store 및 비즈니스 로직
          ├── model          # type 정의
          ├── api            # api 정의
    ├── store                # store
    ├── types                # global or lib type정의
    ├── utils                # 유틸
    ├── views                # views
       ├── 업무              # 업무별 패키지 생성
          ├── components     # 업무별 Components
    ├── App.vue              # App.vue
    ├── main.ts              # main.js
  ├── browserslistrc         # browserslistrc
  ├── .env.*                 # 환경변수
  ├── eslintrc.js            # eslintrc.js
  ├── .gitignore             # gitignore
  ├── babel.config.js        # babel.config.json 
  ├── package.json           # package.json
  ├── package-lock.json      # package-lock.json
  ├── README.md              # README.md
  ├── tsconfig.json          # 타입스크립트 설정
  ├── vue.config.js          # Webpack Config
  ...

```
