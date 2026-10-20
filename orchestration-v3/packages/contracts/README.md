# contracts

api ↔ web 계약. **단방향**이다 — api FastAPI가 진실의 원천(ADR-0003).

```
api (/openapi.json)  ──export──>  packages/contracts/openapi.json  ──codegen──>  web TS 타입
     tools/export_openapi.py                              web: pnpm gen:types
```

- `openapi.json` 은 **생성물**이라 git에 커밋하지 않는다(`.gitignore`). 재생성: `task gen-types`.
- 폴리글랏 시절의 교차언어 codegen·JWT 계약 복제는 단일 백엔드 전환으로 사라졌다(ADR-0003).
