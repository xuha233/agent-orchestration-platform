"""
OpenCode CLI 作为中枢 Agent

通过 OpenCode CLI 实现决策和执行
"""

from __future__ import annotations

import asyncio
import os
import sys
import platform
import subprocess
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any, Optional, TypedDict

from .base import OrchestratorClient
from .types import (
    OrchestratorConfig,
    OrchestratorPresence,
    OrchestratorResponse,
    OrchestratorMode,
    OrchestratorCapability,
)


class AgentProfile(TypedDict, total=False):
    """Agent 配置文件"""
    model: str  # 模型名称，如 "deepseek/deepseek-chat"
    system_prompt: str  # 系统提示
    temperature: float  # 温度参数
    max_tokens: int  # 最大 token 数
    extra_args: List[str]  # 额外的命令行参数


@dataclass
class DispatchResult:
    """单个 Agent 的调度结果"""
    agent_name: str
    success: bool
    response: Optional[OrchestratorResponse]
    error: Optional[str] = None


# Windows 上常见的 npm 全局安装路径
def _get_npm_global_paths():
    """获取 npm 全局路径（跨平台）"""
    paths = []
    if sys.platform == "win32":
        paths.append(Path.home() / "AppData" / "Roaming" / "npm")
    else:
        paths.extend([
            Path("/usr/local/bin"),
            Path("/usr/bin"),
        ])
    # 通用路径
    npm_global = Path.home() / ".npm-global" / "bin"
    if npm_global.exists():
        paths.append(npm_global)
    return paths

NPM_GLOBAL_PATHS = _get_npm_global_paths()


def _find_binary(binary_name: str) -> Optional[str]:
    """
    查找 CLI 二进制文件，支持 Windows 的 .cmd/.bat 扩展名

    在 Windows 上，npm 安装的 CLI 通常是 .cmd 文件，
    shutil.which() 在某些环境下可能无法正确找到它们。
    """
    # 首先尝试标准查找
    result = shutil.which(binary_name)
    if result:
        return result

    # 在 Windows 上额外检查常见路径
    if platform.system() == "Windows":
        # 检查 PATHEXT 环境变量指定的扩展名
        pathext = os.environ.get("PATHEXT", ".COM;.EXE;.BAT;.CMD" if sys.platform == "win32" else "").split(";") if sys.platform == "win32" else [""]

        for npm_path in NPM_GLOBAL_PATHS:
            if not npm_path.exists():
                continue
            for ext in pathext:
                candidate = npm_path / f"{binary_name}{ext}"
                if candidate.exists():
                    return str(candidate)

        # 直接检查 .cmd 扩展名（npm 最常见的情况）
        for npm_path in NPM_GLOBAL_PATHS:
            if not npm_path.exists():
                continue
            candidate = npm_path / f"{binary_name}.cmd"
            if candidate.exists():
                return str(candidate)

    return None


