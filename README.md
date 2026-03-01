# Agent Orchestration Platform (AOP)

**统一的多 Agent 编排平台** — 融合 MCO 执行引擎与 AAIF 工作流方法论

## 核心设计

```
工作流层 (AAIF)
项目评估 | 假设管理 | 团队配置 | 学习捕获 | 阶段协调
                    |
                    v
执行层 (MCO)
并行调度 | 结果聚合 | 去重 | 标准化输出 | 错误处理
                    |
    Claude Agent | Codex Agent | Gemini Agent | OpenCode | Qwen ...
```

## 特性

- **并行执行**: 多 Agent 同时工作，wall-clock 时间 约等于 最慢 Agent
- **结果标准化**: 统一的 Finding 结构，跨 Agent 去重
- **假设驱动**: 假设 - 验证 - 学习的迭代循环
- **学习捕获**: 自动捕获经验教训，持续改进
- **可扩展**: 适配器模式，轻松添加新 Agent
- **多 Provider 支持**: Claude、Codex、Gemini、OpenCode、Qwen

## 安装

```bash
# 从源码安装
git clone https://github.com/yourorg/aop.git
cd aop
pip install -e .
```

## 快速开始

### 1. 基础使用

```python
from aop.core.engine import ExecutionEngine
from aop.core.adapter import get_available_providers

# 检查可用的 providers
available = get_available_providers()
print(f"Available providers: {available}")

# 创建执行引擎
engine = ExecutionEngine(providers=["claude", "codex"])

# 执行代码审查
result = engine.execute(
    prompt="Review this code for security vulnerabilities",
    repo_root="/path/to/repo"
)

print(f"Success: {result.success}")
print(f"Duration: {result.duration_seconds:.2f}s")
print(f"Findings: {len(result.all_findings)}")
```

### 2. 假设驱动开发

```python
from aop.workflow.hypothesis import HypothesisManager
from aop.core.types import HypothesisState

# 创建假设管理器
hm = HypothesisManager()

# 创建新假设
h1 = hm.create(
    statement="添加 Redis 缓存可以将 API 响应时间降低 50%",
    validation_method="使用 wrk 进行压力测试对比",
    priority="quick_win"
)

print(f"Created hypothesis: {h1.hypothesis_id}")
print(f"State: {h1.state}")

# 更新假设状态
hm.update_state(h1.hypothesis_id, HypothesisState.VALIDATING)
hm.update_state(h1.hypothesis_id, HypothesisState.VALIDATED)

# 列出所有待验证的假设
pending = hm.list_by_state(HypothesisState.PENDING)
print(f"Pending hypotheses: {len(pending)}")
```

### 3. 项目评估与团队配置

```python
from aop.workflow.team import TeamOrchestrator
from aop.core.types import ProjectType

# 创建团队编排器
orchestrator = TeamOrchestrator()

# 评估项目复杂度
assessment = orchestrator.assess_project(
    problem_clarity="high",
    data_availability="high",
    tech_novelty="low",
    business_risk="medium"
)

print(f"Project type: {assessment.to_project_type()}")

# 获取团队配置
config = orchestrator.get_team_config()
print(f"Team agents: {config.agents}")

# 获取策略建议
strategy = orchestrator.get_strategy()
print(f"Approach: {strategy['approach']}")
```

### 4. 使用特定 Provider

```python
from aop.core.adapter import GeminiAdapter, QwenAdapter, OpenCodeAdapter
from aop.core.types import TaskInput

# 使用 Gemini
gemini = GeminiAdapter()
if gemini.detect().detected:
    result = gemini.run(TaskInput(
        task_id="gemini-review",
        prompt="Analyze this architecture diagram",
        timeout_seconds=300
    ))
    print(result.output)

# 使用 Qwen
qwen = QwenAdapter()
if qwen.detect().detected:
    result = qwen.run(TaskInput(
        task_id="qwen-analyze",
        prompt="分析这段代码的性能瓶颈"
    ))

# 使用 OpenCode
opencode = OpenCodeAdapter()
if opencode.detect().detected:
    result = opencode.run(TaskInput(
        task_id="opencode-task",
        prompt="Generate unit tests for this module"
    ))
```

