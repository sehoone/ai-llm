"""Generate structured meeting minutes from a transcript via the LLM.

Reuses the shared ``llm_service`` (DB-driven resource selection, retry, circuit
breaker) and follows the JSON-forcing prompt + lenient parse pattern used by
``voice_evaluation.EvaluationService``. Also renders the structured minutes to
Markdown for publishing as an artifact.
"""

import asyncio
import json
from typing import Dict, List

from langchain_core.messages import HumanMessage, SystemMessage

from src.common.config import settings
from src.common.logging import logger
from src.common.services.llm import llm_service

_MAP_SYSTEM_PROMPT = """다음은 긴 회의 전사의 '일부(청크)'입니다. 이 구간의 핵심만 간결히 정리하세요.
불릿 형식으로 아래 항목을 한국어로 작성하되, 해당 구간에 없는 항목은 생략하세요:
- 발화한 참석자(화자)
- 논의 주제와 핵심 포인트
- 결정 사항
- 액션 아이템 (담당자/기한 포함)

전사에 근거한 사실만 적고, 내용을 지어내지 마세요. JSON이 아닌 불릿 텍스트로만 출력하세요."""

_SYSTEM_PROMPT = """당신은 전문 회의록 작성자입니다. 아래 회의 전사(화자 라벨 포함)를 분석하여
구조화된 회의록을 작성하세요. 반드시 아래 JSON 형식만 반환하고, 그 외 텍스트는 출력하지 마세요.

{{
  "title": "회의 제목 (추론)",
  "attendees": ["참석자(화자) 목록"],
  "agenda": ["안건 목록"],
  "discussion": [
    {{"topic": "논의 주제", "points": ["핵심 논의 내용"], "speakers": ["관련 화자"]}}
  ],
  "decisions": ["결정 사항"],
  "action_items": [
    {{"task": "할 일", "owner": "담당자", "due": "기한(없으면 빈 문자열)"}}
  ],
  "summary": "회의 전체 요약 (2-3문단)",
  "next_steps": ["다음 단계"]
}}

주의사항:
- 전사에 근거해 사실만 작성하고, 내용을 지어내지 마세요.
- 화자 라벨(예: Speaker 1)이 실명으로 매핑되어 있으면 실명을 사용하세요.
- 정보가 부족한 필드는 빈 배열/빈 문자열로 두세요.
- 모든 출력은 한국어로 작성하세요."""