class OpenCodeOrchestrator(OrchestratorClient):
    """OpenCode CLI 中枢适配器"""

    BINARY_NAME = "opencode"

    def __init__(self, config: Optional[OrchestratorConfig] = None):
        self.config = config or OrchestratorConfig()
        self._binary_path: Optional[str] = None
        # 默认的 Agent profiles
        self._agent_profiles: Dict[str, AgentProfile] = {
            "reviewer": {
                "model": "anthropic/claude-sonnet-4",
                "system_prompt": "你是一个代码审查专家，专注于代码质量、安全性和最佳实践。",
            },
            "tester": {
                "model": "deepseek/deepseek-chat",
                "system_prompt": "你是一个测试专家，专注于编写测试用例和验证功能。",
            },
            "architect": {
                "model": "anthropic/claude-sonnet-4",
                "system_prompt": "你是一个架构师，专注于系统设计和代码组织。",
            },
            "fixer": {
                "model": "deepseek/deepseek-chat",
                "system_prompt": "你是一个修复专家，专注于解决 bug 和代码问题。",
            },
        }

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

    def set_agent_profile(self, name: str, profile: AgentProfile) -> None:
        """设置或更新 Agent profile"""
        self._agent_profiles[name] = profile

    def get_agent_profile(self, name: str) -> Optional[AgentProfile]:
        """获取 Agent profile"""
        return self._agent_profiles.get(name)

    def detect(self) -> OrchestratorPresence:
        """检测 OpenCode CLI 是否可用"""
        binary = _find_binary(self.BINARY_NAME)
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

        binary = self._binary_path or self.BINARY_NAME
        cmd = [binary, "--print"]

        cwd = str(self.config.working_directory) if self.config.working_directory else "."

        result = subprocess.run(
            cmd,
            input=prompt,
            capture_output=True,
            text=True,
            timeout=self.config.timeout,
            cwd=cwd,
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
        binary = self._binary_path or self.BINARY_NAME
        cmd = [binary]

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

    async def dispatch_async(
        self,
        prompt: str,
        agents: List[str],
        repo_root: str = ".",
        parallel: bool = True,
        agent_profiles: Optional[Dict[str, AgentProfile]] = None,
        **kwargs
    ) -> List[DispatchResult]:
        """
        并行调度多个子 Agent 执行任务

        Args:
            prompt: 任务描述
            agents: 子 Agent 名称列表，如 ["reviewer", "tester"]
            repo_root: 仓库根目录
            parallel: 是否并行执行（默认 True）
            agent_profiles: 自定义 Agent profiles（可选，会与默认 profiles 合并）
            **kwargs: 额外参数
                - timeout_per_agent: 每个 Agent 的超时时间（秒）
                - max_concurrent: 最大并发数

        Returns:
            List[DispatchResult]: 各 Agent 的执行结果

        Example:
            orchestrator = OpenCodeOrchestrator()

            # 使用默认 profiles
            results = await orchestrator.dispatch_async(
                prompt="Review the authentication module",
                agents=["reviewer", "tester"],
                repo_root="/path/to/repo"
            )

            # 使用自定义 profiles
            custom_profiles = {
                "security-auditor": {
                    "model": "anthropic/claude-sonnet-4",
                    "system_prompt": "Focus on security vulnerabilities"
                }
            }
            results = await orchestrator.dispatch_async(
                prompt="Audit security",
                agents=["security-auditor"],
                agent_profiles=custom_profiles
            )
        """
        # 合并自定义 profiles
        effective_profiles = {**self._agent_profiles}
        if agent_profiles:
            effective_profiles.update(agent_profiles)

        # 获取配置
        timeout_per_agent = kwargs.get("timeout_per_agent", self.config.timeout)
        max_concurrent = kwargs.get("max_concurrent", self.config.max_parallel)

        if parallel:
            return await self._dispatch_parallel(
                prompt=prompt,
                agents=agents,
                repo_root=repo_root,
                profiles=effective_profiles,
                timeout=timeout_per_agent,
                max_concurrent=max_concurrent,
            )
        else:
            return await self._dispatch_sequential(
                prompt=prompt,
                agents=agents,
                repo_root=repo_root,
                profiles=effective_profiles,
                timeout=timeout_per_agent,
            )

    async def _dispatch_parallel(
        self,
        prompt: str,
        agents: List[str],
        repo_root: str,
        profiles: Dict[str, AgentProfile],
        timeout: int,
        max_concurrent: int,
    ) -> List[DispatchResult]:
        """并行执行多个 Agent"""
        semaphore = asyncio.Semaphore(max_concurrent)

        async def run_with_semaphore(agent: str) -> DispatchResult:
            async with semaphore:
                return await self._run_single_agent(
                    agent=agent,
                    prompt=prompt,
                    repo_root=repo_root,
                    profile=profiles.get(agent),
                    timeout=timeout,
                )

        # 并行启动所有任务
        tasks = [run_with_semaphore(agent) for agent in agents]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理结果，将异常转换为 DispatchResult
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, DispatchResult):
                final_results.append(result)
            elif isinstance(result, Exception):
                final_results.append(DispatchResult(
                    agent_name=agents[i],
                    success=False,
                    response=None,
                    error=f"Exception: {str(result)}"
                ))

        return final_results

    async def _dispatch_sequential(
        self,
        prompt: str,
        agents: List[str],
        repo_root: str,
        profiles: Dict[str, AgentProfile],
        timeout: int,
    ) -> List[DispatchResult]:
        """顺序执行多个 Agent"""
        results = []
        for agent in agents:
            result = await self._run_single_agent(
                agent=agent,
                prompt=prompt,
                repo_root=repo_root,
                profile=profiles.get(agent),
                timeout=timeout,
            )
            results.append(result)
        return results

    async def _run_single_agent(
        self,
        agent: str,
        prompt: str,
        repo_root: str,
        profile: Optional[AgentProfile],
        timeout: int,
    ) -> DispatchResult:
        """
        执行单个 Agent 任务

        使用 asyncio.create_subprocess_exec 启动 opencode 进程，
        实现非阻塞的并行执行。
        """
        binary = self._binary_path or self.BINARY_NAME

        # 构建命令
        cmd = [binary]

        # 添加模型参数
        if profile and "model" in profile:
            cmd.extend(["--model", profile["model"]])

        # 添加额外参数
        if profile and "extra_args" in profile:
            cmd.extend(profile["extra_args"])

        # 构建完整的 prompt
        full_prompt = prompt
        if profile and "system_prompt" in profile:
            full_prompt = f"[System: {profile['system_prompt']}]\n\n{prompt}"

        try:
            # 使用 asyncio 创建子进程
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=repo_root,
            )

            # 发送输入并等待完成
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(input=full_prompt.encode()),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return DispatchResult(
                    agent_name=agent,
                    success=False,
                    response=None,
                    error=f"Timeout after {timeout}s"
                )

            stdout_str = stdout.decode() if stdout else ""
            stderr_str = stderr.decode() if stderr else ""

            if process.returncode != 0:
                return DispatchResult(
                    agent_name=agent,
                    success=False,
                    response=None,
                    error=f"Exit code {process.returncode}: {stderr_str}"
                )

            # 构建响应
            model = profile.get("model", "opencode") if profile else "opencode"
            response = OrchestratorResponse(
                content=stdout_str,
                model=model,
                orchestrator_type=self.orchestrator_type,
                mode=OrchestratorMode.EXECUTION,
                raw={"agent": agent, "profile": profile}
            )

            return DispatchResult(
                agent_name=agent,
                success=True,
                response=response
            )

        except Exception as e:
            return DispatchResult(
                agent_name=agent,
                success=False,
                response=None,
                error=str(e)
            )

    # 保留同步版本的 dispatch 方法（兼容基类）
    def dispatch(
        self,
        prompt: str,
        agents: List[str],
        repo_root: str = ".",
        parallel: bool = True,
        **kwargs
    ) -> List[OrchestratorResponse]:
        """
        调度多个子 Agent 执行任务（同步版本）

        注意：这是同步包装器，内部使用 asyncio.run()。
        如果在异步环境中，建议直接使用 dispatch_async()。
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop is not None:
            # 已在异步环境中，使用 run_until_complete
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    self.dispatch_async(prompt, agents, repo_root, parallel, **kwargs)
                )
                results = future.result()
        else:
            # 不在异步环境中，直接运行
            results = asyncio.run(
                self.dispatch_async(prompt, agents, repo_root, parallel, **kwargs)
            )

        # 将 DispatchResult 转换为 OrchestratorResponse
        responses = []
        for result in results:
            if result.success and result.response:
                responses.append(result.response)
            else:
                # 失败时返回错误响应
                responses.append(OrchestratorResponse(
                    content="",
                    model="opencode",
                    orchestrator_type=self.orchestrator_type,
                    mode=OrchestratorMode.EXECUTION,
                    raw={
                        "agent": result.agent_name,
                        "success": False,
                        "error": result.error
                    }
                ))

        return responses

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

    def _get_version(self) -> Optional[str]:
        """获取 OpenCode 版本"""
        if not self._binary_path:
            return None
        try:
            result = subprocess.run(
                [self._binary_path, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return result.stdout.strip().split('\'n')[0][:50]
        except Exception:
            pass
        return None

    def _check_auth(self) -> tuple[bool, str]:
        """
        检查认证状态

        通过运行一个简单的测试命令来验证 CLI 是否可用。
        注意：这个检查不仅检查认证，还验证 CLI 是否能正常工作。
        """
        if not self._binary_path:
            return False, "binary_not_found"

        try:
            # 使用 --print 运行一个简单的 prompt 来验证
            result = subprocess.run(
                [self._binary_path, "--print", "Say 'ok'"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                # 成功执行，CLI 可用
                return True, "authenticated"

            # 检查是否是认证相关的错误
            stderr_lower = result.stderr.lower()
            stdout_lower = result.stdout.lower()

            # 明确的认证错误模式
            auth_error_patterns = [
                "not authenticated",
                "authentication required",
                "please run",
                "login required",
                "no api key",
                "needs auth",
            ]

            for pattern in auth_error_patterns:
                if pattern in stderr_lower or pattern in stdout_lower:
                    return False, "not_authenticated"

            # 非 0 返回码但没有明确的认证错误
            # 可能是网络问题、API 限制等，暂时认为可用
            return True, "available"

        except subprocess.TimeoutExpired:
            return False, "timeout"
        except Exception as e:
            return False, f"error: {str(e)[:50]}"


__all__ = [
    "OpenCodeOrchestrator",
    "AgentProfile",
    "DispatchResult",
]
