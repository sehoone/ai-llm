"""Long-term memory mixin for LangGraphAgent."""

from mem0 import AsyncMemory

from src.common.config import settings
from src.common.logging import logger


class MemoryMixin:
    """Provides long-term memory operations via mem0ai + pgvector.

    Requires ``self.memory`` (Optional[AsyncMemory]) set to ``None`` by the host class.
    """

    async def _long_term_memory(self) -> AsyncMemory:
        """Lazily initialize and return the AsyncMemory instance."""
        if self.memory is None:
            self.memory = await AsyncMemory.from_config(
                config_dict={
                    "vector_store": {
                        "provider": "pgvector",
                        "config": {
                            "collection_name": settings.LONG_TERM_MEMORY_COLLECTION_NAME,
                            "dbname": settings.POSTGRES_DB,
                            "user": settings.POSTGRES_USER,
                            "password": settings.POSTGRES_PASSWORD,
                            "host": settings.POSTGRES_HOST,
                            "port": settings.POSTGRES_PORT,
                        },
                    },
                    "llm": {
                        "provider": "openai",
                        "config": {"model": settings.LONG_TERM_MEMORY_MODEL},
                    },
                    "embedder": {
                        "provider": "openai",
                        "config": {"model": settings.LONG_TERM_MEMORY_EMBEDDER_MODEL},
                    },
                }
            )
        return self.memory

    async def _get_relevant_memory(self, user_id: str, query: str) -> str:
        """Search long-term memory for context relevant to *query*.

        Returns an empty string on failure so the caller can continue gracefully.
        """
        try:
            memory = await self._long_term_memory()
            results = await memory.search(user_id=str(user_id), query=query)
            return "\n".join([f"* {r['memory']}" for r in results["results"]])
        except Exception as e:
            logger.error("failed_to_get_relevant_memory", error=str(e), user_id=user_id, query=query)
            return ""

    async def _update_long_term_memory(self, user_id: str, messages: list[dict], metadata: dict = None) -> None:
        """Persist *messages* to long-term memory, stripping image content first."""
        try:
            memory = await self._long_term_memory()

            filtered: list[dict] = []
            for msg in messages:
                if isinstance(msg.get("content"), list):
                    text_parts = [
                        block["text"]
                        for block in msg["content"]
                        if isinstance(block, dict) and block.get("type") == "text" and "text" in block
                    ] + [block for block in msg["content"] if isinstance(block, str)]
                    if text_parts:
                        filtered.append({"role": msg.get("role"), "content": "\n".join(text_parts)})
                else:
                    filtered.append(msg)

            if filtered:
                await memory.add(filtered, user_id=str(user_id), metadata=metadata)
                logger.info("long_term_memory_updated_successfully", user_id=user_id)
        except Exception as e:
            logger.exception("failed_to_update_long_term_memory", user_id=user_id, error=str(e))
