"""Query transformation strategies for RAG: HyDE and Multi-Query expansion."""

import asyncio
from typing import List

from langchain_core.messages import HumanMessage, SystemMessage

from src.common.logging import logger
from src.common.services.llm import llm_service


class QueryTransformer:
    """Transforms user queries to improve RAG retrieval quality.

    Strategies:
    - HyDE: generates a hypothetical document that would answer the query,
      then embeds that document for search (closes query-document embedding gap).
    - Multi-Query: rephrases the query N ways to cover different vocabulary/angles,
      then merges results with RRF in the caller.
    """

    _HYDE_SYSTEM = (
        "당신은 문서 작성 전문가입니다. "
        "사용자 질문에 대한 이상적인 답변 단락을 2~3문장으로 작성하세요. "
        "실제 문서에서 발췌한 것처럼 자연스럽게 서술하고, 답변 내용만 출력하세요."
    )
    _MULTI_QUERY_SYSTEM = (
        "사용자 질문을 {n}가지 다른 방식으로 다시 표현하세요. "
        "각 표현은 서로 다른 어휘나 관점을 사용해야 합니다. "
        "번호나 기호 없이 한 줄씩 출력하세요."
    )

    def __init__(self) -> None:
        self.llm_service = llm_service

    async def hyde_transform(self, query: str) -> str:
        """Generate a hypothetical document that would answer the query.

        Returns the hypothetical document text on success, or the original
        query string on failure so the caller always has a valid fallback.
        """
        try:
            response = await self.llm_service.call(
                messages=[
                    SystemMessage(content=self._HYDE_SYSTEM),
                    HumanMessage(content=query),
                ],
                model_name="gpt-5-nano",
                use_tools=False,
            )
            doc = str(response.content).strip()
            if not doc:
                return query
            logger.info("hyde_transform_completed", query_len=len(query), doc_len=len(doc))
            return doc
        except Exception as e:
            logger.warning("hyde_transform_failed", error=str(e))
            return query

    async def multi_query_expand(self, query: str, n: int = 2) -> List[str]:
        """Generate n alternative phrasings of the query.

        Returns [original_query, alt_1, ..., alt_n]. On failure returns
        [original_query] so the caller always has at least the original.
        """
        try:
            response = await self.llm_service.call(
                messages=[
                    SystemMessage(content=self._MULTI_QUERY_SYSTEM.format(n=n)),
                    HumanMessage(content=query),
                ],
                model_name="gpt-5-nano",
                use_tools=False,
            )
            lines = [line.strip() for line in str(response.content).strip().splitlines() if line.strip()]
            alternatives = lines[:n]
            logger.info("multi_query_expand_completed", alternatives_count=len(alternatives))
            return [query] + alternatives
        except Exception as e:
            logger.warning("multi_query_expand_failed", error=str(e))
            return [query]

    async def generate_all(self, query: str, multi_query_n: int = 2) -> tuple[str, List[str]]:
        """Run HyDE and Multi-Query expansion concurrently.

        Returns:
            (hyde_doc, query_variants) where query_variants includes the original.
        """
        hyde_doc, query_variants = await asyncio.gather(
            self.hyde_transform(query),
            self.multi_query_expand(query, n=multi_query_n),
        )
        return hyde_doc, query_variants


query_transformer = QueryTransformer()
