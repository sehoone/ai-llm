# prompts

프롬프트는 **코드가 아닌 자산**이다 — 로직과 분리해 변경·리뷰·(향후)A·B를 재배포 없이 (ADR-0005 §5).

## 레이아웃

```
prompts/
├─ <domain>/<name>.jinja   # 템플릿 (예: chat/system.jinja)
└─ (loader)                # render(id, **vars) — 로직은 여기, 문구는 .jinja
```

- 참조는 id로: `render("chat.system", user=..., context=...)`.
- 문구 변경은 `.jinja`만 수정 — 서비스 코드 재배포 불필요.

> 현재는 골격 — 템플릿·로더는 도메인 이식 시 추가.
