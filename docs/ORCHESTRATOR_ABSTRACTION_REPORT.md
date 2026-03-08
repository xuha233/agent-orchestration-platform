# AOP 中枢 Agent 抽象层优化报告

> 目标：保留 OpenClaw 中枢能力，同时支持 Claude Code、OpenCode 作为中枢 Agent 调度智能体团队

## 一、现状分析

### 1.1 当前架构

```
┌─────────────────────────────────────────────────────────────┐
│                    AgentDriver (顶层入口)                    │
│  run_from_vague_description() → 全自动工作流                 │
└─────────────────────────┬───────────────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
    ┌───────────┐   ┌───────────┐   ┌───────────┐
    │ Clarifier │   │ Hypothesis│   │ Learning  │
    │ (需求澄清) │   │ Generator │   │ Extractor │
    └─────┬─────┘   └─────┬─────┘   └─────┬─────┘
          │               │               │
          └───────────────┼───────────────┘
                          ▼
              ┌─────────────────────┐
              │     LLMClient       │  ← 决策层 (API 调用)
              │  ┌───────────────┐  │
              │  │ ClaudeClient  │  │  (anthropic SDK)
              │  │ OpenAIClient  │  │  (openai SDK)  
              │  │ LocalLLMClient│  │  (ollama)
              │  └───────────────┘  │
              └─────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
    ┌───────────────────────────────────────────┐
    │            ExecutionEngine                │  ← 执行层 (CLI 调用)
    │  ┌─────────┐ ┌─────────┐ ┌─────────┐     │
    │  │ Claude  │ │ Codex   │ │ OpenCode│     │
    │  │ Code CLI│ │ CLI     │ │ CLI     │     │
    │  └─────────┘ └─────────┘ └─────────┘     │
    └───────────────────────────────────────────┘
```

### 1.2 问题诊断

**问题 1：决策层与执行层耦合不统一**

```python
# 当前决策层 (LLMClient) - 使用 API
class ClaudeClient(LLMClient):
    def complete(self, messages, **kwargs):
        response = self._client.messages.create(
            model=self.model,
            messages=api_messages,
            ...
        )
        return LLMResponse(content=response.content[0].text, ...)

# 当前执行层 (ExecutionEngine) - 使用 CLI
class ExecutionEngine:
    def execute(self, prompt, repo_root="."):
        adapter.run(TaskInput(prompt=prompt, ...))  # 调用 CLI
```

决策层用的是 **API 调用**，执行层用的是 **CLI 调用**，两者接口不统一。

**问题 2：缺失 Agent CLI 中枢适配器**

| 中枢类型 | 当前状态 | 决策方式 | 执行方式 |
|---------|---------|---------|---------|
| OpenClaw | 未集成 | - | - |
| Claude Code CLI | 仅执行层 | ❌ 无 | ✅ 有 |
| OpenCode CLI | 仅执行层 | ❌ 无 | ✅ 有 |
| Claude API | ✅ 有 | ✅ 有 | ❌ 无 |

**问题 3：工作流组件依赖 LLMClient 协议**

```python
# clarifier.py:58-65
class RequirementClarifier:
    def __init__(self, llm_client: LLMClient | None = None, ...):
        self.llm = llm_client  # 必须是 LLMClient 类型

# hypothesis_generator.py:76-82
class HypothesisGenerator:
    def __init__(self, llm_client: LLMClientProtocol | None = None, ...):
        self.llm = llm_client  # 必须实现 complete() 方法
```

所有决策组件都依赖 `LLMClient.complete(messages) -> LLMResponse` 接口。

---

## 二、优化方案

### 2.1 核心思路：统一中枢抽象

**目标架构：**

```
┌─────────────────────────────────────────────────────────────┐
│                    AgentDriver (顶层入口)                    │
└─────────────────────────┬───────────────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
    ┌───────────┐   ┌───────────┐   ┌───────────┐
    │ Clarifier │   │ Hypothesis│   │ Learning  │
    │           │   │ Generator │   │ Extractor │
    └─────┬─────┘   └─────┬─────┘   └─────┬─────┘
          │               │               │
          └───────────────┼───────────────┘
                          ▼
              ┌─────────────────────────────────────┐
              │      OrchestratorClient (新)        │  ← 统一中枢接口
              │  ┌─────────────────────────────────┐│
              │  │ complete(messages) -> Response  ││
              │  │ execute(prompt) -> Result       ││
              │  └─────────────────────────────────┘│
              └───────────────┬─────────────────────┘
                              │
       ┌──────────────────────┼──────────────────────┐
       ▼                      ▼                      ▼
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│ ClaudeCode  │      │  OpenCode   │      │  OpenClaw   │
│ Orchestrator│      │ Orchestrator│      │ Orchestrator│
│   (CLI)     │      │   (CLI)     │      │  (Client)   │
└─────────────┘      └─────────────┘      └─────────────┘
       │                      │                      │
       ▼                      ▼                      ▼
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│ Claude Code │      │  OpenCode   │      │  OpenClaw   │
│    CLI      │      │    CLI      │      │   Client    │
└─────────────┘      └─────────────┘      └─────────────┘
```

### 2.2 新增文件清单

```
src/aop/
├── orchestrator/                    # 新增目录
│   ├── __init__.py
│   ├── base.py                      # OrchestratorClient 抽象基类
│   ├── claude_code_orchestrator.py  # Claude Code CLI 中枢适配器
│   ├── opencode_orchestrator.py     # OpenCode CLI 中枢适配器
│   ├── openclaw_orchestrator.py     # OpenClaw 中枢适配器
│   ├── api_orchestrator.py          # API 方式中枢适配器 (兼容现有)
│   └── types.py                     # 中枢相关类型定义
├── llm/                             # 现有目录 (保留兼容)
│   └── ...                          # API 客户端保持不变
└── agent/
    ├── driver.py                    # 修改：使用 OrchestratorClient
    └── orchestrator.py              # 修改：统一入口
```

