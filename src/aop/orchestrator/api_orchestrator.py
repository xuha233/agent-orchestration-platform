"""
API 方式中枢

通过 API 调用 (Claude API, OpenAI API 等) 实现决策。
执行层委托给 ExecutionEngine。
"""

from __future__ import annotations

from typing import List, Dict, Any, Optional, TYPE_CHECKING

from .base import OrchestratorClient
from .types import (
    OrchestratorConfig,
    OrchestratorPresence,
    OrchestratorResponse,
    OrchestratorMode,
    OrchestratorCapability,
)

if TYPE_CHECKING:
    from ..llm import LLMClient, LLMMessage


class APIOrchestrator(OrchestratorClient):
    """
    API 方式中枢适配器

    决策层使用 LLM API，执行层委托给 ExecutionEngine。
    兼容现有的 LLMClient 实现。
    """

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        config: Optional[OrchestratorConfig] = None,
    ):
        self.config = config or OrchestratorConfig()
        self.llm = llm_client
        self._execution_engine = None

    @property
    def orchestrator_type(self) -> str:
        if self.llm:
            return f"api-{self.llm.provider.value}"
        return "api-unknown"

    @property
    def capabilities(self) -> List[OrchestratorCapability]:
        return [
            OrchestratorCapability.REQUIREMENT_CLARIFICATION,
            OrchestratorCapability.HYPOTHESIS_GENERATION,
            OrchestratorCapability.LEARNING_EXTRACTION,
            # 执行能力需要 ExecutionEngine
            OrchestratorCapability.TASK_EXECUTION,
            OrchestratorCapability.CODE_REVIEW,
            OrchestratorCapability.MULTI_AGENT_DISPATCH,
        ]

    def detect(self) -> OrchestratorPresence:
        """检测 API 中枢是否可用"""
        if not self.llm:
            return OrchestratorPresence(
                orchestrator_type=self.orchestrator_type,
                detected=False,
                reason="no_llm_client",
            )

        auth_ok = self.llm.validate_connection()

        return OrchestratorPresence(
            orchestrator_type=self.orchestrator_type,
            detected=True,
            auth_ok=auth_ok,
            capabilities=self.capabilities,
            reason="authenticated" if auth_ok else "not_authenticated",
        )

    def complete(
        self,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
        **kwargs
    ) -> OrchestratorResponse:
        """使用 LLM API 进行决策"""
        if not self.llm:
            raise RuntimeError("No LLM client configured")

        from ..llm import LLMMessage

        llm_messages = [
            LLMMessage(role=m["role"], content=m["content"])
            for m in messages
        ]

        response = self.llm.complete(
            messages=llm_messages,
            system=system,
            temperature=kwargs.get("temperature", self.config.temperature),
            max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
        )

        return OrchestratorResponse(
            content=response.content,
            model=response.model,
            orchestrator_type=self.orchestrator_type,
            mode=OrchestratorMode.DECISION,
            usage=response.usage,
            finish_reason=response.finish_reason,
            raw=response.raw or {},
        )

    def execute(
        self,
        prompt: str,
        repo_root: str = ".",
        target_paths: Optional[List[str]] = None,
        **kwargs
    ) -> OrchestratorResponse:
        """使用 ExecutionEngine 执行任务"""
        if self._execution_engine is None:
            from ..core.engine import ExecutionEngine
            self._execution_engine = ExecutionEngine(
                providers=self.config.sub_agents,
                default_timeout=self.config.timeout,
            )

        result = self._execution_engine.execute(
            prompt=prompt,
            repo_root=repo_root,
        )

        # 聚合结果
        outputs = []
        for pid, r in result.provider_results.items():
            if hasattr(r, 'output'):
                outputs.append(f"=== {pid} ===\n{r.output}")

        raw_data = {}
        if hasattr(result, '__dict__'):
            raw_data = {k: str(v) for k, v in result.__dict__.items()}

        return OrchestratorResponse(
            content="\n\n".join(outputs),
            model="multi-agent",
            orchestrator_type=self.orchestrator_type,
            mode=OrchestratorMode.EXECUTION,
            raw=raw_data,
        )

    def dispatch(
        self,
        prompt: str,
        agents: List[str],
        repo_root: str = ".",
        parallel: bool = True,
        **kwargs
    ) -> List[OrchestratorResponse]:
        """调度多个 Agent"""
        # 使用 ExecutionEngine 并行调度
        if self._execution_engine is None:
            from ..core.engine import ExecutionEngine
            self._execution_engine = ExecutionEngine(
                providers=agents,
                default_timeout=self.config.timeout,
            )

        result = self._execution_engine.execute(prompt=prompt, repo_root=repo_root)

        responses = []
        for pid, r in result.provider_results.items():
            responses.append(OrchestratorResponse(
                content=getattr(r, 'output', str(r)),
                model=pid,
                orchestrator_type=self.orchestrator_type,
                mode=OrchestratorMode.EXECUTION,
            ))

        return responses


__all__ = [
    "APIOrchestrator",
]