class MinutesService:
    """Create and render structured minutes."""

    def __init__(self) -> None:
        self.llm_service = llm_service
        self.model = settings.MEETING_SUMMARY_MODEL

    @staticmethod
    def _transcript_text(segments: List[Dict]) -> str:
        """Render segments to a speaker-labelled transcript string."""
        lines = []
        for s in segments:
            speaker = s.get("speaker_name") or s.get("speaker_label") or "화자"
            start_ms = int(s.get("start_ms", 0) or 0)
            ts = f"{start_ms // 60000:02d}:{(start_ms // 1000) % 60:02d}"
            lines.append(f"[{speaker} {ts}] {s.get('text', '')}")
        return "\n".join(lines)

    async def generate(self, title: str, segments: List[Dict]) -> Dict:
        """Generate structured minutes from transcript segments.

        For short transcripts this is a single LLM call. For long transcripts
        (over ``MEETING_MAP_REDUCE_CHAR_THRESHOLD`` characters) it runs a
        map-reduce: summarize each chunk in parallel (map), then combine the
        partial summaries into the final structured minutes (reduce).

        Returns:
            dict: ``{"summary": str, "content": dict, "model_used": str}``.
        """
        transcript = self._transcript_text(segments)
        if not transcript.strip():
            return {
                "summary": "",
                "content": {"summary": "전사 내용이 비어 있어 회의록을 생성할 수 없습니다."},
                "model_used": self.model,
            }

        try:
            if len(transcript) <= settings.MEETING_MAP_REDUCE_CHAR_THRESHOLD:
                data = await self._single_shot(title, transcript)
            else:
                logger.info(
                    "minutes_map_reduce",
                    transcript_chars=len(transcript),
                    threshold=settings.MEETING_MAP_REDUCE_CHAR_THRESHOLD,
                )
                partials = await self._map(segments)
                data = await self._reduce(title, partials)
        except Exception as e:
            logger.error("minutes_generate_failed", error=str(e), exc_info=True)
            raise

        return {
            "summary": data.get("summary", ""),
            "content": data,
            "model_used": self.model,
        }

    async def _single_shot(self, title: str, transcript: str) -> Dict:
        """One-call structured summarization for short transcripts."""
        user_message = f"회의 제목(참고): {title or '제목 없음'}\n\n전사 내용:\n{transcript}"
        response = await self.llm_service.call(
            messages=[
                SystemMessage(content=_SYSTEM_PROMPT),
                HumanMessage(content=user_message),
            ],
            model_name=self.model,
            use_tools=False,
        )
        content = response.content
        return self._parse_json(content if isinstance(content, str) else json.dumps(content))

    def _chunk_segments(self, segments: List[Dict], budget: int) -> List[List[Dict]]:
        """Split segments into chunks under ``budget`` chars, keeping utterances whole."""
        chunks: List[List[Dict]] = []
        current: List[Dict] = []
        size = 0
        for s in segments:
            line_len = len(s.get("text", "")) + 32  # +speaker/timestamp overhead
            if size + line_len > budget and current:
                chunks.append(current)
                current = []
                size = 0
            current.append(s)
            size += line_len
        if current:
            chunks.append(current)
        return chunks

    async def _map(self, segments: List[Dict]) -> List[str]:
        """Summarize each transcript chunk into bullet notes (run in parallel)."""
        chunks = self._chunk_segments(segments, settings.MEETING_CHUNK_CHAR_SIZE)

        async def _summarize_chunk(index: int, chunk: List[Dict]) -> str:
            chunk_text = self._transcript_text(chunk)
            try:
                response = await self.llm_service.call(
                    messages=[
                        SystemMessage(content=_MAP_SYSTEM_PROMPT),
                        HumanMessage(content=f"[구간 {index + 1}/{len(chunks)}]\n{chunk_text}"),
                    ],
                    model_name=self.model,
                    use_tools=False,
                )
                return str(response.content).strip()
            except Exception as e:
                logger.warning("minutes_map_chunk_failed", index=index, error=str(e))
                return ""

        results = await asyncio.gather(
            *(_summarize_chunk(i, c) for i, c in enumerate(chunks))
        )
        return [r for r in results if r]

    async def _reduce(self, title: str, partials: List[str]) -> Dict:
        """Combine partial chunk summaries into final structured minutes."""
        if not partials:
            return {"summary": "회의록 생성에 실패했습니다 (부분 요약 없음)."}
        combined = "\n\n".join(
            f"[부분 요약 {i + 1}]\n{p}" for i, p in enumerate(partials)
        )
        user_message = (
            f"회의 제목(참고): {title or '제목 없음'}\n\n"
            "아래는 긴 회의를 구간별로 나눠 요약한 '부분 요약'들입니다. "
            "이 부분 요약들을 시간 순서대로 통합하여 하나의 회의록으로 작성하세요.\n\n"
            f"{combined}"
        )
        response = await self.llm_service.call(
            messages=[
                SystemMessage(content=_SYSTEM_PROMPT),
                HumanMessage(content=user_message),
            ],
            model_name=self.model,
            use_tools=False,
        )
        content = response.content
        return self._parse_json(content if isinstance(content, str) else json.dumps(content))

    @staticmethod
    def _parse_json(content: str) -> Dict:
        """Extract the first JSON object from an LLM response (lenient)."""
        try:
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(content[start:end])
        except (ValueError, TypeError) as e:
            logger.warning("minutes_json_parse_failed", error=str(e))
        return {"summary": content.strip()}

    @staticmethod
    def to_markdown(title: str, content: Dict) -> str:
        """Render structured minutes to Markdown (for artifact publishing)."""
        md: List[str] = [f"# {content.get('title') or title or '회의록'}", ""]

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


minutes_service = MinutesService()