### 2.3 核心接口设计

#### 2.3.1 OrchestratorClient 基类

```python
# src/aop/orchestrator/base.py

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional, Callable
from pathlib import Path


class OrchestratorMode(Enum):
    """中枢模式"""
    DECISION = "decision"      # 仅决策，不执行
    EXECUTION = "execution"    # 仅执行，不决策
    FULL = "full"              # 决策 + 执行


class OrchestratorCapability(Enum):
    """中枢能力"""
    REQUIREMENT_CLARIFICATION = "requirement_clarification"
    HYPOTHESIS_GENERATION = "hypothesis_generation"
    TASK_EXECUTION = "task_execution"
    CODE_REVIEW = "code_review"
    LEARNING_EXTRACTION = "learning_extraction"
    MULTI_AGENT_DISPATCH = "multi_agent_dispatch"


@dataclass
class OrchestratorPresence:
    """中枢可用性检测结果"""
    orchestrator_type: str
    detected: bool
    binary_path: Optional[str] = None
    version: Optional[str] = None
    auth_ok: bool = False
    capabilities: List[OrchestratorCapability] = field(default_factory=list)
    reason: str = ""


@dataclass
class OrchestratorResponse:
    """中枢响应结果"""
    content: str
    model: str
    orchestrator_type: str
    mode: OrchestratorMode
    usage: Dict[str, int] = field(default_factory=dict)
    finish_reason: str = "stop"
    artifacts: List[str] = field(default_factory=list)
    raw: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OrchestratorConfig:
    """中枢配置"""
    mode: OrchestratorMode = OrchestratorMode.FULL
    working_directory: Optional[Path] = None
    timeout: int = 600
    max_retries: int = 3
    temperature: float = 0.7
    max_tokens: int = 4096
    
    # 多 Agent 调度配置
    sub_agents: List[str] = field(default_factory=lambda: ["claude", "codex"])
    parallel_execution: bool = True
    max_parallel: int = 5
    
    # 回调
    progress_callback: Optional[Callable[[str, str], None]] = None


class OrchestratorClient(ABC):
    """
    中枢 Agent 抽象基类
    
    统一接口，支持：
    - Claude Code CLI 作为中枢
    - OpenCode CLI 作为中枢
    - OpenClaw 作为中枢
    - API 方式作为中枢 (兼容现有)
    
    核心方法：
    - detect(): 检测中枢是否可用
    - complete(): 决策/规划类任务
    - execute(): 执行类任务
    - dispatch(): 多 Agent 调度
    """
    
    @property
    @abstractmethod
    def orchestrator_type(self) -> str:
        """中枢类型标识"""
        pass
    
    @property
    @abstractmethod
    def capabilities(self) -> List[OrchestratorCapability]:
        """中枢能力列表"""
        pass
    
    @abstractmethod
    def detect(self) -> OrchestratorPresence:
        """检测中枢是否可用"""
        pass
    
    @abstractmethod
    def complete(
        self,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
        **kwargs
    ) -> OrchestratorResponse:
        """
        执行决策/规划类任务
        
        Args:
            messages: 消息列表 [{"role": "user", "content": "..."}]
            system: 系统提示
            **kwargs: 额外参数
        
        Returns:
            OrchestratorResponse: 响应结果
        """
        pass
    
    @abstractmethod
    def execute(
        self,
        prompt: str,
        repo_root: str = ".",
        target_paths: Optional[List[str]] = None,
        **kwargs
    ) -> OrchestratorResponse:
        """
        执行任务
        
        Args:
            prompt: 任务描述
            repo_root: 仓库根目录
            target_paths: 目标路径
            **kwargs: 额外参数
        
        Returns:
            OrchestratorResponse: 执行结果
        """
        pass
    
    def dispatch(
        self,
        prompt: str,
        agents: List[str],
        repo_root: str = ".",
        parallel: bool = True,
        **kwargs
    ) -> List[OrchestratorResponse]:
        """
        调度多个子 Agent 执行任务
        
        Args:
            prompt: 任务描述
            agents: 子 Agent 列表
            repo_root: 仓库根目录
            parallel: 是否并行执行
            **kwargs: 额外参数
        
        Returns:
            List[OrchestratorResponse]: 各 Agent 的执行结果
        """
        # 默认实现：顺序或并行调用 execute()
        # 子类可以覆盖实现更高效的调度
        ...
    
    def validate_connection(self) -> bool:
        """验证连接是否正常"""
        try:
            response = self.complete(
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=10
            )
            return bool(response.content)
        except Exception:
            return False
    
    def supports(self, capability: OrchestratorCapability) -> bool:
        """检查是否支持某能力"""
        return capability in self.capabilities
```

#### 2.3.2 Claude Code 中枢适配器

