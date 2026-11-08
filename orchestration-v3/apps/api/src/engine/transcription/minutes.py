"""전사로부터 구조화된 회의록 생성(순수 LLM + JSON) + 마크다운 렌더.

긴 전사는 map-reduce: 구간별 요약(map) → 통합 구조화(reduce). 짧은 전사는 1-shot.
LLM 설정은 도메인이 `llm_resource`를 해석해 `LlmConfig`로 주입(engine은 DB 미조회 — ADR-0005).
map-reduce 임계값은 파라미터로 주입(engine은 settings 미참조).

동기 함수 — 도메인이 `asyncio.to_thread`로 오프로드한다(V2 비동기 gather 대신 순차 map).
"""

from __future__ import annotations

import json
import logging

from langchain_core.messages import HumanMessage, SystemMessage

from src.engine.llm.config import LlmConfig
from src.engine.llm.model import build_chat_model

logger = logging.getLogger(__name__)

_DEFAULT_MAP_REDUCE_THRESHOLD = 12000
_DEFAULT_CHUNK_SIZE = 8000

_MAP_SYSTEM_PROMPT = """다음은 긴 회의 전사의 '일부(청크)'입니다. 이 구간의 핵심만 간결히 정리하세요.
불릿 형식으로 아래 항목을 한국어로 작성하되, 해당 구간에 없는 항목은 생략하세요:
- 발화한 참석자(화자)
- 논의 주제와 핵심 포인트
- 결정 사항
- 액션 아이템 (담당자/기한 포함)

전사에 근거한 사실만 적고, 내용을 지어내지 마세요. JSON이 아닌 불릿 텍스트로만 출력하세요."""

_SYSTEM_PROMPT = """당신은 전문 회의록 작성자입니다. 아래 회의 전사(화자 라벨 포함)를 분석하여
구조화된 회의록을 작성하세요. 반드시 아래 JSON 형식만 반환하고, 그 외 텍스트는 출력하지 마세요.

{
  "title": "회의 제목 (추론)",
  "attendees": ["참석자(화자) 목록"],
  "agenda": ["안건 목록"],
  "discussion": [
    {"topic": "논의 주제", "points": ["핵심 논의 내용"], "speakers": ["관련 화자"]}
  ],
  "decisions": ["결정 사항"],
  "action_items": [
    {"task": "할 일", "owner": "담당자", "due": "기한(없으면 빈 문자열)"}
  ],
  "summary": "회의 전체 요약 (2-3문단)",
  "next_steps": ["다음 단계"]
}

주의사항:
- 전사에 근거해 사실만 작성하고, 내용을 지어내지 마세요.
- 화자 라벨(예: Speaker 1)이 실명으로 매핑되어 있으면 실명을 사용하세요.
- 정보가 부족한 필드는 빈 배열/빈 문자열로 두세요.
- 모든 출력은 한국어로 작성하세요."""


def _message_text(content: object) -> str:
    if isinstance(content, list):
        return " ".join(b.get("text", "") if isinstance(b, dict) else str(b) for b in content)
    return str(content)


def _transcript_text(segments: list[dict]) -> str:
    """세그먼트를 화자 라벨 포함 전사 문자열로 렌더."""
    lines: list[str] = []
    for s in segments:
        speaker = s.get("speaker_name") or s.get("speaker_label") or "화자"
        start_ms = int(s.get("start_ms", 0) or 0)
        ts = f"{start_ms // 60000:02d}:{(start_ms // 1000) % 60:02d}"
        lines.append(f"[{speaker} {ts}] {s.get('text', '')}")
    return "\n".join(lines)


def _parse_json(content: str) -> dict:
    """LLM 응답에서 첫 JSON 객체를 관대하게 추출."""
    try:
        start = content.find("{")
        end = content.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(content[start:end])
    except (ValueError, TypeError):
        logger.warning("minutes_json_parse_failed")
    return {"summary": content.strip()}


def _invoke(config: LlmConfig, system: str, user: str) -> str:
    model = build_chat_model(config, system_prompt=None)
    resp = model.invoke([SystemMessage(content=system), HumanMessage(content=user)])
    return _message_text(resp.content)


def _chunk_segments(segments: list[dict], budget: int) -> list[list[dict]]:
    """세그먼트를 budget 문자 이하 청크로 분할(발화 단위 유지)."""
    chunks: list[list[dict]] = []
    current: list[dict] = []
    size = 0
    for s in segments:
        line_len = len(s.get("text", "")) + 32  # 화자/타임스탬프 오버헤드
        if size + line_len > budget and current:
            chunks.append(current)
            current = []
            size = 0
        current.append(s)
        size += line_len
    if current:
        chunks.append(current)
    return chunks


