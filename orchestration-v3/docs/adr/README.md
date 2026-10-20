# Architecture Decision Records (ADR)

orchestration-v3의 주요 아키텍처 결정을 기록합니다. 각 ADR은 결정 당시의 맥락·대안·결과를 담으며,
결정이 바뀌면 새 ADR로 기존 것을 `Superseded` 처리합니다(기존 파일은 보존).

## 형식

[MADR](https://adr.github.io/madr/) 변형을 사용합니다: **Context → Decision → Alternatives → Consequences**.

## 상태 값

`Proposed` → `Accepted` → (`Superseded by ADR-XXXX` | `Deprecated`)

## 목록

| ADR | 제목 | 상태 |
|-----|------|------|
| [0001](0001-monorepo-structure.md) | 모노레포 구조와 태스크 오케스트레이션(moon) | Superseded by 0003 |
| [0002](0002-polyglot-and-auth-boundary.md) | 폴리글랏 3서비스 유지와 인증 경계 | Superseded by 0003 |
| [0003](0003-single-python-backend.md) | 단일 Python 백엔드 + 사내 IdP 인증 위임 | Accepted (구조 섹션은 0004가 개정) |
| [0004](0004-apps-packages-monorepo-layout.md) | apps/* + packages/* 모노레포 레이아웃 채택 | Accepted |
| [0005](0005-ai-engine-layer.md) | AI 엔진 레이어 분리 (domains ↔ engine) | Accepted |
| [0006](0006-web-structure-and-oidc.md) | 프론트 구조(shadcn-admin) 및 OIDC 리다이렉트 인증 | Accepted |

## 관련 문서

- [`../structure-and-references.md`](../structure-and-references.md) — 위 결정들이 업계 표준·사실상 표준과 어떻게 정렬되는지 검증·참조 소스 모음 (ADR이 아닌 레퍼런스).