```python
# src/aop/orchestrator/claude_code_orchestrator.py

"""
Claude Code CLI 作为中枢 Agent

通过 Claude Code CLI 实现决策和执行：
- complete(): 使用 ccr code --print 进行决策
- execute(): 使用 claude 进行代码修改
- dispatch(): 使用 claude 调度其他 Agent
"""

from __future__ import annotations

import json
import subprocess
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional

from .base import (
    OrchestratorClient,
    OrchestratorConfig,
    OrchestratorPresence,
    OrchestratorResponse,
    OrchestratorMode,
    OrchestratorCapability,
)


class ClaudeCodeOrchestrator(OrchestratorClient):
    """Claude Code CLI 中枢适配器"""
    
    BINARY_NAME = "claude"
    
    def __init__(self, config: Optional[OrchestratorConfig] = None):
        self.config = config or OrchestratorConfig()
        self._binary_path: Optional[str] = None
    
    @property
    def orchestrator_type(self) -> str:
        return "claude-code"
    
    @property
    def capabilities(self) -> List[OrchestratorCapability]:
        return [
            OrchestratorCapability.REQUIREMENT_CLARIFICATION,
            OrchestratorCapability.HYPOTHESIS_GENERATION,
            OrchestratorCapability.TASK_EXECUTION,
            OrchestratorCapability.CODE_REVIEW,
            OrchestratorCapability.LEARNING_EXTRACTION,
            OrchestratorCapability.MULTI_AGENT_DISPATCH,
        ]
    
    def detect(self) -> OrchestratorPresence:
        """检测 Claude Code CLI 是否可用"""
        binary = shutil.which(self.BINARY_NAME)
        if not binary:
            return OrchestratorPresence(
                orchestrator_type=self.orchestrator_type,
                detected=False,
                reason="binary_not_found",
            )
        
        self._binary_path = binary
        
        # 检测版本
        version = self._get_version()
        
        # 检测认证状态
        auth_ok, auth_reason = self._check_auth()
        
        return OrchestratorPresence(
            orchestrator_type=self.orchestrator_type,
            detected=True,
            binary_path=binary,
            version=version,
            auth_ok=auth_ok,
            capabilities=self.capabilities,
            reason=auth_reason,
        )
    
    def complete(
        self,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
        **kwargs
    ) -> OrchestratorResponse:
        """
        使用 Claude Code CLI 进行决策
        
        通过 `ccr code --print` 执行，不修改文件系统
        """
        prompt = self._build_prompt_from_messages(messages, system)
        
        cmd = [
            self.BINARY_NAME,
            "--print",
            "--output-format", "json",
        ]
        
        # 添加配置参数
        if kwargs.get("max_tokens"):
            cmd.extend(["--max-tokens", str(kwargs["max_tokens"])])
        
        result = subprocess.run(
            cmd,
            input=prompt,
            capture_output=True,
            text=True,
            timeout=self.config.timeout,
            cwd=self.config.working_directory or ".",
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"Claude Code error: {result.stderr}")
        
        return self._parse_response(result.stdout)
    
    def execute(
        self,
        prompt: str,
        repo_root: str = ".",
        target_paths: Optional[List[str]] = None,
        **kwargs
    ) -> OrchestratorResponse:
        """
        使用 Claude Code CLI 执行任务
        
        允许 Claude Code 修改文件系统
        """
        cmd = [
            self.BINARY_NAME,
            "--output-format", "json",
        ]
        
        # 添加权限配置
        if kwargs.get("permission_mode"):
            cmd.extend(["--permission-mode", kwargs["permission_mode"]])
        else:
            cmd.extend(["--permission-mode", "plan"])  # 默认计划模式
        
        # 添加目标路径限制
        if target_paths:
            cmd.extend(["--target-paths", ",".join(target_paths)])
        
        result = subprocess.run(
            cmd,
            input=prompt,
            capture_output=True,
            text=True,
            timeout=self.config.timeout,
            cwd=repo_root,
        )
        
        return self._parse_response(result.stdout)
    
    def dispatch(
        self,
        prompt: str,
        agents: List[str],
        repo_root: str = ".",
        parallel: bool = True,
        **kwargs
    ) -> List[OrchestratorResponse]:
        """
        Claude Code 作为中枢调度其他 Agent
        
        使用 Claude Code 的 MCP 或工具调用能力来调度其他 Agent
        """
        dispatch_prompt = f"""你是一个多 Agent 调度器。现在需要完成以下任务：

{prompt}

你需要调度以下 Agent 来完成这个任务：
{chr(10).join(f'- {agent}' for agent in agents)}

请分析任务，分配给合适的 Agent，并汇总结果。
"""
        
        response = self.execute(
            prompt=dispatch_prompt,
            repo_root=repo_root,
            **kwargs
        )
        
        return [response]
    
    def _build_prompt_from_messages(
        self,
        messages: List[Dict[str, str]],
        system: Optional[str] = None
    ) -> str:
        """从消息列表构建提示"""
        parts = []
        if system:
            parts.append(f"System: {system}")
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            parts.append(f"{role.capitalize()}: {content}")
        return "\n\n".join(parts)
    
    def _parse_response(self, stdout: str) -> OrchestratorResponse:
        """解析 Claude Code 输出"""
        try:
            data = json.loads(stdout)
            return OrchestratorResponse(
                content=data.get("content", stdout),
                model=data.get("model", "claude-unknown"),
                orchestrator_type=self.orchestrator_type,
                mode=OrchestratorMode.FULL,
                usage=data.get("usage", {}),
                finish_reason=data.get("stop_reason", "stop"),
                raw=data,
            )
        except json.JSONDecodeError:
            return OrchestratorResponse(
                content=stdout,
                model="claude-unknown",
                orchestrator_type=self.orchestrator_type,
                mode=OrchestratorMode.FULL,
            )
    
    def _get_version(self) -> Optional[str]:
        """获取 Claude Code 版本"""
        try:
            result = subprocess.run(
                [self.BINARY_NAME, "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return result.stdout.strip().split('\n')[0][:50]
        except Exception:
            pass
        return None
    
    def _check_auth(self) -> tuple[bool, str]:
        """检查认证状态"""
        try:
            result = subprocess.run(
                [self.BINARY_NAME, "--print", "test"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return True, "authenticated"
            elif "auth" in result.stderr.lower():
                return False, "not_authenticated"
            return True, "ok"
        except Exception as e:
            return False, str(e)
```

#### 2.3.3 OpenCode 中枢适配器

