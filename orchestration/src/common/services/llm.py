"""LLM service for managing LLM calls with retries and fallback mechanisms."""

import random
import time
from dataclasses import dataclass
from enum import Enum
from itertools import groupby
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from langchain_community.chat_models import ChatLiteLLM
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI, AzureChatOpenAI
from src.common.services.database import database_service
from src.llm_resources.models.llm_resource_model import LLMResource
from openai import (
    APIError,
    APITimeoutError,
    OpenAIError,
    RateLimitError,
)
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.common.config import (
    Environment,
    settings,
)
from src.common.logging import logger


# ── Circuit Breaker ───────────────────────────────────────────────────────────

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreaker:
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    last_failure_time: float = 0.0

    FAILURE_THRESHOLD: int = 3
    RECOVERY_TIMEOUT: float = 30.0

    def is_available(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.OPEN:
            if time.monotonic() - self.last_failure_time >= self.RECOVERY_TIMEOUT:
                self.state = CircuitState.HALF_OPEN
                return True
            return False
        # HALF_OPEN: allow one test request
        return True

    def record_success(self) -> None:
        self.state = CircuitState.CLOSED
        self.failure_count = 0

    def record_failure(self) -> None:
        self.failure_count += 1
        self.last_failure_time = time.monotonic()
        if self.failure_count >= self.FAILURE_THRESHOLD:
            self.state = CircuitState.OPEN


# ── LLM Registry ─────────────────────────────────────────────────────────────

class LLMRegistry:
    """Registry of available LLM models with pre-initialized instances."""

    LLMS: List[Dict[str, Any]] = [
        {
            "name": "gpt-5-mini",
            "llm": ChatOpenAI(
                model="gpt-5-mini",
                api_key=settings.OPENAI_API_KEY,
                max_tokens=settings.MAX_TOKENS,
                reasoning={"effort": "low"},
            ),
        },
        {
            "name": "gpt-5",
            "llm": ChatOpenAI(
                model="gpt-5",
                api_key=settings.OPENAI_API_KEY,
                max_tokens=settings.MAX_TOKENS,
                reasoning={"effort": "medium"},
            ),
        },
        {
            "name": "gpt-5-nano",
            "llm": ChatOpenAI(
                model="gpt-5-nano",
                api_key=settings.OPENAI_API_KEY,
                max_tokens=settings.MAX_TOKENS,
                reasoning={"effort": "minimal"},
            ),
        },
        {
            "name": "gpt-4o",
            "llm": ChatOpenAI(
                model="gpt-4o",
                temperature=settings.DEFAULT_LLM_TEMPERATURE,
                api_key=settings.OPENAI_API_KEY,
                max_tokens=settings.MAX_TOKENS,
                top_p=0.95 if settings.ENVIRONMENT == Environment.PRODUCTION else 0.8,
                presence_penalty=0.1 if settings.ENVIRONMENT == Environment.PRODUCTION else 0.0,
                frequency_penalty=0.1 if settings.ENVIRONMENT == Environment.PRODUCTION else 0.0,
            ),
        },
        {
            "name": "gpt-4o-mini",
            "llm": ChatOpenAI(
                model="gpt-4o-mini",
                temperature=settings.DEFAULT_LLM_TEMPERATURE,
                api_key=settings.OPENAI_API_KEY,
                max_tokens=settings.MAX_TOKENS,
                top_p=0.9 if settings.ENVIRONMENT == Environment.PRODUCTION else 0.8,
            ),
        },
    ]

    @classmethod
    def get(cls, model_name: str, **kwargs) -> BaseChatModel:
        model_entry = next((e for e in cls.LLMS if e["name"] == model_name), None)
        if not model_entry:
            available = [e["name"] for e in cls.LLMS]
            raise ValueError(f"model '{model_name}' not found in registry. available: {', '.join(available)}")

        if kwargs:
            logger.debug("creating_llm_with_custom_args", model_name=model_name, custom_args=list(kwargs.keys()))
            return ChatOpenAI(model=model_name, api_key=settings.OPENAI_API_KEY, **kwargs)

        logger.debug("using_default_llm_instance", model_name=model_name)
        return model_entry["llm"]

    @classmethod
    def get_all_names(cls) -> List[str]:
        return [e["name"] for e in cls.LLMS]

    @classmethod
    def get_model_at_index(cls, index: int) -> Dict[str, Any]:
        if 0 <= index < len(cls.LLMS):
            return cls.LLMS[index]
        return cls.LLMS[0]


# ── LLM Service ───────────────────────────────────────────────────────────────

class LLMService:
    """Service for managing LLM calls with Priority + Circuit Breaker + Weighted Random selection.

    DB resources are tried first (priority groups DESC, weighted random within group).
    Falls back to the hardcoded registry on full DB failure.

    Thread-safety note: call() and astream() are stateless with respect to the chosen
    LLM — each invocation selects a resource and passes it as a local variable, so
    concurrent calls do not interfere with each other.
    """

    # Class-level caches shared across all instances
    _resources_cache: List = []
    _resources_cache_ts: float = 0.0
    _RESOURCES_CACHE_TTL: float = 60.0

    # Circuit breaker state keyed by resource.id
    _circuit_breakers: Dict[int, CircuitBreaker] = {}

    def __init__(self):
        self._current_model_index: int = 0
        self._bound_tools: List = []

        # Keep a registry LLM reference for token-counting (prepare_messages) and get_llm()
        all_names = LLMRegistry.get_all_names()
        try:
            self._current_model_index = all_names.index(settings.DEFAULT_LLM_MODEL)
            self._default_llm: BaseChatModel = LLMRegistry.get(settings.DEFAULT_LLM_MODEL)
            logger.info(
                "llm_service_initialized",
                default_model=settings.DEFAULT_LLM_MODEL,
                model_index=self._current_model_index,
                total_models=len(all_names),
                environment=settings.ENVIRONMENT.value,
            )
        except (ValueError, Exception) as e:
            self._current_model_index = 0
            self._default_llm = LLMRegistry.LLMS[0]["llm"]
            logger.warning(
                "default_model_not_found_using_first",
                requested=settings.DEFAULT_LLM_MODEL,
                using=all_names[0] if all_names else "none",
                error=str(e),
            )

    # ── Circuit breaker helpers ───────────────────────────────────────────────

    def _get_circuit_breaker(self, resource_id: int) -> CircuitBreaker:
        if resource_id not in LLMService._circuit_breakers:
            LLMService._circuit_breakers[resource_id] = CircuitBreaker()
        return LLMService._circuit_breakers[resource_id]

    # ── Weighted selection ────────────────────────────────────────────────────

    def _select_by_weight(self, resources: List[LLMResource]) -> List[LLMResource]:
        """Order resources by priority DESC, with weighted random shuffle within each priority tier."""
        sorted_resources = sorted(resources, key=lambda r: r.priority, reverse=True)
        result: List[LLMResource] = []
        for _, group_iter in groupby(sorted_resources, key=lambda r: r.priority):
            group = list(group_iter)
            remaining = group[:]
            while remaining:
                weights = [max(r.weight, 1) for r in remaining]
                chosen = random.choices(remaining, weights=weights, k=1)[0]
                result.append(chosen)
                remaining.remove(chosen)
        return result

    # ── Candidate resolution ──────────────────────────────────────────────────

    def _resolve_candidates(
        self, db_resources: List[LLMResource], model_name: Optional[str]
    ) -> List[LLMResource]:
        """Filter and order DB resources for a given model_name request."""
        if model_name:
            # Primary: match on logical model_name field
            candidates = [r for r in db_resources if r.model_name == model_name]
            if not candidates:
                # Fallback: match on deployment_name or resource name
                candidates = [r for r in db_resources if (r.deployment_name or r.name) == model_name]
            if not candidates:
                logger.warning("requested_model_not_in_db", model_name=model_name)
                candidates = db_resources
        else:
            candidates = db_resources

        # Exclude resources whose circuit breaker is OPEN
        available = [r for r in candidates if self._get_circuit_breaker(r.id).is_available()]
        if not available:
            # All breakers open — reset to avoid full outage
            logger.warning("all_circuit_breakers_open_resetting", count=len(candidates), model_name=model_name)
            for r in candidates:
                self._get_circuit_breaker(r.id).record_success()
            available = candidates

        return self._select_by_weight(available)

    # ── LLM factory ───────────────────────────────────────────────────────────

    def _create_llm_from_resource(self, resource: LLMResource, **kwargs) -> BaseChatModel:
        """Create a ChatLiteLLM client from a DB resource config.

        LiteLLM unifies Azure / OpenAI / Anthropic / Google / Ollama under one interface.
        model_id format follows LiteLLM conventions:
          azure/<deployment_name>, anthropic/<model>, gemini/<model>, ollama/<model>, <model>
        """
        provider = resource.provider

        if provider == "azure":
            model_id = f"azure/{resource.deployment_name}"
        elif provider == "anthropic":
            model_id = f"anthropic/{resource.model_name or resource.name}"
        elif provider == "google":
            model_id = f"gemini/{resource.model_name or resource.name}"
        elif provider == "ollama":
            model_id = f"ollama/{resource.model_name or resource.name}"
        else:  # openai, other
            model_id = resource.model_name or resource.deployment_name or resource.name

        params: Dict[str, Any] = {
            "api_key": resource.api_key,
            "api_base": resource.api_base,
            "max_tokens": settings.MAX_TOKENS,
            "temperature": settings.DEFAULT_LLM_TEMPERATURE,
        }

        if provider == "azure" and resource.api_version:
            params["api_version"] = resource.api_version

        params.update(kwargs)

        llm: BaseChatModel = ChatLiteLLM(model=model_id, **params)

        if self._bound_tools:
            llm = llm.bind_tools(self._bound_tools)

        return llm

    # ── Cache ─────────────────────────────────────────────────────────────────

    async def _get_cached_resources(self) -> List[LLMResource]:
        """Return all LLM resources, re-fetching from DB at most once per TTL."""
        now = time.monotonic()
        if now - LLMService._resources_cache_ts > LLMService._RESOURCES_CACHE_TTL:
            try:
                all_resources = await database_service.get_llm_resources()
                LLMService._resources_cache = list(all_resources)
                LLMService._resources_cache_ts = now
            except Exception as e:
                logger.error("failed_to_fetch_llm_resources", error=str(e))
        return LLMService._resources_cache

    # ── Retry-wrapped invocation ──────────────────────────────────────────────

    @retry(
        stop=stop_after_attempt(settings.MAX_LLM_CALL_RETRIES),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((APITimeoutError, APIError)),
        before_sleep=before_sleep_log(logger, "WARNING"),
        reraise=True,
    )
    async def _invoke_with_retry(
        self, llm: BaseChatModel, messages: List[BaseMessage], config: Optional[Dict] = None
    ) -> BaseMessage:
        """Invoke a given LLM with automatic retry on transient errors.

        RateLimitError is NOT retried — the caller immediately fails over to the next resource.

        Args:
            llm: The LLM instance to invoke (passed explicitly — stateless).
            messages: Messages to send.
            config: Optional RunnableConfig (carries callbacks, e.g. Langfuse).

        Returns:
            BaseMessage response.
        """
        try:
            response = await llm.ainvoke(messages, config=config)
            logger.debug("llm_call_successful", message_count=len(messages))
            return response
        except RateLimitError as e:
            logger.warning("llm_rate_limit_immediate_failover", error_type=type(e).__name__, error=str(e))
            raise
        except (APITimeoutError, APIError) as e:
            logger.warning("llm_call_failed_retrying", error_type=type(e).__name__, error=str(e))
            raise
        except OpenAIError as e:
            logger.error("llm_call_failed", error_type=type(e).__name__, error=str(e))
            raise

    # ── Registry fallback ─────────────────────────────────────────────────────

    def _get_next_model_index(self) -> int:
        return (self._current_model_index + 1) % len(LLMRegistry.LLMS)

    def _switch_to_next_model(self) -> bool:
        try:
            next_index = self._get_next_model_index()
            next_entry = LLMRegistry.get_model_at_index(next_index)
            logger.warning(
                "switching_to_next_model",
                from_index=self._current_model_index,
                to_index=next_index,
                to_model=next_entry["name"],
            )
            self._current_model_index = next_index
            self._default_llm = next_entry["llm"]
            if self._bound_tools:
                self._default_llm = self._default_llm.bind_tools(self._bound_tools)
            logger.info("model_switched", new_model=next_entry["name"], new_index=next_index)
            return True
        except Exception as e:
            logger.error("model_switch_failed", error=str(e))
            return False

    async def _call_registry_with_fallback(
        self,
        messages: List[BaseMessage],
        model_name: Optional[str],
        config: Optional[Dict] = None,
        **model_kwargs,
    ) -> BaseMessage:
        """Try registry models in circular order, starting from model_name if given."""
        if model_name:
            try:
                llm = LLMRegistry.get(model_name, **model_kwargs)
                if self._bound_tools:
                    llm = llm.bind_tools(self._bound_tools)
                all_names = LLMRegistry.get_all_names()
                try:
                    self._current_model_index = all_names.index(model_name)
                except ValueError:
                    pass
                logger.info("using_requested_registry_model", model_name=model_name)
            except ValueError as e:
                logger.error("requested_model_not_found_in_registry", model_name=model_name, error=str(e))
                raise
        else:
            entry = LLMRegistry.get_model_at_index(self._current_model_index)
            llm = entry["llm"]
            if self._bound_tools:
                llm = llm.bind_tools(self._bound_tools)
            logger.info("using_registry_fallback", model=entry["name"])

        total_models = len(LLMRegistry.LLMS)
        models_tried = 0
        starting_index = self._current_model_index
        last_error: Optional[Exception] = None

        while models_tried < total_models:
            try:
                return await self._invoke_with_retry(llm, messages, config=config)
            except OpenAIError as e:
                last_error = e
                models_tried += 1
                current_name = LLMRegistry.LLMS[self._current_model_index]["name"]
                logger.error(
                    "registry_model_failed",
                    model=current_name,
                    models_tried=models_tried,
                    total_models=total_models,
                    error=str(e),
                )
                if models_tried >= total_models:
                    break
                if not self._switch_to_next_model():
                    break
                entry = LLMRegistry.get_model_at_index(self._current_model_index)
                llm = entry["llm"]
                if self._bound_tools:
                    llm = llm.bind_tools(self._bound_tools)

        logger.error(
            "all_registry_models_failed",
            models_tried=models_tried,
            starting_model=LLMRegistry.LLMS[starting_index]["name"],
        )
        raise RuntimeError(
            f"failed to get response from llm after trying {models_tried} models. last error: {str(last_error)}"
        )

    # ── Public API ────────────────────────────────────────────────────────────

    async def call(
        self,
        messages: List[BaseMessage],
        model_name: Optional[str] = None,
        config: Optional[Dict] = None,
        **model_kwargs,
    ) -> BaseMessage:
        """Call the LLM, selecting a resource via Priority + Circuit Breaker + Weighted Random.

        1. DB resources filtered by model_name → circuit-breaker → priority+weight order.
        2. Registry circular fallback if all DB resources fail or none exist.

        Args:
            messages: Messages to send.
            model_name: Logical model name (matches llm_resource.model_name).
            config: Optional RunnableConfig forwarded to the LLM (carries callbacks, e.g. Langfuse).
            **model_kwargs: Override default model config.

        Returns:
            BaseMessage response.

        Raises:
            RuntimeError: If all models fail.
        """
        all_resources = await self._get_cached_resources()
        db_resources = [r for r in all_resources if r.is_active]

        if db_resources:
            ordered = self._resolve_candidates(db_resources, model_name)
            last_error: Optional[Exception] = None

            for resource in ordered:
                cb = self._get_circuit_breaker(resource.id)
                try:
                    logger.info(
                        "using_db_resource",
                        resource_name=resource.name,
                        model_name=resource.model_name,
                        provider=resource.provider,
                        region=resource.region,
                        priority=resource.priority,
                        weight=resource.weight,
                        circuit_state=cb.state.value,
                    )
                    llm = self._create_llm_from_resource(resource, **model_kwargs)
                    response = await self._invoke_with_retry(llm, messages, config=config)
                    cb.record_success()
                    return response
                except OpenAIError as e:
                    cb.record_failure()
                    last_error = e
                    logger.warning(
                        "db_resource_failed",
                        resource=resource.name,
                        region=resource.region,
                        error=str(e),
                        circuit_state=cb.state.value,
                        failure_count=cb.failure_count,
                    )
                except Exception as e:
                    cb.record_failure()
                    last_error = e
                    logger.error(
                        "db_resource_error",
                        resource=resource.name,
                        region=resource.region,
                        error=str(e),
                        circuit_state=cb.state.value,
                    )

            logger.warning(
                "all_db_resources_failed_falling_back_to_registry",
                tried=len(ordered),
                error=str(last_error),
            )

        return await self._call_registry_with_fallback(messages, model_name, config=config, **model_kwargs)

    async def astream(
        self,
        messages: List[BaseMessage],
        model_name: Optional[str] = None,
        **model_kwargs,
    ):
        """Stream response from the LLM using the same selection logic as call().

        Args:
            messages: Messages to send.
            model_name: Logical model name to select.
            **model_kwargs: Override default model config.

        Yields:
            Response chunks.
        """
        all_resources = await self._get_cached_resources()
        db_resources = [r for r in all_resources if r.is_active]

        if db_resources:
            ordered = self._resolve_candidates(db_resources, model_name)

            for resource in ordered:
                cb = self._get_circuit_breaker(resource.id)
                try:
                    logger.info(
                        "stream_using_db_resource",
                        resource_name=resource.name,
                        model_name=resource.model_name,
                        provider=resource.provider,
                        region=resource.region,
                        circuit_state=cb.state.value,
                    )
                    llm = self._create_llm_from_resource(resource, **model_kwargs)
                    async for chunk in llm.astream(messages):
                        yield chunk
                    cb.record_success()
                    return
                except Exception as e:
                    cb.record_failure()
                    logger.warning(
                        "db_resource_stream_failed",
                        resource=resource.name,
                        region=resource.region,
                        error=str(e),
                        circuit_state=cb.state.value,
                    )

            logger.warning("all_db_resources_stream_failed_falling_back_to_registry")

        # Registry fallback for streaming
        if model_name:
            try:
                llm = LLMRegistry.get(model_name, **model_kwargs)
            except ValueError:
                llm = self._default_llm
        else:
            llm = self._default_llm

        if self._bound_tools:
            llm = llm.bind_tools(self._bound_tools)

        async for chunk in llm.astream(messages):
            yield chunk

    def get_llm(self) -> Optional[BaseChatModel]:
        """Return the current default registry LLM (used for token counting in prepare_messages)."""
        return self._default_llm

    def bind_tools(self, tools: List) -> "LLMService":
        """Bind tools to all LLM instances created by this service.

        Stores the tool list so that LLMs created from DB resources also receive tools.

        Args:
            tools: List of tools to bind.

        Returns:
            Self for method chaining.
        """
        self._bound_tools = tools
        if self._default_llm:
            self._default_llm = self._default_llm.bind_tools(tools)
            logger.debug("tools_bound_to_llm", tool_count=len(tools))
        return self


# Create global LLM service instance
llm_service = LLMService()
