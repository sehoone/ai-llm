"""샘플 02: 딥씽킹 에이전트 — 노드 구현

실제 구현: src/common/langgraph/_nodes.py

핵심 개념:
- think 노드: LLM에게 "답하지 말고 계획만 세워라"고 지시
- verify 노드: LLM에게 "이전 답변을 평가하라"고 지시 → 품질 루프
- Command 반환: 노드가 다음에 실행할 노드(goto)를 직접 결정
- 최대 반복 제한: verify_iterations로 무한 루프 방지

흐름:
    [복잡한 질문]
         │
         ▼
    think ──→ "전략: 먼저 X를 설명하고 Y로 심화..."
         │
         ▼
    chat  ──→ 실제 답변 생성 (think의 계획 참고)
         │
         ▼
    verify ──→ {"approved": false, "feedback": "예시가 부족함"}
         │ (피드백이 있으면)
         ▼
    chat  ──→ 개선된 답변 (feedback 반영)
         │
         ▼
    verify ──→ {"approved": true, "feedback": ""}
         │
         ▼
        END
"""

import json
import re
from typing import Optional

from langchain_core.messages import AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END
from langgraph.graph.state import Command
from langgraph.types import RunnableConfig

from .state import DeepThinkingState

_MAX_VERIFY_ITERATIONS = 2

# ── 프롬프트 ───────────────────────────────────────────────────────────────────

# think 노드: "답하지 말고 전략만 수립"이 핵심
_THINK_PROMPT = """당신은 AI 응답 전략 수립 전문가입니다.
사용자 질문에 직접 답하지 말고, 최적의 응답 전략을 분석하세요.

분석할 내용:
1. 질문의 핵심 요구사항 분해
2. 필요한 배경 지식과 맥락
3. 응답 구조 계획 (도입 → 핵심 → 예시 → 심화 → 결론)
4. 적절한 톤과 스타일

내부 독백 형태로 작성 (예: "사용자는 X를 묻고 있다. Y와 Z를 반드시 다뤄야 한다...")
사용자에게 직접 말하지 말 것. 최종 답변 텍스트를 쓰지 말 것.
"""

# verify 노드: JSON 형식 강제로 파싱 가능하게
_VERIFY_PROMPT = """당신은 AI 응답 품질 평가자입니다.
직전 assistant 응답이 사용자 질문을 충분히 충족하는지 평가하세요.

평가 기준:
1. 완결성: 질문의 모든 부분에 답했는가?
2. 정확성: 사실 오류나 논리적 모순이 없는가?
3. 깊이: 충분히 상세하고 통찰력 있는가?
4. 명확성: 이해하기 쉽게 구조화되었는가?

반드시 아래 JSON 형식으로만 응답하세요 (마크다운, 추가 텍스트 금지):
{"approved": true, "feedback": ""}
또는
{"approved": false, "feedback": "<구체적인 개선 지시사항>"}
"""

_TAG_RE = re.compile(r"^\[Deep Thinking[^\]]*\]\s*", re.MULTILINE)

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)


# ── 노드 함수들 ────────────────────────────────────────────────────────────────

async def think_node(state: DeepThinkingState, config: RunnableConfig) -> Command:
    """전략 수립 노드.

    LLM에게 전략 계획만 세우도록 지시한다.
    결과는 thinking_context에 저장되어 chat 노드에서 system_prompt에 주입된다.

    Command(goto="chat"): 항상 chat 노드로 이동
    """
    messages = [SystemMessage(content=_THINK_PROMPT)] + list(state.messages)
    response = await llm.ainvoke(messages, config=config)

    # thinking_context를 chat 노드에서 사용할 수 있도록 상태에 저장
    thinking_content = str(response.content)

    # 스트리밍 시 구분을 위한 태그 추가
    response.content = f"[Deep Thinking - Analysis]\n{thinking_content}"

    return Command(
        update={
            "messages": [response],
            "thinking_context": thinking_content,
        },
        goto="chat",
    )


async def chat_node(state: DeepThinkingState, config: RunnableConfig) -> Command:
    """메인 응답 생성 노드.

    thinking_context와 verify_feedback을 system_prompt에 주입하여
    이전 단계의 분석과 피드백을 반영한 응답을 생성한다.
    """
    system_parts = ["당신은 전문 AI 어시스턴트입니다."]

    # think 노드의 전략 계획 주입
    if state.thinking_context:
        system_parts.append(f"\n\n[실행 계획]\n{state.thinking_context}")

    # verify 노드의 품질 피드백 주입
    if state.verify_feedback:
        system_parts.append(
            f"\n\n[품질 피드백 — 반드시 이 지점을 개선할 것]\n{state.verify_feedback}"
        )

    system_prompt = "".join(system_parts)

    # 메시지에서 Deep Thinking 태그가 붙은 분석/검증 메시지 제외
    # (사용자에게 보여줄 메시지만 LLM에 전달)
    filtered_messages = [
        m for m in state.messages
        if not (hasattr(m, "content") and _TAG_RE.match(str(m.content)))
    ]

    messages = [SystemMessage(content=system_prompt)] + filtered_messages
    response = await llm.ainvoke(messages, config=config)

    # 딥씽킹 모드에서는 answer 태그 추가
    response.content = f"[Deep Thinking - Answer]\n{response.content}"

    # verify 노드로 품질 검증
    return Command(
        update={"messages": [response], "verify_feedback": None},
        goto="verify",
    )


async def verify_node(state: DeepThinkingState, config: RunnableConfig) -> Command:
    """품질 검증 노드.

    LLM이 직전 응답을 평가하여 승인 여부와 피드백을 JSON으로 반환.
    - approved=True: END로 종료
    - approved=False: feedback과 함께 chat 노드로 재시도 요청
    - 최대 반복 횟수(_MAX_VERIFY_ITERATIONS) 초과 시 강제 종료
    """
    iterations = state.verify_iterations

    # 무한 루프 방지: 최대 반복 초과 시 현재 응답으로 종료
    if iterations >= _MAX_VERIFY_ITERATIONS:
        return Command(
            update={"verify_iterations": 0, "verify_feedback": None},
            goto=END,
        )

    messages = [SystemMessage(content=_VERIFY_PROMPT)] + list(state.messages)
    response = await llm.ainvoke(messages, config=config)

    raw = _TAG_RE.sub("", str(response.content)).strip()

    try:
        result = json.loads(raw)
        approved: bool = result.get("approved", True)
        feedback: str = result.get("feedback", "")
    except json.JSONDecodeError:
        # JSON 파싱 실패 시 승인으로 처리 (안전한 기본값)
        approved, feedback = True, ""

    if approved or not feedback:
        return Command(
            update={"verify_iterations": 0, "verify_feedback": None},
            goto=END,
        )

    # 품질 미달: 피드백을 상태에 저장하고 chat 재시도
    response.content = f"[Deep Thinking - Verification (attempt {iterations + 1})]\n{feedback}"
    return Command(
        update={
            "messages": [response],
            "verify_feedback": feedback,
            "verify_iterations": iterations + 1,
        },
        goto="chat",
    )


def route_start(state: DeepThinkingState) -> str:
    """시작점 라우팅: 딥씽킹 모드이거나 복잡한 질문이면 think 노드로.

    실제 코드(NodesMixin._route_start)에서는 키워드 기반 복잡도 판단 로직이 있음.
    여기서는 is_deep_thinking 플래그만 사용하여 단순화.
    """
    return "think" if state.is_deep_thinking else "chat"