```python
# src/aop/orchestrator/opencode_orchestrator.py

"""
OpenCode CLI 作为中枢 Agent

通过 OpenCode CLI 实现决策和执行
"""

from __future__ import annotations

import json
import subprocess
import shutil
from typing import List, Dict, Any, Optional

from .base import (
    OrchestratorClient,
    OrchestratorConfig,
    OrchestratorPresence,
    OrchestratorResponse,
    OrchestratorMode,
    OrchestratorCapability,
)


class OpenCodeOrchestrator(OrchestratorClient):
    """OpenCode CLI 中枢适配器"""
    
    BINARY_NAME = "opencode"
    
    def __init__(self, config: Optional[OrchestratorConfig] = None):
        self.config = config or OrchestratorConfig()
        self._binary_path: Optional[str] = None
    
    @property
    def orchestrator_type(self) -> str:
        return "opencode"
    
    @property
    def capabilities(self) -> List[OrchestratorCapability]:
        return [
            OrchestratorCapability.REQUIREMENT_CLARIFICATION,
            OrchestratorCapability.HYPOTHESIS_GENERATION,
            OrchestratorCapability.TASK_EXECUTION,
            OrchestratorCapability.CODE_REVIEW,
            OrchestratorCapability.LEARNING_EXTRACTION,
            OrchestratorCapability.MULTI_AGENT_DISPATCH,
        ]
    
    def detect(self) -> OrchestratorPresence:
        """检测 OpenCode CLI 是否可用"""
        binary = shutil.which(self.BINARY_NAME)
        if not binary:
            return OrchestratorPresence(
                orchestrator_type=self.orchestrator_type,
                detected=False,
                reason="binary_not_found",
            )
        
        self._binary_path = binary
        version = self._get_version()
        auth_ok, auth_reason = self._check_auth()
        
        return OrchestratorPresence(
            orchestrator_type=self.orchestrator_type,
            detected=True,
            binary_path=binary,
            version=version,
            auth_ok=auth_ok,
            capabilities=self.capabilities,
            reason=auth_reason,
        )
    
    def complete(
        self,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
        **kwargs
    ) -> OrchestratorResponse:
        """使用 OpenCode CLI 进行决策"""
        prompt = self._build_prompt_from_messages(messages, system)
        
        cmd = [self.BINARY_NAME, "--print"]
        
        result = subprocess.run(
            cmd,
            input=prompt,
            capture_output=True,
            text=True,
            timeout=self.config.timeout,
            cwd=self.config.working_directory or ".",
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"OpenCode error: {result.stderr}")
        
        return OrchestratorResponse(
            content=result.stdout,
            model="opencode",
            orchestrator_type=self.orchestrator_type,
            mode=OrchestratorMode.FULL,
        )
    
    def execute(
        self,
        prompt: str,
        repo_root: str = ".",
        target_paths: Optional[List[str]] = None,
        **kwargs
    ) -> OrchestratorResponse:
        """使用 OpenCode CLI 执行任务"""
        cmd = [self.BINARY_NAME]
        
        result = subprocess.run(
            cmd,
            input=prompt,
            capture_output=True,
            text=True,
            timeout=self.config.timeout,
            cwd=repo_root,
        )
        
        return OrchestratorResponse(
            content=result.stdout,
            model="opencode",
            orchestrator_type=self.orchestrator_type,
            mode=OrchestratorMode.EXECUTION,
        )
    
    def _build_prompt_from_messages(
        self,
        messages: List[Dict[str, str]],
        system: Optional[str] = None
    ) -> str:
        parts = []
        if system:
            parts.append(f"System: {system}")
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            parts.append(f"{role.capitalize()}: {content}")
        return "\n\n".join(parts)
    
    def _get_version(self) -> Optional[str]:
        try:
            result = subprocess.run(
                [self.BINARY_NAME, "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return result.stdout.strip().split('\n')[0][:50]
        except Exception:
            pass
        return None
    
    def _check_auth(self) -> tuple[bool, str]:
        try:
            result = subprocess.run(
                [self.BINARY_NAME, "--print", "test"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return True, "authenticated"
            return False, "not_authenticated"
        except Exception as e:
            return False, str(e)
```

#### 2.3.4 OpenClaw 中枢适配器

```python
# src/aop/orchestrator/openclaw_orchestrator.py

"""
OpenClaw 作为中枢 Agent

通过 OpenClaw 客户端实现决策和执行。
OpenClaw 可以通过其 MCP 或 API 接口调用其他 Agent。
"""

from __future__ import annotations

from typing import List, Dict, Any, Optional

from .base import (
    OrchestratorClient,
    OrchestratorConfig,
    OrchestratorPresence,
    OrchestratorResponse,
    OrchestratorMode,
    OrchestratorCapability,
)


class OpenClawOrchestrator(OrchestratorClient):
    """OpenClaw 中枢适配器"""
    
    def __init__(self, config: Optional[OrchestratorConfig] = None):
        self.config = config or OrchestratorConfig()
        # TODO: 初始化 OpenClaw 客户端连接
        # self._client = openclaw.Client(...)
    
    @property
    def orchestrator_type(self) -> str:
        return "openclaw"
    
    @property
    def capabilities(self) -> List[OrchestratorCapability]:
        return [
            OrchestratorCapability.REQUIREMENT_CLARIFICATION,
            OrchestratorCapability.HYPOTHESIS_GENERATION,
            OrchestratorCapability.TASK_EXECUTION,
            OrchestratorCapability.CODE_REVIEW,
            OrchestratorCapability.LEARNING_EXTRACTION,
            OrchestratorCapability.MULTI_AGENT_DISPATCH,
        ]
    
    def detect(self) -> OrchestratorPresence:
        """检测 OpenClaw 是否可用"""
        # TODO: 实现 OpenClaw 检测逻辑
        # 1. 检查 OpenClaw 服务是否运行
        # 2. 检查连接状态
        # 3. 获取版本信息
        
        return OrchestratorPresence(
            orchestrator_type=self.orchestrator_type,
            detected=False,  # 待实现
            reason="openclaw_integration_pending",
        )
    
    def complete(
        self,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
        **kwargs
    ) -> OrchestratorResponse:
        """通过 OpenClaw 进行决策"""
        # TODO: 调用 OpenClaw API
        # response = self._client.chat(messages, system=system)
        # return OrchestratorResponse(...)
        raise NotImplementedError("OpenClaw integration pending")
    
    def execute(
        self,
        prompt: str,
        repo_root: str = ".",
        target_paths: Optional[List[str]] = None,
        **kwargs
    ) -> OrchestratorResponse:
        """通过 OpenClaw 执行任务"""
        # TODO: 调用 OpenClaw 执行 API
        raise NotImplementedError("OpenClaw integration pending")
    
    def dispatch(
        self,
        prompt: str,
        agents: List[str],
        repo_root: str = ".",
        parallel: bool = True,
        **kwargs
    ) -> List[OrchestratorResponse]:
        """
        OpenClaw 调度多 Agent
        
        OpenClaw 原生支持多 Agent 调度，可以直接使用其调度能力
        """
        # TODO: 使用 OpenClaw 的多 Agent 调度能力
        # response = self._client.dispatch(prompt, agents, parallel=parallel)
        # return [self._parse_response(r) for r in response]
        raise NotImplementedError("OpenClaw integration pending")
```

