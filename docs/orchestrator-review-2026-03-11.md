# AOP Orchestrator 多 Provider 集成代码审查报告

**日期**: 2026-03-11
**审查范围**: multi_provider_orchestrator.py, opencode_orchestrator.py, __init__.py

---

## ✅ 做得好的地方

1. **架构设计清晰** - 抽象基类 `OrchestratorClient` 定义了统一接口，工厂函数 `create_orchestrator()` 使用便捷
2. **MultiProviderOrchestrator 设计亮点**
   - 任务类型到 Provider 的映射（`TASK_PROVIDER_MAP`）设计合理
   - 统计信息 `ProviderStats` 提供成功率、平均时间等关键指标
   - 故障转移逻辑完整，支持排除已失败的 provider
3. **OpenCodeOrchestrator 特色**
   - `AgentProfile` 支持自定义模型、系统提示、额外参数
   - `dispatch_async()` 实现了真正的并行调度，使用信号量控制并发
   - `_find_binary()` 跨平台查找二进制文件，考虑了 Windows 的 `.cmd` 扩展名
4. **文档字符串** - 主要方法都有清晰的 docstring，使用示例嵌入文档中

---

## ⚠️ 需要改进的地方

### 1. 严重的 API 不一致问题

**问题：`dispatch` 方法返回值类型不一致**

```python
# 基类 OrchestratorClient（base.py）
def dispatch(...) -> List[OrchestratorResponse]:
    ...

# MultiProviderOrchestrator（multi_provider_orchestrator.py）
async def dispatch(...) -> Dict[str, OrchestratorResponse]:
    # 返回 Dict[agent_name, response]
```

这违反了里氏替换原则，用户无法用统一的方式处理返回值。

**问题：参数命名不一致**

| Provider | 工作目录参数名 | 任务参数名 |
|----------|---------------|-----------|
| 基类 | `repo_root` | - |
| Claude Code | `repo_root` | `prompt` |
| OpenCode | `repo_root` | `prompt` |
| OpenClaw | `repo_root` | `prompt` |
| MultiProvider | `repo_root` (kwargs) | `prompt` |
| OrchestratorConfig | `working_directory` | - |

参数命名虽然在方法层面一致（`repo_root`），但与 `OrchestratorConfig.working_directory` 不一致，容易混淆。

### 2. 异步/同步混合问题

```python
# OpenCodeOrchestrator.dispatch() - 同步方法
def dispatch(...) -> List[OrchestratorResponse]:
    # 内部调用 asyncio.run() 或 ThreadPoolExecutor
    ...

# OpenCodeOrchestrator.dispatch_async() - 异步方法
async def dispatch_async(...) -> List[DispatchResult]:
    ...

# MultiProviderOrchestrator.dispatch() - 异步方法
async def dispatch(...) -> Dict[str, OrchestratorResponse]:
    ...
```

**问题**：
- `dispatch_async` 返回 `List[DispatchResult]`，而 `dispatch` 返回 `List[OrchestratorResponse]`
- 同步包装器逻辑复杂，在已有事件循环时使用 `ThreadPoolExecutor`，可能导致问题

### 3. 大量重复代码

以下代码在 3 个文件中完全重复：

```python
def _get_npm_global_paths():
    """获取 npm 全局路径（跨平台）"""
    paths = []
    if sys.platform == "win32":
        paths.append(Path.home() / "AppData" / "Roaming" / "npm")
    # ... 完全相同的实现


def _find_binary(binary_name: str) -> Optional[str]:
    """查找 CLI 二进制文件..."""
    # ... 完全相同的实现
```

### 4. 错误处理不一致

```python
# ClaudeCodeOrchestrator - 抛出异常
if result.returncode != 0:
    raise RuntimeError(f"Claude Code error: {result.stderr}")

# OpenClawOrchestrator - 返回包含错误的响应
return OrchestratorResponse(
    content=f"OpenClaw Gateway 错误: {str(e)}",
    finish_reason="error",
)

# MultiProviderOrchestrator - 先尝试 fallback，最终抛出异常
raise RuntimeError("No available provider for fallback")
```

### 5. 类型注解缺失

```python
# types.py - OrchestratorConfig
progress_callback: Optional[Callable[[str, str], None]] = None

# multi_provider_orchestrator.py - set_progress_callback
def set_progress_callback(self, callback: Callable[[str, str, str], None]) -> None:
    # 回调签名与 OrchestratorConfig 中定义不一致！
```

### 6. 潜在 Bug

**Bug 1：统计信息线程安全问题**

```python
# multi_provider_orchestrator.py
stats = self._stats.get(provider, ProviderStats())
stats.total_calls += 1  # 非原子操作
```

在并行执行时，多个协程可能同时修改统计数据，导致竞态条件。