def generate_minutes(
    title: str,
    segments: list[dict],
    config: LlmConfig,
    *,
    map_reduce_threshold: int = _DEFAULT_MAP_REDUCE_THRESHOLD,
    chunk_size: int = _DEFAULT_CHUNK_SIZE,
) -> dict:
    """전사 세그먼트에서 구조화된 회의록 생성(동기).

    Returns:
        dict: ``{"summary": str, "content": dict, "model_used": str}``.
    """
    transcript = _transcript_text(segments)
    if not transcript.strip():
        return {
            "summary": "",
            "content": {"summary": "전사 내용이 비어 있어 회의록을 생성할 수 없습니다."},
            "model_used": config.model,
        }

    if len(transcript) <= map_reduce_threshold:
        data = _single_shot(title, transcript, config)
    else:
        logger.info("minutes_map_reduce chars=%s threshold=%s", len(transcript), map_reduce_threshold)
        partials = _map(segments, config, chunk_size)
        data = _reduce(title, partials, config)

    return {"summary": data.get("summary", ""), "content": data, "model_used": config.model}


def _single_shot(title: str, transcript: str, config: LlmConfig) -> dict:
    user_message = f"회의 제목(참고): {title or '제목 없음'}\n\n전사 내용:\n{transcript}"
    return _parse_json(_invoke(config, _SYSTEM_PROMPT, user_message))


def _map(segments: list[dict], config: LlmConfig, chunk_size: int) -> list[str]:
    """각 전사 청크를 불릿 노트로 순차 요약."""
    chunks = _chunk_segments(segments, chunk_size)
    partials: list[str] = []
    for i, chunk in enumerate(chunks):
        chunk_text = _transcript_text(chunk)
        try:
            out = _invoke(
                config, _MAP_SYSTEM_PROMPT, f"[구간 {i + 1}/{len(chunks)}]\n{chunk_text}"
            ).strip()
            if out:
                partials.append(out)
        except Exception:
            logger.warning("minutes_map_chunk_failed index=%s", i, exc_info=True)
    return partials


def _reduce(title: str, partials: list[str], config: LlmConfig) -> dict:
    """부분 요약들을 최종 구조화 회의록으로 통합."""
    if not partials:
        return {"summary": "회의록 생성에 실패했습니다 (부분 요약 없음)."}
    combined = "\n\n".join(f"[부분 요약 {i + 1}]\n{p}" for i, p in enumerate(partials))
    user_message = (
        f"회의 제목(참고): {title or '제목 없음'}\n\n"
        "아래는 긴 회의를 구간별로 나눠 요약한 '부분 요약'들입니다. "
        "이 부분 요약들을 시간 순서대로 통합하여 하나의 회의록으로 작성하세요.\n\n"
        f"{combined}"
    )
    return _parse_json(_invoke(config, _SYSTEM_PROMPT, user_message))


def minutes_to_markdown(title: str, content: dict) -> str:
    """구조화 회의록을 마크다운으로 렌더(아티팩트 발행용)."""
    md: list[str] = [f"# {content.get('title') or title or '회의록'}", ""]

    attendees = content.get("attendees") or []
    if attendees:
        md.append("## 참석자")
        md.append(", ".join(str(a) for a in attendees))
        md.append("")

    agenda = content.get("agenda") or []
    if agenda:
        md.append("## 안건")
        md.extend(f"{i}. {a}" for i, a in enumerate(agenda, 1))
        md.append("")

    discussion = content.get("discussion") or []
    if discussion:
        md.append("## 논의 내용")
        for d in discussion:
            topic = d.get("topic", "") if isinstance(d, dict) else str(d)
            md.append(f"### {topic}")
            for p in (d.get("points") or []) if isinstance(d, dict) else []:
                md.append(f"- {p}")
            md.append("")

    decisions = content.get("decisions") or []
    if decisions:
        md.append("## 결정 사항")
        md.extend(f"- {d}" for d in decisions)
        md.append("")

    action_items = content.get("action_items") or []
    if action_items:
        md.append("## 액션 아이템")
        for a in action_items:
            if isinstance(a, dict):
                owner = a.get("owner", "")
                task = a.get("task", "")
                due = a.get("due", "")
                suffix = f" (담당: {owner}{', 기한: ' + due if due else ''})" if owner or due else ""
                md.append(f"- [ ] {task}{suffix}")
            else:
                md.append(f"- [ ] {a}")
        md.append("")

    summary = content.get("summary")
    if summary:
        md.append("## 요약")
        md.append(str(summary))
        md.append("")

    next_steps = content.get("next_steps") or []
    if next_steps:
        md.append("## 다음 단계")
        md.extend(f"- {n}" for n in next_steps)
        md.append("")

    return "\n".join(md).strip()