#### 2.3.5 API 中枢适配器 (兼容现有)

```python
# src/aop/orchestrator/api_orchestrator.py

"""
API 方式中枢

通过 API 调用 (Claude API, OpenAI API 等) 实现决策。
执行层委托给 ExecutionEngine。
"""

from __future__ import annotations

from typing import List, Dict, Any, Optional, TYPE_CHECKING

from .base import (
    OrchestratorClient,
    OrchestratorConfig,
    OrchestratorPresence,
    OrchestratorResponse,
    OrchestratorMode,
    OrchestratorCapability,
)

if TYPE_CHECKING:
    from ..llm import LLMClient


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
        
        # 延迟导入避免循环依赖
        from ..core.engine import ExecutionEngine
        self._execution_engine: Optional[ExecutionEngine] = None
    
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
            raw=response.raw,
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
        
        return OrchestratorResponse(
            content="\n\n".join(outputs),
            model="multi-agent",
            orchestrator_type=self.orchestrator_type,
            mode=OrchestratorMode.EXECUTION,
            raw={"result": result.__dict__ if hasattr(result, '__dict__') else str(result)},
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
```

#### 2.3.6 OrchestratorClient 工厂

```python
# src/aop/orchestrator/__init__.py

"""
Orchestrator Layer - 中枢 Agent 抽象层

统一接口支持多种中枢类型：
- Claude Code CLI
- OpenCode CLI
- OpenClaw
- API 方式 (Claude API, OpenAI API, etc.)
"""

from __future__ import annotations

from typing import Dict, List, Optional, TYPE_CHECKING

from .base import (
    OrchestratorClient,
    OrchestratorConfig,
    OrchestratorPresence,
    OrchestratorResponse,
    OrchestratorMode,
    OrchestratorCapability,
)
from .claude_code_orchestrator import ClaudeCodeOrchestrator
from .opencode_orchestrator import OpenCodeOrchestrator
from .openclaw_orchestrator import OpenClawOrchestrator
from .api_orchestrator import APIOrchestrator

if TYPE_CHECKING:
    from ..llm import LLMClient


# 中枢类型注册表
ORCHESTRATOR_REGISTRY: Dict[str, type] = {
    "claude-code": ClaudeCodeOrchestrator,
    "opencode": OpenCodeOrchestrator,
    "openclaw": OpenClawOrchestrator,
    "api": APIOrchestrator,
}


def create_orchestrator(
    orchestrator_type: str,
    config: Optional[OrchestratorConfig] = None,
    llm_client: Optional[LLMClient] = None,
) -> OrchestratorClient:
    """
    创建中枢客户端
    
    Args:
        orchestrator_type: 中枢类型 (claude-code, opencode, openclaw, api)
        config: 中枢配置
        llm_client: LLM 客户端 (仅 api 类型需要)
    
    Returns:
        OrchestratorClient 实例
    """
    if orchestrator_type == "api":
        return APIOrchestrator(llm_client=llm_client, config=config)
    
    orchestrator_cls = ORCHESTRATOR_REGISTRY.get(orchestrator_type)
    if not orchestrator_cls:
        raise ValueError(f"Unknown orchestrator type: {orchestrator_type}")
    
    return orchestrator_cls(config=config)


def discover_orchestrators() -> Dict[str, OrchestratorPresence]:
    """
    发现所有可用的中枢
    
    Returns:
        Dict[类型, 检测结果]
    """
    results = {}
    
    for orch_type, orch_cls in ORCHESTRATOR_REGISTRY.items():
        if orch_type == "api":
            # API 类型需要 LLMClient，跳过自动检测
            continue
        
        try:
            orchestrator = orch_cls()
            results[orch_type] = orchestrator.detect()
        except Exception as e:
            results[orch_type] = OrchestratorPresence(
                orchestrator_type=orch_type,
                detected=False,
                reason=f"error: {str(e)}",
            )
    
    return results


def get_available_orchestrators() -> List[str]:
    """获取所有可用的中枢类型列表"""
    discovered = discover_orchestrators()
    return [
        orch_type
        for orch_type, presence in discovered.items()
        if presence.detected and presence.auth_ok
    ]


def get_best_orchestrator() -> str:
    """
    获取最佳可用的中枢
    
    优先级: claude-code > opencode > openclaw
    """
    available = get_available_orchestrators()
    priority = ["claude-code", "opencode", "openclaw"]
    
    for orch_type in priority:
        if orch_type in available:
            return orch_type
    
    return "api"  # 回退到 API 方式


__all__ = [
    # 基类和类型
    "OrchestratorClient",
    "OrchestratorConfig",
    "OrchestratorPresence",
    "OrchestratorResponse",
    "OrchestratorMode",
    "OrchestratorCapability",
    # 具体实现
    "ClaudeCodeOrchestrator",
    "OpenCodeOrchestrator",
    "OpenClawOrchestrator",
    "APIOrchestrator",
    # 工厂函数
    "create_orchestrator",
    "discover_orchestrators",
    "get_available_orchestrators",
    "get_best_orchestrator",
    # 注册表
    "ORCHESTRATOR_REGISTRY",
]
```

---

## 三、AgentDriver 改造

### 3.1 改造后的 AgentDriver