**Bug 2：provider 实例创建后的异常未记录**

```python
def _get_provider(self, provider_type: str) -> Optional[OrchestratorClient]:
    try:
        # ... 创建 provider
    except Exception:
        return None  # 异常被吞掉，无日志
```

**Bug 3：OpenCodeOrchestrator._check_auth 逻辑问题**

```python
# 返回码非 0 但没有认证错误时，仍然认为可用
return True, "available"
```

这可能导致 CLI 实际不可用时误判为可用。

---

## 🔧 具体改进建议

### 1. 统一 API 设计

```python
# 建议：在基类中定义统一的返回类型
@dataclass
class DispatchResult:
    """统一的调度结果"""
    agent_name: str
    response: OrchestratorResponse
    success: bool
    error: Optional[str] = None

# 所有 dispatch 方法返回 Dict[str, DispatchResult] 或 List[DispatchResult]
```

### 2. 抽取公共工具函数

```python
# 创建 utils/binary_finder.py
def get_npm_global_paths() -> List[Path]:
    ...

def find_binary(binary_name: str) -> Optional[str]:
    ...

# 各 orchestrator 导入使用
from aop.utils.binary_finder import find_binary, get_npm_global_paths
```

### 3. 统一错误处理策略

```python
# 定义统一的错误处理装饰器
def handle_orchestrator_error(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            return OrchestratorResponse(
                content="",
                finish_reason="error",
                error=str(e),  # 添加 error 字段
            )
    return wrapper
```

或在 `OrchestratorResponse` 中添加 `error: Optional[str]` 字段。

### 4. 添加线程安全的统计

```python
import threading

class ProviderStats:
    def __init__(self):
        self._lock = threading.Lock()
        self._total_calls = 0
        # ...
    
    def record_call(self, success: bool, time_ms: float, error: Optional[str] = None):
        with self._lock:
            self._total_calls += 1
            # ...
```

### 5. 异步接口统一

```python
# 基类添加异步方法
class OrchestratorClient(ABC):
    @abstractmethod
    async def execute_async(self, prompt: str, repo_root: str = ".", **kwargs) -> OrchestratorResponse:
        """异步执行任务"""
        pass
    
    def execute(self, prompt: str, repo_root: str = ".", **kwargs) -> OrchestratorResponse:
        """同步执行任务（默认实现）"""
        return asyncio.run(self.execute_async(prompt, repo_root, **kwargs))
```

### 6. 完善类型注解和文档

```python
class OrchestratorClient(ABC):
    @abstractmethod
    def execute(
        self,
        prompt: str,
        repo_root: str = ".",
        target_paths: Optional[List[str]] = None,
        **kwargs: Any,  # 添加类型注解
    ) -> OrchestratorResponse:
        """
        执行任务
        
        Args:
            prompt: 任务描述
            repo_root: 仓库根目录（用于文件操作）
            target_paths: 限制操作的目标路径列表
            **kwargs: 额外参数，子类可扩展
            
        Returns:
            OrchestratorResponse: 包含执行结果
            
        Raises:
            OrchestratorError: 执行失败时抛出
        """
        pass
```

---

## 📝 使用体验对齐检查

| 检查项 | 状态 | 详情 |
|--------|------|------|
| **参数命名一致性** | ⚠️ 部分一致 | 方法参数统一用 `repo_root`，但 `OrchestratorConfig` 用 `working_directory` |
| **返回值一致性** | ❌ 不一致 | `dispatch` 返回值类型冲突（`List` vs `Dict`），`DispatchResult` vs `OrchestratorResponse` 混用 |
| **错误处理一致性** | ❌ 不一致 | 有的抛异常，有的返回错误响应，`finish_reason` 不统一 |
| **异步接口一致性** | ⚠️ 部分一致 | OpenCode 有 `dispatch_async`，其他没有；MultiProvider 全部是异步但基类是同步 |
| **OpenClaw sessions_spawn 集成** | ❌ 缺失 | `OpenClawOrchestrator` 只调用 Gateway API，未实现 `sessions_spawn` 语义 |

---

## 🎯 优先级建议

1. **高优先级**：修复 `dispatch` 返回值类型不一致问题
2. **高优先级**：抽取 `_find_binary` 等重复代码
3. **中优先级**：统一错误处理策略
4. **中优先级**：添加线程安全的统计
5. **低优先级**：完善类型注解和文档字符串

---

## 后续行动

- [ ] 创建 `DispatchResult` 统一类型
- [ ] 抽取 `aop/utils/binary_finder.py`
- [ ] 在 `OrchestratorResponse` 添加 `error` 字段
- [ ] 为 `ProviderStats` 添加线程安全支持
- [ ] 统一 `repo_root` / `working_directory` 命名
