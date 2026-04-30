"""Long-term memory mixin for LangGraphAgent."""

from mem0 import AsyncMemory

from src.common.config import settings
from src.common.logging import logger
from src.common.services.database import database_service


class MemoryMixin:
    """Provides long-term memory operations via mem0ai + pgvector.

    Requires ``self.memory`` (Optional[AsyncMemory]) set to ``None`` by the host class.
    """

    async def _resolve_llm_resource(self, model_name: str):
        """Return the best-matching active chat LLM resource for *model_name*, or None."""
        try:
            all_resources = await database_service.get_llm_resources()
            active = [r for r in all_resources if r.is_active and r.resource_type != "embedding"]
            return (
                next((r for r in active if r.model_name == model_name), None)
                or next((r for r in active if r.deployment_name == model_name), None)
                or (active[0] if active else None)
            )
        except Exception as e:
            logger.warning("failed_to_resolve_llm_resource", model_name=model_name, error=str(e))
        return None

    async def _resolve_embedding_resource(self, model_name: str):
        """Return the best-matching active embedding resource for *model_name*, or None."""
        try:
            embedding_resources = await database_service.get_embedding_resources()
            return (
                next((r for r in embedding_resources if r.model_name == model_name), None)
                or next((r for r in embedding_resources if r.deployment_name == model_name), None)
                or (embedding_resources[0] if embedding_resources else None)
            )
        except Exception as e:
            logger.warning("failed_to_resolve_embedding_resource", model_name=model_name, error=str(e))
        return None

    def _build_mem0_component_config(self, resource, model_name: str) -> dict:
        """Return a mem0ai LLM/embedder component config dict for the given resource."""
        if resource is None:
            return {"provider": "openai", "config": {"model": model_name}}

        provider = (resource.provider or "openai").lower()
        if provider == "azure":
            deployment = resource.deployment_name or resource.model_name or model_name
            azure_kwargs = {
                "api_key": resource.api_key,
                "azure_deployment": deployment,
                "azure_endpoint": resource.api_base,
            }
            if resource.api_version:
                azure_kwargs["api_version"] = resource.api_version
            return {"provider": "azure_openai", "config": {"model": deployment, "azure_kwargs": azure_kwargs}}

        cfg = {"model": model_name, "api_key": resource.api_key}
        if resource.api_base:
            cfg["openai_base_url"] = resource.api_base
        return {"provider": "openai", "config": cfg}

    async def _long_term_memory(self) -> AsyncMemory:
        """Lazily initialize and return the AsyncMemory instance."""
        if self.memory is None:
            llm_resource = await self._resolve_llm_resource(settings.LONG_TERM_MEMORY_MODEL)
            embedder_resource = await self._resolve_embedding_resource(settings.LONG_TERM_MEMORY_EMBEDDER_MODEL)
            llm_cfg = self._build_mem0_component_config(llm_resource, settings.LONG_TERM_MEMORY_MODEL)
            embedder_cfg = self._build_mem0_component_config(embedder_resource, settings.LONG_TERM_MEMORY_EMBEDDER_MODEL)
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
                    "llm": llm_cfg,
                    "embedder": embedder_cfg,
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