```python
# src/aop/agent/driver.py (改造版)

"""
AgentDriver - 全自动 Agent 团队驱动器

支持多种中枢类型：
- Claude Code CLI
- OpenCode CLI
- OpenClaw
- API 方式
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Callable, Dict, Any, Optional, Literal

from .types import (
    SprintContext,
    SprintState,
    SprintResult,
    ClarifiedRequirement,
    ExtractedLearning,
)
from .clarifier import RequirementClarifier
from .hypothesis_generator import HypothesisGenerator
from .validator import AutoValidator
from .learning_extractor import LearningExtractor
from .persistence import SprintPersistence
from .scheduler import TaskScheduler
from ..core.engine import ExecutionEngine
from ..orchestrator import (
    OrchestratorClient,
    OrchestratorConfig,
    create_orchestrator,
    get_best_orchestrator,
    discover_orchestrators,
)


@dataclass
class AgentDriverConfig:
    """AgentDriver 配置"""
    # 中枢配置 (新增)
    orchestrator_type: Literal["claude-code", "opencode", "openclaw", "api", "auto"] = "auto"
    orchestrator_config: Optional[OrchestratorConfig] = None
    
    # LLM 配置 (API 模式使用)
    llm_provider: Literal["claude", "openai", "local"] = "claude"
    llm_model: str = "claude-sonnet-4-20250514"
    llm_api_key: Optional[str] = None

    # 执行配置
    providers: List[str] = field(default_factory=lambda: ["claude", "codex"])
    default_timeout: int = 600
    max_parallel_tasks: int = 5

    # 流程配置
    max_clarification_rounds: int = 3
    auto_execute: bool = True
    parallel_execution: bool = True
    auto_validate: bool = True
    auto_learn: bool = True

    # 存储配置
    storage_path: Optional[Path] = None
    progress_callback: Optional[Callable[[str, str], None]] = None


class AgentDriver:
    """
    全自动 Agent 团队驱动器

    支持多种中枢类型，从模糊需求到交付，全自动执行。

    使用示例:
        # 自动选择最佳中枢
        driver = AgentDriver()
        result = driver.run_from_vague_description("帮我做一个电商系统")

        # 指定 Claude Code 作为中枢
        driver = AgentDriver(config=AgentDriverConfig(orchestrator_type="claude-code"))
        result = driver.run_from_vague_description("帮我做一个电商系统")

        # 指定 OpenCode 作为中枢
        driver = AgentDriver(config=AgentDriverConfig(orchestrator_type="opencode"))

        # 使用 API 方式作为中枢
        driver = AgentDriver(config=AgentDriverConfig(orchestrator_type="api"))
    """

    def __init__(
        self,
        config: Optional[AgentDriverConfig] = None,
        orchestrator: Optional[OrchestratorClient] = None,
    ):
        self.config = config or AgentDriverConfig()
        self.context: Optional[SprintContext] = None

        # 初始化中枢
        if orchestrator:
            self.orchestrator = orchestrator
        else:
            self.orchestrator = self._create_orchestrator()

        # 初始化组件
        # Clarifier 和 HypothesisGenerator 现在使用 OrchestratorClient
        self.clarifier = RequirementClarifier(orchestrator_client=self.orchestrator)
        self.hypothesis_generator = HypothesisGenerator(orchestrator_client=self.orchestrator)
        self.validator = AutoValidator()
        self.learning_extractor = LearningExtractor()

        # 存储路径
        self.storage_path = self.config.storage_path or Path(".aop")
        self.persistence = SprintPersistence(str(self.storage_path / "sprints"))

    def _create_orchestrator(self) -> OrchestratorClient:
        """创建中枢客户端"""
        orch_type = self.config.orchestrator_type

        if orch_type == "auto":
            orch_type = get_best_orchestrator()

        orch_config = self.config.orchestrator_config or OrchestratorConfig(
            sub_agents=self.config.providers,
            timeout=self.config.default_timeout,
            max_parallel=self.config.max_parallel_tasks,
        )

        return create_orchestrator(
            orchestrator_type=orch_type,
            config=orch_config,
        )

    def discover_available_orchestrators(self) -> Dict[str, Any]:
        """发现所有可用的中枢"""
        return discover_orchestrators()

    def get_orchestrator_info(self) -> Dict[str, Any]:
        """获取当前中枢信息"""
        presence = self.orchestrator.detect()
        return {
            "type": presence.orchestrator_type,
            "detected": presence.detected,
            "version": presence.version,
            "auth_ok": presence.auth_ok,
            "capabilities": [c.value for c in presence.capabilities],
        }

    def run_from_vague_description(
        self,
        vague_input: str,
        clarifications_callback: Optional[Callable[[str], str]] = None,
    ) -> SprintResult:
        """
        从模糊描述开始全自动执行
        
        工作流程:
        1. 需求澄清 - 使用中枢进行决策
        2. 假设生成 - 使用中枢生成假设
        3. 任务分解 - 构建任务依赖图
        4. 并行执行 - 使用中枢调度子 Agent 执行
        5. 自动验证 - 验证结果
        6. 学习提取 - 提取经验教训
        """
        # ... (实现与原版类似，但使用 self.orchestrator 代替 self.llm)
        pass

    def _clarify_requirement(
        self,
        vague_input: str,
        callback: Optional[Callable[[str], str]],
    ) -> ClarifiedRequirement:
        """使用中枢澄清需求"""
        return self.clarifier.clarify(
            vague_input,
            interactive_callback=callback,
        )

    def _generate_hypotheses(self, requirement: ClarifiedRequirement) -> List[Any]:
        """使用中枢生成假设"""
        return self.hypothesis_generator.generate(requirement)

    def _execute_tasks(self) -> List[Dict[str, Any]]:
        """使用中枢调度执行任务"""
        if not self.context or not self.context.hypotheses:
            return []

        # 使用中枢的 dispatch 能力
        results = []
        for hypothesis in self.context.hypotheses:
            prompt = getattr(hypothesis, 'validation_method', str(hypothesis))
            
            responses = self.orchestrator.dispatch(
                prompt=prompt,
                agents=self.config.providers,
                repo_root=".",
                parallel=self.config.parallel_execution,
            )
            
            for resp in responses:
                results.append({
                    "hypothesis_id": getattr(hypothesis, 'hypothesis_id', ''),
                    "success": True,
                    "output": resp.content,
                    "model": resp.model,
                    "orchestrator_type": resp.orchestrator_type,
                })

        return results
```