### 5. 检测 Provider 状态

```python
from aop.core.adapter import get_adapter_registry

registry = get_adapter_registry()

for provider_id, adapter in registry.items():
    presence = adapter.detect()
    status = "OK" if presence.detected else "X"
    print(f"[{status}] {provider_id}")
```

## 架构

```
src/aop/
+-- core/               # 执行层
|   +-- adapter/       # Agent 适配器
|   |   +-- ClaudeAdapter
|   |   +-- CodexAdapter
|   |   +-- GeminiAdapter
|   |   +-- OpenCodeAdapter
|   |   +-- QwenAdapter
|   +-- engine/        # 执行引擎
|   +-- types/         # 类型定义
+-- workflow/          # 工作流层
|   +-- hypothesis/    # 假设管理
|   +-- learning/      # 学习捕获
|   +-- team/          # 团队配置
+-- cli/               # CLI 入口
```

## API 文档

### 核心类型 (core/types)

#### TaskInput
```python
@dataclass
class TaskInput:
    task_id: str           # 任务唯一标识
    prompt: str            # 任务提示
    repo_root: str = "."   # 代码仓库根目录
    timeout_seconds: int = 600  # 超时时间
```

#### TaskResult
```python
@dataclass
class TaskResult:
    task_id: str
    provider: ProviderId
    success: bool
    output: Optional[str]
    findings: List[NormalizedFinding]
    error: Optional[str]
    duration_seconds: float
```

#### Hypothesis
```python
@dataclass
class Hypothesis:
    hypothesis_id: str
    statement: str
    validation_method: str
    success_criteria: List[str]
    state: HypothesisState
    priority: str
```

### 适配器 (core/adapter)

#### ProviderAdapter Protocol
```python
class ProviderAdapter(Protocol):
    @property
    def id(self) -> ProviderId: ...
    
    def detect(self) -> ProviderPresence: ...
    def run(self, task: TaskInput) -> TaskResult: ...
```

#### ProviderPresence
```python
@dataclass
class ProviderPresence:
    provider: ProviderId
    detected: bool
    binary_path: Optional[str]
    version: Optional[str]
    auth_ok: bool = False
```

### 假设管理 (workflow/hypothesis)

#### HypothesisManager
```python
class HypothesisManager:
    def create(statement, validation_method, priority) -> Hypothesis
    def update_state(hid, state, confidence) -> Optional[Hypothesis]
    def list_by_state(state) -> List[Hypothesis]
```

### 团队编排 (workflow/team)

#### TeamOrchestrator
```python
class TeamOrchestrator:
    def assess_project(...) -> ComplexityAssessment
    def get_team_config() -> Optional[TeamConfig]
    def get_strategy() -> Dict[str, str]
```

## 运行测试

```bash
# 安装测试依赖
pip install pytest

# 运行所有测试
pytest

# 运行特定测试
pytest tests/core/test_types.py
pytest tests/workflow/test_hypothesis.py
pytest tests/workflow/test_team.py

# 显示覆盖率
pytest --cov=aop
```

## Provider 配置

### Claude (Anthropic)
```bash
npm install -g @anthropic-ai/claude-code
export ANTHROPIC_API_KEY=your-key
```

### Gemini (Google)
```bash
npm install -g @google/gemini-cli
# 或使用 gcloud
gcloud components install ai
gcloud auth login
```

### Qwen (阿里云通义千问)
```bash
# 方式1: DashScope API
pip install dashscope
export DASHSCOPE_API_KEY=your-key

# 方式2: Ollama 本地运行
ollama pull qwen2.5-coder
```

### OpenCode
```bash
npm install -g opencode
export OPENCODE_API_KEY=your-key
```

## License

MIT