### 3.2 改造 Clarifier 支持双模式

```python
# src/aop/agent/clarifier.py (改造版关键部分)

class RequirementClarifier:
    """
    需求澄清器
    
    支持两种模式:
    1. OrchestratorClient 模式 - 使用 CLI Agent 作为中枢
    2. LLMClient 模式 - 使用 API 作为中枢 (兼容现有)
    """

    def __init__(
        self,
        orchestrator_client: Optional[OrchestratorClient] = None,
        llm_client: Optional[LLMClient] = None,  # 兼容现有
        config: Optional[ClarificationConfig] = None,
    ):
        self.orchestrator = orchestrator_client
        self.llm = llm_client
        self.config = config or ClarificationConfig()
        self.clarification_history: List[QAPair] = []

    def _has_decision_engine(self) -> bool:
        """检查是否有决策引擎"""
        return self.orchestrator is not None or self.llm is not None

    def _call_decision_engine(
        self,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
    ) -> str:
        """调用决策引擎"""
        if self.orchestrator:
            response = self.orchestrator.complete(
                messages=messages,
                system=system,
            )
            return response.content
        elif self.llm:
            llm_messages = [LLMMessage(role=m["role"], content=m["content"]) for m in messages]
            response = self.llm.complete(messages=llm_messages, system=system)
            return response.content
        else:
            raise RuntimeError("No decision engine available")
```

---

## 四、CLI 改造

### 4.1 新增 orchestrator 命令组

```python
# src/aop/cli/orchestrator.py

"""
中枢 Agent CLI 命令
"""

import click
from pathlib import Path

try:
    from rich.console import Console
    from rich.table import Table
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

from ..orchestrator import (
    discover_orchestrators,
    get_available_orchestrators,
    get_best_orchestrator,
    create_orchestrator,
    OrchestratorConfig,
)


@click.group()
def orchestrator():
    """
    中枢 Agent 命令组

    管理和配置中枢 Agent。

    \b
    示例:
      aop orchestrator doctor
      aop orchestrator list
      aop orchestrator use claude-code
    """
    pass


@orchestrator.command("doctor")
@click.option("--json", "output_json", is_flag=True, help="JSON 输出")
def doctor(output_json: bool):
    """检测所有可用的中枢"""
    results = discover_orchestrators()

    if output_json:
        import json
        output = {
            orch_type: {
                "detected": p.detected,
                "version": p.version,
                "auth_ok": p.auth_ok,
                "capabilities": [c.value for c in p.capabilities],
                "reason": p.reason,
            }
            for orch_type, p in results.items()
        }
        click.echo(json.dumps(output, indent=2))
        return

    if HAS_RICH:
        console = Console()
        table = Table(title="Orchestrator Status")
        table.add_column("Type")
        table.add_column("Detected")
        table.add_column("Version")
        table.add_column("Auth")
        table.add_column("Capabilities")

        for orch_type, presence in results.items():
            table.add_row(
                orch_type,
                "✅" if presence.detected else "❌",
                presence.version or "-",
                "✅" if presence.auth_ok else "❌",
                ", ".join(c.value for c in presence.capabilities[:3]) + ("..." if len(presence.capabilities) > 3 else ""),
            )

        console.print(table)
    else:
        click.echo("Orchestrator Status:")
        for orch_type, presence in results.items():
            status = "✅" if presence.detected and presence.auth_ok else "❌"
            click.echo(f"  {status} {orch_type}: {presence.reason}")


@orchestrator.command("list")
def list_orchestrators():
    """列出所有可用的中枢"""
    available = get_available_orchestrators()
    best = get_best_orchestrator()

    click.echo("Available Orchestrators:")
    for orch_type in available:
        marker = " (recommended)" if orch_type == best else ""
        click.echo(f"  - {orch_type}{marker}")

    if not available:
        click.echo("  No orchestrators available. Install one of:")
        click.echo("    - Claude Code: npm install -g @anthropic-ai/claude-code")
        click.echo("    - OpenCode: npm install -g opencode")


@orchestrator.command("use")
@click.argument("orchestrator_type", type=click.Choice(["claude-code", "opencode", "openclaw", "api", "auto"]))
@click.option("--project", "-p", default=".", help="Project directory")
def use(orchestrator_type: str, project: str):
    """设置项目使用的中枢类型"""
    config_path = Path(project) / ".aop" / "config.yaml"

    import yaml
    config = {}
    if config_path.exists():
        config = yaml.safe_load(config_path.read_text()) or {}

    config["orchestrator"] = {"type": orchestrator_type}

    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(yaml.dump(config))

    click.echo(f"✅ Set orchestrator to: {orchestrator_type}")
```

### 4.2 修改 agent run 命令

```python
# src/aop/cli/agent.py (改造版关键部分)

@agent.command("run")
@click.argument("description", required=False)
@click.option("--interactive", "-i", is_flag=True, help="交互式追问模式")
@click.option("--orchestrator", "-o", "orchestrator_type", 
              default="auto",
              type=click.Choice(["claude-code", "opencode", "openclaw", "api", "auto"]),
              help="中枢类型")
@click.option("--providers", "-P", default="claude,codex", help="子 Agent 列表")
@click.option("--storage", "-s", default=".aop", help="存储路径")
@click.option("--resume", "-r", default=None, help="恢复指定冲刺ID")
def run_agent(description: str, interactive: bool, orchestrator_type: str, 
              providers: str, storage: str, resume: str):
    """
    启动全自动 Agent 团队

    \b
    示例:
      # 使用自动选择的中枢
      aop agent run "做一个电商系统"

      # 使用 Claude Code 作为中枢
      aop agent run -o claude-code "做一个电商系统"

      # 使用 OpenCode 作为中枢
      aop agent run -o opencode "做一个电商系统"

      # 使用 API 方式作为中枢
      aop agent run -o api "做一个电商系统"
    """
    config = AgentDriverConfig(
        orchestrator_type=orchestrator_type,
        providers=providers.split(","),
        storage_path=Path(storage),
        auto_execute=True,
        parallel_execution=True,
        auto_validate=True,
        auto_learn=True,
    )

    driver = AgentDriver(config)

    # 显示中枢信息
    if HAS_RICH:
        info = driver.get_orchestrator_info()
        console.print(f"[cyan]Using orchestrator: {info['type']}[/cyan]")
        if info.get('version'):
            console.print(f"[dim]Version: {info['version']}[/dim]")

    # ... 后续逻辑
```

---

## 五、实施计划

### 5.1 阶段一：核心抽象层 (1-2 周)

| 任务 | 优先级 | 预估时间 |
|-----|-------|---------|
| 创建 `orchestrator/` 目录结构 | P0 | 0.5 天 |
| 实现 `OrchestratorClient` 基类 | P0 | 1 天 |
| 实现 `ClaudeCodeOrchestrator` | P0 | 1.5 天 |
| 实现 `OpenCodeOrchestrator` | P0 | 1 天 |
| 实现 `APIOrchestrator` (兼容现有) | P0 | 1 天 |
| 编写单元测试 | P0 | 1 天 |

### 5.2 阶段二：组件改造 (1 周)

| 任务 | 优先级 | 预估时间 |
|-----|-------|---------|
| 改造 `RequirementClarifier` | P0 | 0.5 天 |
| 改造 `HypothesisGenerator` | P0 | 0.5 天 |
| 改造 `AgentDriver` | P0 | 1 天 |
| 改造 `LearningExtractor` | P1 | 0.5 天 |
| 更新配置系统 | P1 | 0.5 天 |

### 5.3 阶段三：CLI 和文档 (0.5 周)

| 任务 | 优先级 | 预估时间 |
|-----|-------|---------|
| 新增 `aop orchestrator` 命令组 | P1 | 0.5 天 |
| 修改 `aop agent run` 命令 | P1 | 0.5 天 |
| 更新 README 文档 | P1 | 0.5 天 |
| 添加使用示例 | P2 | 0.5 天 |

### 5.4 阶段四：OpenClaw 集成 (后续)

| 任务 | 优先级 | 预估时间 |
|-----|-------|---------|
| 实现 `OpenClawOrchestrator` | P1 | 2 天 |
| OpenClaw API 对接 | P1 | 1 天 |
| 集成测试 | P1 | 1 天 |

---

## 六、使用示例

### 6.1 基本使用

```bash
# 查看可用中枢
aop orchestrator doctor

# 自动选择最佳中枢运行
aop agent run "做一个电商系统"

# 指定 Claude Code 作为中枢
aop agent run -o claude-code "做一个电商系统"

# 指定 OpenCode 作为中枢
aop agent run -o opencode "做一个电商系统"

# 使用 API 方式 (需要配置 API Key)
aop agent run -o api "做一个电商系统"
```

### 6.2 Python API

```python
from aop.agent import AgentDriver, AgentDriverConfig
from aop.orchestrator import create_orchestrator, OrchestratorConfig

# 方式1: 自动选择中枢
driver = AgentDriver()
result = driver.run_from_vague_description("做一个电商系统")

# 方式2: 指定 Claude Code 作为中枢
driver = AgentDriver(config=AgentDriverConfig(
    orchestrator_type="claude-code"
))

# 方式3: 自定义配置
orchestrator = create_orchestrator(
    "claude-code",
    config=OrchestratorConfig(
        mode="full",
        sub_agents=["claude", "codex", "gemini"],
        parallel_execution=True,
    )
)
driver = AgentDriver(orchestrator=orchestrator)

# 方式4: 检查中枢状态
info = driver.get_orchestrator_info()
print(f"Using: {info['type']}, Version: {info['version']}")
```

---

## 七、风险评估

### 7.1 技术风险

| 风险 | 影响 | 缓解措施 |
|-----|-----|---------|
| CLI 输出格式不稳定 | 中 | 实现健壮的输出解析，支持多种格式 |
| 中枢认证失败 | 高 | 优雅降级到其他可用中枢 |
| 并行调度冲突 | 中 | 实现任务锁和状态同步机制 |
| OpenClaw API 变更 | 低 | 抽象层隔离，便于适配 |

### 7.2 兼容性风险

| 风险 | 影响 | 缓解措施 |
|-----|-----|---------|
| 现有 LLMClient 接口变更 | 高 | 保留 LLMClient 接口，APIOrchestrator 作为适配层 |
| 配置文件格式变更 | 中 | 实现配置迁移脚本 |
| CLI 参数变更 | 低 | 保留旧参数作为别名 |

---

## 八、总结

本优化方案通过抽象出 `OrchestratorClient` 中枢接口层，实现了：

1. **统一接口** - 所有中枢 (Claude Code, OpenCode, OpenClaw, API) 都通过 `OrchestratorClient` 接口调用
2. **自动发现** - 自动检测可用中枢，选择最佳方案
3. **灵活切换** - 用户可以通过 CLI 参数或配置文件轻松切换中枢
4. **向后兼容** - 现有的 `LLMClient` API 调用方式通过 `APIOrchestrator` 保持兼容
5. **扩展性强** - 新增中枢只需实现 `OrchestratorClient` 接口

核心改造点：
- 新增 `src/aop/orchestrator/` 目录
- 改造 `AgentDriver`, `RequirementClarifier`, `HypothesisGenerator` 支持双模式
- 新增 `aop orchestrator` CLI 命令组
- 更新配置系统支持中枢选择
