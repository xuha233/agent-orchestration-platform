# AOP 改进方案

> 基于 Anthropic 多智能体研究系统经验与 AOP 现有架构对比分析

---

## 1. 概述

本文档基于 Anthropic 发布的《How we built our multi-agent research system》文章，结合 AOP (Agent Orchestration Platform) 现有架构，提出系统性改进方案。

### 1.1 Anthropic 核心经验总结

| 核心经验 | 说明 | 价值 |
|---------|------|------|
| 编排器-工人模式 | 主 Agent 规划调度，子 Agent 执行具体任务 | 清晰职责分离 |
| 子代理委托格式 | 明确目标、输出格式、工具指导、边界、努力预算 | 减少90%错误 |
| 并行工具调用 | 同时调用多个工具，减少90%时间 | 大幅提升效率 |
| LLM-as-Judge | 用 LLM 评估输出质量 | 自动化评估 |
| 人机协作评估 | 人类审查关键决策，AI 处理常规检查 | 质量与效率平衡 |
| 断点续传 | 任务中断后可恢复 | 可靠性保障 |

### 1.2 AOP 现有架构优势

```
┌─────────────────────────────────────────────────────────────┐
│                    AOP 架构概览                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  AgentOrchestrator ──────────────────────────────────┐      │
│       │                                               │      │
│       ├── RequirementClarifier (需求澄清)             │      │
│       ├── HypothesisGenerator (假设生成)             │      │
│       ├── AutoValidator (自动验证)                   │      │
│       ├── LearningExtractor (学习提取)               │      │
│       └── SprintPersistence (持久化)                 │      │
│                                                       │      │
│  OrchestratorClient (中枢抽象) ───────────────────────┤      │
│       ├── ClaudeCodeOrchestrator                     │      │
│       ├── OpenCodeOrchestrator                       │      │
│       ├── OpenClawOrchestrator                       │      │
│       └── APIOrchestrator                            │      │
│                                                       │      │
│  HypothesisGraph (依赖图) ────────────────────────────┤      │
│       └── 拓扑排序、并行执行                          │      │
│                                                       │      │
│  工作流状态机 ─────────────────────────────────────────┤      │
│       INITIALIZED → CLARIFIED → HYPOTHESES_GENERATED │      │
│       → TASKS_DECOMPOSED → EXECUTED → VALIDATED      │      │
│       → COMPLETED/FAILED                             │      │
│                                                       │      │
└─────────────────────────────────────────────────────────────┘
```

**已实现的优势：**
- ✅ 编排器-工人模式（OrchestratorClient 抽象）
- ✅ 并行执行（ThreadPoolExecutor）
- ✅ 假设依赖图（HypothesisGraph）
- ✅ 持久化和恢复（SprintPersistence）
- ✅ 状态机管理（SprintState）

---

## 2. 架构改进点

### 2.1 子代理委托格式标准化

**问题**：AOP 现有的 `GeneratedHypothesis` 已包含部分字段，但未在任务执行时充分使用。

**Anthropic 推荐格式**：

```python
@dataclass
class SubagentTask:
    """子代理任务 - Anthropic 推荐格式"""
    
    # 核心字段
    objective: str           # 明确目标：这个任务要解决什么问题
    output_format: str       # 输出格式：期望的输出结构
    tools_guidance: str      # 工具指导：建议使用的工具和方法
    boundaries: str          # 任务边界：不要做什么
    effort_budget: int       # 努力预算：预估工具调用次数
    
    # 上下文字段
    context: str             # 上下文：为什么需要这个任务
    success_criteria: List[str]  # 成功标准
    
    # 元数据
    task_id: str
    hypothesis_id: str
    priority: str            # quick_win / deep_dive / strategic
```

**改进方案**：

```python
# 1. 扩展 GeneratedHypothesis，强化任务委托字段
@dataclass
class GeneratedHypothesis:
    # ... 现有字段 ...
    
    # 强化的子代理委托字段
    objective: str = ""                    # 明确目标
    output_format: str = ""                # 输出格式
    tools_guidance: str = ""               # 工具指导
    boundaries: str = ""                   # 任务边界
    effort_budget: int = 10                # 努力预算
    
    # 新增字段
    context: str = ""                      # 任务上下文
    verification_steps: List[str] = field(default_factory=list)  # 验证步骤
    rollback_plan: str = ""                # 回滚计划

# 2. Prompt 模板优化
SUBAGENT_TASK_PROMPT = """
## 任务目标
{objective}

## 输出格式
{output_format}

## 工具指导
{tools_guidance}

## 任务边界
{boundaries}

## 努力预算
预计工具调用次数: ~{effort_budget} 次

## 成功标准
{success_criteria}

## 验证步骤
{verification_steps}
"""
```

### 2.2 编排器职责强化

**问题**：当前 Orchestrator 职责不够清晰，缺少任务前验证和超时接管。

**改进后的编排器职责**：

```
┌─────────────────────────────────────────────────────────────┐
│                Enhanced Orchestrator 职责                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Phase 1: 规划阶段                                          │
│  ├── 需求澄清（自动追问 + 交互式澄清）                       │
│  ├── 假设生成（多角度技术假设）                              │
│  ├── 依赖分析（构建依赖图）                                  │
│  └── 风险评估（识别高风险假设）                              │
│                                                             │
│  Phase 2: 验证阶段 ⭐ 新增                                   │
│  ├── 任务前验证（检查代码是否已存在）                        │
│  ├── 环境检查（工具、依赖是否可用）                          │
│  ├── 超时估算（基于任务复杂度）                              │
│  └── 工作目录验证（确保在正确路径）                          │
│                                                             │
│  Phase 3: 执行阶段                                          │
│  ├── 并行调度（基于依赖图的并行执行）                        │
│  ├── 进度监控（实时跟踪子代理状态）                          │
│  ├── 动态超时（根据进度调整超时）                            │
│  └── 错误处理（失败重试、降级策略）                          │
│                                                             │
│  Phase 4: 接管阶段 ⭐ 新增                                   │
│  ├── 超时接管（子代理超时后 Orchestrator 接管）              │
│  ├── 失败恢复（检查完成度，决定下一步）                      │
│  ├── 冲突解决（多代理修改冲突）                              │
│  └── 降级执行（复杂任务简化执行）                            │
│                                                             │
│  Phase 5: 评估阶段                                          │
│  ├── 自动验证（基于成功标准）                                │
│  ├── LLM-as-Judge（质量评估）                               │
│  ├── 集成测试（跨假设验证）                                  │
│  └── 学习提取（经验总结）                                    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**代码实现**：

```python
class EnhancedOrchestrator:
    """增强版编排器"""
    
    async def orchestrate(self, requirement: str) -> SprintResult:
        # Phase 1: 规划
        clarified = await self._clarify(requirement)
        hypotheses = await self._generate_hypotheses(clarified)
        dependency_graph = self._build_dependency_graph(hypotheses)
        
        # Phase 2: 验证 ⭐ 新增
        validated_hypotheses = await self._pre_validate(hypotheses)
        
        # Phase 3: 执行
        execution_plan = self._create_execution_plan(validated_hypotheses)
        results = await self._execute_with_monitoring(execution_plan)
        
        # Phase 4: 接管处理 ⭐ 新增
        results = await self._handle_timeouts_and_failures(results)
        
        # Phase 5: 评估
        validated = await self._validate_results(results)
        learnings = await self._extract_learnings(results)
        
        return SprintResult(...)
    
    async def _pre_validate(self, hypotheses: List[GeneratedHypothesis]) -> List[ValidatedHypothesis]:
        """任务前验证"""
        validated = []
        for h in hypotheses:
            # 检查代码是否已存在
            existing_code = await self._check_existing_code(h.statement)
            if existing_code:
                h.skip_reason = "相关代码已存在"
                h.skip_files = existing_code
                continue
            
            # 估算超时
            h.estimated_timeout = self._estimate_timeout(h)
            
            # 验证环境
            env_ok = await self._verify_environment(h.tools_guidance)
            if not env_ok:
                h.requires_setup = True
            
            validated.append(h)
        return validated
    
    async def _handle_timeouts_and_failures(self, results: List[ExecutionResult]) -> List[ExecutionResult]:
        """处理超时和失败"""
        for r in results:
            if r.status == "timeout":
                # 检查任务是否实际完成
                if await self._check_task_completed(r):
                    r.status = "completed"
                    r.completion_source = "post_timeout_verification"
                else:
                    # Orchestrator 接管
                    r = await self._take_over_task(r)
        return results
```

### 2.3 任务前验证系统

**问题**：PurifyAI 项目中发现，子 Agent 超时后检查发现任务已完成，浪费 ~1.6M tokens。

**解决方案**：

```python
class PreTaskValidator:
    """任务前验证器"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.keyword_extractor = KeywordExtractor()
    
    async def validate(self, hypothesis: GeneratedHypothesis) -> ValidationResult:
        """
        验证任务是否需要执行
        
        Returns:
            ValidationResult:
                - should_execute: 是否需要执行
                - reason: 原因
                - existing_files: 已存在的相关文件
                - estimated_effort: 预估工作量
        """
        # 1. 提取关键词
        keywords = self.keyword_extractor.extract(hypothesis.statement)
        
        # 2. 搜索相关代码
        existing_files = await self._search_existing_code(keywords)
        
        # 3. 分析相似度
        if existing_files:
            similarity = await self._calculate_similarity(hypothesis, existing_files)
            if similarity > 0.8:
                return ValidationResult(
                    should_execute=False,
                    reason="相关代码已存在且高度相似",
                    existing_files=existing_files,
                    similarity=similarity
                )
        
        # 4. 估算工作量
        effort = self._estimate_effort(hypothesis)
        
        return ValidationResult(
            should_execute=True,
            estimated_effort=effort
        )
    
    async def _search_existing_code(self, keywords: List[str]) -> List[Path]:
        """搜索已存在的相关代码"""
        results = []
        for keyword in keywords:
            # 使用 ripgrep 搜索
            cmd = f"rg -l '{keyword}' {self.project_root}"
            output = await run_command(cmd)
            if output:
                results.extend([Path(f) for f in output.strip().split('\n')])
        return list(set(results))
```

### 2.4 动态超时管理

**问题**：固定超时不适合不同复杂度的任务。

**解决方案**：

```python
class DynamicTimeoutManager:
    """动态超时管理器"""
    
    # 任务复杂度与默认超时映射
    COMPLEXITY_TIMEOUTS = {
        TaskComplexity.SIMPLE: 300,      # 5 分钟
        TaskComplexity.MODERATE: 600,    # 10 分钟
        TaskComplexity.COMPLEX: 1800,    # 30 分钟
        TaskComplexity.EXPLORATORY: 1200 # 20 分钟
    }
    
    def __init__(self, max_total_timeout: int = 3600):
        self.max_total_timeout = max_total_timeout
        self.active_timeouts: Dict[str, TimeoutInfo] = {}
    
    def estimate_complexity(self, hypothesis: GeneratedHypothesis) -> TaskComplexity:
        """估算任务复杂度"""
        # 基于多个因素判断
        factors = {
            "effort_budget": hypothesis.effort_budget,
            "risk_level": hypothesis.risk_level,
            "dependencies_count": len(hypothesis.dependencies),
            "has_verification": bool(hypothesis.verification_steps)
        }
        
        score = 0
        score += min(factors["effort_budget"] / 10, 3)  # 0-3 分
        score += {"low": 0, "medium": 1, "high": 2}.get(factors["risk_level"], 1)
        score += min(factors["dependencies_count"], 2)
        score += 1 if factors["has_verification"] else 0
        
        if score <= 2:
            return TaskComplexity.SIMPLE
        elif score <= 4:
            return TaskComplexity.MODERATE
        elif score <= 6:
            return TaskComplexity.COMPLEX
        else:
            return TaskComplexity.EXPLORATORY
    
    def request_timeout(
        self,
        agent_id: str,
        task_id: str,
        requested_timeout: int,
        reason: str,
        complexity: TaskComplexity
    ) -> TimeoutDecision:
        """请求超时时间"""
        default_timeout = self.COMPLEXITY_TIMEOUTS[complexity]
        
        # 如果请求超时在合理范围内，直接批准
        if requested_timeout <= default_timeout * 1.5:
            return TimeoutDecision(
                approved=True,
                timeout_seconds=requested_timeout,
                message=f"批准 {requested_timeout}s"
            )
        
        # 如果请求过长，使用默认值
        return TimeoutDecision(
            approved=True,
            timeout_seconds=default_timeout,
            message=f"调整到建议值 {default_timeout}s"
        )
    
    def request_extension(
        self,
        agent_id: str,
        task_id: str,
        additional_timeout: int,
        reason: str,
        current_progress: float
    ) -> TimeoutDecision:
        """请求延长超时"""
        info = self.active_timeouts.get(task_id)
        if not info:
            return TimeoutDecision(approved=False, message="任务不存在")
        
        # 进度必须超过 50% 才能申请延长
        if current_progress < 0.5:
            return TimeoutDecision(
                approved=False,
                message=f"进度 {current_progress:.0%} 不足 50%，无法延长"
            )
        
        # 检查总超时是否超过限制
        new_total = info.current_timeout + additional_timeout
        if new_total > self.max_total_timeout:
            return TimeoutDecision(
                approved=False,
                message=f"总超时将超过限制 {self.max_total_timeout}s"
            )
        
        # 批准延长
        info.current_timeout = new_total
        return TimeoutDecision(
            approved=True,
            timeout_seconds=additional_timeout,
            message=f"批准延长 {additional_timeout}s"
        )
```

---

## 3. Prompt 工程改进

### 3.1 编排器系统提示优化

**现有问题**：系统提示不够具体，缺少明确的角色定义和行为规范。

**改进方案**：

```python
ORCHESTRATOR_SYSTEM_PROMPT = """
你是一个多智能体系统的中央编排器，负责协调多个子代理完成复杂开发任务。

## 你的核心职责

1. **规划**: 将复杂需求分解为可执行的假设和任务
2. **调度**: 根据依赖关系并行调度子代理
3. **监控**: 实时监控子代理状态和进度
4. **干预**: 在必要时接管或调整任务
5. **验证**: 确保输出质量和功能完整性

## 决策原则

### 任务分配原则
- **并行优先**: 无依赖的任务必须并行执行
- **边界清晰**: 每个子代理任务必须有明确的边界
- **预算合理**: 根据任务复杂度设置合理的努力预算

### 超时处理原则
- **先验证**: 超时后先检查任务是否已完成
- **再评估**: 评估是否值得重试
- **后接管**: 必要时 Orchestrator 直接接管

### 质量保障原则
- **标准明确**: 每个任务必须有可验证的成功标准
- **证据驱动**: 验证基于实际证据而非假设
- **学习导向**: 从失败中提取经验

## 输出格式

当需要委托子代理时，使用以下格式：

```json
{
  "subagent_tasks": [
    {
      "task_id": "task-001",
      "objective": "明确描述这个任务要解决什么问题",
      "output_format": "描述期望的输出结构",
      "tools_guidance": "建议使用的工具和方法",
      "boundaries": "明确不要做什么",
      "effort_budget": 10,
      "success_criteria": ["标准1", "标准2"]
    }
  ]
}
```

## 关键约束

- 永远不要假设子代理会理解隐含意图
- 永远不要在未验证的情况下声明任务完成
- 永远不要忽略失败模式
- 始终记录决策过程和学习经验
"""
```

### 3.2 子代理任务提示模板

**Anthropic 推荐格式**：

```python
SUBAGENT_TASK_TEMPLATE = """
# 任务: {task_title}

## 目标
{objective}

## 上下文
{context}

## 输出格式
{output_format}

## 工具指导
{tools_guidance}

## 任务边界
{boundaries}

## 努力预算
预计工具调用次数: ~{effort_budget} 次

如果发现任务比预期复杂，请立即报告并说明原因。

## 成功标准
{success_criteria}

## 验证步骤
{verification_steps}

## 重要提醒
1. 如果遇到超出边界的问题，立即报告
2. 如果发现任务已完成或不需要执行，报告原因
3. 如果接近努力预算但未完成，报告进度和下一步计划
"""
```

### 3.3 需求澄清提示优化

**改进方案**：

```python
CLARIFICATION_PROMPT = """
你是一个需求分析专家，负责将模糊的用户需求转化为清晰的、可执行的技术规格。

## 你的任务

分析用户需求，识别以下关键信息：

1. **核心功能**: 用户真正想要实现什么
2. **用户类型**: 谁会使用这个功能
3. **技术约束**: 有哪些技术限制或偏好
4. **成功标准**: 怎样算成功完成
5. **潜在风险**: 可能遇到什么问题

## 输出格式

```json
{
  "summary": "一句话描述需求核心",
  "user_type": "描述目标用户",
  "core_features": ["功能1", "功能2"],
  "tech_constraints": {
    "language": "技术栈偏好",
    "framework": "框架偏好",
    "constraints": ["其他约束"]
  },
  "success_criteria": ["标准1", "标准2"],
  "priority_order": ["优先级排序"],
  "risks": ["风险1", "风险2"],
  "clarifications_needed": [
    {
      "question": "需要澄清的问题",
      "options": ["选项A", "选项B"],
      "impact": "这个决定的影响范围"
    }
  ]
}
```

## 澄清策略

- 如果需求已经足够清晰，`clarifications_needed` 可以为空
- 如果需要澄清，最多提出 3 个最关键的问题
- 每个问题都应该是二选一或有限选项的问题
- 说明每个决定的影响范围

## 示例

**输入**: "帮我做一个电商系统"

**输出**:
```json
{
  "summary": "构建一个支持商品展示、购物车、订单管理的电商系统",
  "user_type": "小型电商商家",
  "core_features": ["商品管理", "购物车", "订单管理", "支付集成"],
  "tech_constraints": {},
  "success_criteria": ["用户可以浏览商品", "用户可以下单", "商家可以管理订单"],
  "priority_order": ["商品管理", "购物车", "订单管理", "支付集成"],
  "risks": ["支付安全", "性能瓶颈"],
  "clarifications_needed": [
    {
      "question": "技术栈偏好？",
      "options": ["Next.js + Supabase", "Django + PostgreSQL", "Spring Boot + MySQL"],
      "impact": "决定整体架构和开发效率"
    }
  ]
}
```
"""
```

---

## 4. 评估体系设计

### 4.1 多层次评估架构

```
┌─────────────────────────────────────────────────────────────┐
│                    评估体系架构                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Level 1: 自动验证                                          │
│  ├── 成功标准匹配                                           │
│  ├── 代码语法检查                                           │
│  ├── 测试执行结果                                           │
│  └── 静态分析                                               │
│                                                             │
│  Level 2: LLM-as-Judge                                      │
│  ├── 代码质量评估                                           │
│  ├── 架构合理性评估                                         │
│  ├── 安全性评估                                             │
│  └── 可维护性评估                                           │
│                                                             │
│  Level 3: 集成测试                                          │
│  ├── 功能完整性测试                                         │
│  ├── 跨模块集成测试                                         │
│  ├── 端到端测试                                             │
│  └── 性能测试                                               │
│                                                             │
│  Level 4: 人机协作                                          │
│  ├── 关键决策审查                                           │
│  ├── 最终验收                                               │
│  └── 反馈收集                                               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 LLM-as-Judge 实现

```python
class LLMJudge:
    """LLM 评估器"""
    
    EVALUATION_PROMPT = """
你是一个代码质量评估专家，负责评估 AI 生成的代码质量。

## 评估维度

1. **功能正确性** (0-10分): 代码是否实现了预期功能
2. **代码质量** (0-10分): 代码是否清晰、可读、遵循最佳实践
3. **架构合理性** (0-10分): 架构设计是否合理
4. **安全性** (0-10分): 是否存在安全隐患
5. **可维护性** (0-10分): 代码是否易于维护和扩展

## 评估对象

假设: {hypothesis}
代码变更: {code_changes}

## 输出格式

```json
{
  "scores": {
    "functional_correctness": 8,
    "code_quality": 7,
    "architecture": 8,
    "security": 9,
    "maintainability": 7
  },
  "overall_score": 7.8,
  "strengths": ["优点1", "优点2"],
  "weaknesses": ["弱点1", "弱点2"],
  "recommendations": ["建议1", "建议2"],
  "verdict": "accept|needs_revision|reject",
  "verdict_reason": "判断理由"
}
```
"""
    
    async def evaluate(
        self,
        hypothesis: GeneratedHypothesis,
        code_changes: List[CodeChange]
    ) -> EvaluationResult:
        """评估代码质量"""
        prompt = self.EVALUATION_PROMPT.format(
            hypothesis=hypothesis.statement,
            code_changes=self._format_changes(code_changes)
        )
        
        response = await self.llm.complete(prompt)
        result = self._parse_evaluation(response)
        
        return EvaluationResult(
            hypothesis_id=hypothesis.id,
            scores=result["scores"],
            overall_score=result["overall_score"],
            verdict=result["verdict"],
            recommendations=result["recommendations"]
        )
```

### 4.3 自动验证增强

**现有验证器的改进**：

```python
class EnhancedAutoValidator:
    """增强版自动验证器"""
    
    def __init__(self):
        self.test_runner = TestRunner()
        self.static_analyzer = StaticAnalyzer()
        self.security_scanner = SecurityScanner()
    
    async def validate(
        self,
        hypothesis: GeneratedHypothesis,
        execution_results: List[ExecutionResult]
    ) -> ValidationResult:
        """综合验证"""
        
        # 1. 成功标准验证
        criteria_results = await self._check_success_criteria(
            hypothesis, execution_results
        )
        
        # 2. 测试执行
        test_results = await self._run_tests(execution_results)
        
        # 3. 静态分析
        analysis_results = await self._static_analysis(execution_results)
        
        # 4. 安全扫描
        security_results = await self._security_scan(execution_results)
        
        # 5. 综合判断
        verdict = self._make_verdict(
            criteria_results,
            test_results,
            analysis_results,
            security_results
        )
        
        return ValidationResult(
            hypothesis_id=hypothesis.id,
            verdict=verdict,
            criteria_results=criteria_results,
            test_results=test_results,
            analysis_results=analysis_results,
            security_results=security_results,
            confidence=self._calculate_confidence(...)
        )
    
    async def _run_tests(self, execution_results: List[ExecutionResult]) -> TestResults:
        """执行测试"""
        test_files = self._find_test_files(execution_results)
        if not test_files:
            return TestResults(skipped=True, reason="No test files found")
        
        return await self.test_runner.run(test_files)
    
    async def _static_analysis(self, execution_results: List[ExecutionResult]) -> AnalysisResults:
        """静态分析"""
        changed_files = self._get_changed_files(execution_results)
        return await self.static_analyzer.analyze(changed_files)
    
    async def _security_scan(self, execution_results: List[ExecutionResult]) -> SecurityResults:
        """安全扫描"""
        changed_files = self._get_changed_files(execution_results)
        return await self.security_scanner.scan(changed_files)
```

### 4.4 人机协作评估

```python
class HumanAICollaboration:
    """人机协作评估"""
    
    def __init__(self, notification_channel: str):
        self.notification_channel = notification_channel
    
    async def request_review(
        self,
        hypothesis: GeneratedHypothesis,
        auto_result: ValidationResult,
        llm_result: EvaluationResult
    ) -> ReviewRequest:
        """请求人工审查"""
        
        # 判断是否需要人工审查
        if not self._needs_human_review(auto_result, llm_result):
            return ReviewRequest(skipped=True, reason="自动评估置信度高")
        
        # 发送通知
        await self._send_notification(
            channel=self.notification_channel,
            title=f"需要审查: {hypothesis.statement[:50]}...",
            summary=self._create_review_summary(auto_result, llm_result),
            actions=["approve", "request_changes", "reject"]
        )
        
        # 等待响应
        response = await self._wait_for_response(timeout=3600)
        
        return ReviewRequest(
            hypothesis_id=hypothesis.id,
            human_decision=response.decision,
            human_feedback=response.feedback
        )
    
    def _needs_human_review(
        self,
        auto_result: ValidationResult,
        llm_result: EvaluationResult
    ) -> bool:
        """判断是否需要人工审查"""
        # 需要人工审查的情况
        return (
            auto_result.verdict == ValidationVerdict.INCONCLUSIVE or
            auto_result.confidence < 0.7 or
            llm_result.overall_score < 6.0 or
            "security" in llm_result.weaknesses or
            auto_result.has_conflicts
        )
```

---

## 5. 生产可靠性增强

### 5.1 断点续传增强

**现有功能**：SprintPersistence 支持保存和恢复。

**增强方案**：

```python
class EnhancedPersistence:
    """增强版持久化管理"""
    
    def __init__(self, storage_path: Path):
        self.storage_path = storage_path
        self.checkpoint_interval = 60  # 每60秒自动保存
        self._last_checkpoint = time.time()
    
    async def save_checkpoint(
        self,
        context: SprintContext,
        force: bool = False
    ) -> None:
        """保存检查点"""
        now = time.time()
        if not force and (now - self._last_checkpoint) < self.checkpoint_interval:
            return
        
        checkpoint = SprintCheckpoint(
            sprint_id=context.sprint_id,
            state=context.state,
            timestamp=datetime.now(),
            context=self._serialize_context(context),
            recovery_info=self._create_recovery_info(context)
        )
        
        # 原子写入
        await self._atomic_write(checkpoint)
        self._last_checkpoint = now
    
    def _create_recovery_info(self, context: SprintContext) -> RecoveryInfo:
        """创建恢复信息"""
        return RecoveryInfo(
            can_resume=context.state not in [SprintState.COMPLETED, SprintState.FAILED],
            next_action=self._determine_next_action(context),
            estimated_remaining_time=self._estimate_remaining_time(context),
            dependencies_satisfied=self._check_dependencies(context)
        )
    
    async def recover(self, sprint_id: str) -> RecoveryPlan:
        """恢复冲刺"""
        checkpoint = await self._load_checkpoint(sprint_id)
        
        return RecoveryPlan(
            sprint_id=sprint_id,
            from_state=checkpoint.state,
            actions=[
                Action(type="restore_context", data=checkpoint.context),
                Action(type="verify_state", data=checkpoint.recovery_info),
                Action(type="continue_execution", data=checkpoint.recovery_info.next_action)
            ]
        )
```

### 5.2 错误恢复机制

```python
class ErrorRecoveryManager:
    """错误恢复管理器"""
    
    async def handle_error(
        self,
        error: Exception,
        context: SprintContext,
        execution_result: ExecutionResult
    ) -> RecoveryDecision:
        """处理错误并决定恢复策略"""
        
        error_type = self._classify_error(error)
        
        recovery_strategies = {
            ErrorType.TIMEOUT: self._handle_timeout,
            ErrorType.NETWORK: self._handle_network_error,
            ErrorType.RATE_LIMIT: self._handle_rate_limit,
            ErrorType.VALIDATION: self._handle_validation_error,
            ErrorType.DEPENDENCY: self._handle_dependency_error,
            ErrorType.UNKNOWN: self._handle_unknown_error
        }
        
        handler = recovery_strategies.get(error_type, self._handle_unknown_error)
        return await handler(error, context, execution_result)
    
    async def _handle_timeout(
        self,
        error: TimeoutError,
        context: SprintContext,
        execution_result: ExecutionResult
    ) -> RecoveryDecision:
        """处理超时"""
        
        # 1. 检查任务是否实际完成
        if await self._check_task_completed(execution_result):
            return RecoveryDecision(
                action="mark_completed",
                reason="任务实际已完成"
            )
        
        # 2. 检查重试次数
        if execution_result.retry_count >= 3:
            return RecoveryDecision(
                action="escalate",
                reason="重试次数已达上限"
            )
        
        # 3. 增加超时后重试
        return RecoveryDecision(
            action="retry",
            params={
                "timeout_multiplier": 1.5,
                "max_retries": 3
            }
        )
    
    async def _handle_network_error(
        self,
        error: NetworkError,
        context: SprintContext,
        execution_result: ExecutionResult
    ) -> RecoveryDecision:
        """处理网络错误"""
        return RecoveryDecision(
            action="retry_with_backoff",
            params={
                "initial_delay": 5,
                "max_delay": 60,
                "max_retries": 5
            }
        )
```

### 5.3 监控和可观测性

```python
class MonitoringSystem:
    """监控系统"""
    
    def __init__(self):
        self.metrics = MetricsCollector()
        self.tracer = Tracer()
        self.logger = StructuredLogger()
    
    async def track_execution(
        self,
        hypothesis: GeneratedHypothesis,
        execution: ExecutionResult
    ) -> None:
        """追踪执行"""
        
        # 记录指标
        self.metrics.record(
            name="execution_duration",
            value=execution.duration_seconds,
            tags={
                "hypothesis_id": hypothesis.id,
                "complexity": hypothesis.effort_budget,
                "status": execution.status
            }
        )
        
        # 记录追踪
        with self.tracer.span("execution") as span:
            span.set_attribute("hypothesis_id", hypothesis.id)
            span.set_attribute("status", execution.status)
            span.set_attribute("tokens_used", execution.tokens_used)
        
        # 结构化日志
        self.logger.info(
            "execution_completed",
            hypothesis_id=hypothesis.id,
            status=execution.status,
            duration=execution.duration_seconds,
            tokens_used=execution.tokens_used
        )
    
    def get_health_metrics(self) -> HealthMetrics:
        """获取健康指标"""
        return HealthMetrics(
            total_sprints=self.metrics.get("sprints_total"),
            success_rate=self.metrics.get("sprints_success_rate"),
            avg_duration=self.metrics.get("sprints_avg_duration"),
            error_rate=self.metrics.get("error_rate"),
            active_agents=self.metrics.get("active_agents")
        )
```

### 5.4 Dashboard 增强

```python
class EnhancedDashboard:
    """增强版 Dashboard"""
    
    async def render(self, context: SprintContext) -> DashboardView:
        """渲染 Dashboard"""
        return DashboardView(
            header=self._render_header(context),
            metrics=self._render_metrics(context),
            hypotheses=self._render_hypotheses(context),
            timeline=self._render_timeline(context),
            logs=self._render_logs(context),
            actions=self._render_actions(context)
        )
    
    def _render_hypotheses(self, context: SprintContext) -> HypothesesView:
        """渲染假设视图"""
        return HypothesesView(
            hypotheses=[
                HypothesisCard(
                    id=h.id,
                    statement=h.statement,
                    status=self._get_status(h),
                    progress=self._calculate_progress(h),
                    dependencies=h.dependencies,
                    risk_level=h.risk_level,
                    estimated_remaining=self._estimate_remaining(h)
                )
                for h in context.hypotheses
            ],
            dependency_graph=self._render_dependency_graph(context),
            parallel_groups=self._identify_parallel_groups(context)
        )
```

---

## 6. 实施计划

### 6.1 阶段划分

| 阶段 | 目标 | 预计时间 | 优先级 |
|------|------|---------|--------|
| Phase 1 | Prompt 工程优化 | 1周 | P0 |
| Phase 2 | 任务前验证系统 | 1周 | P0 |
| Phase 3 | 动态超时管理 | 1周 | P1 |
| Phase 4 | 评估体系增强 | 2周 | P1 |
| Phase 5 | 可靠性增强 | 2周 | P2 |

### 6.2 Phase 1: Prompt 工程优化

**任务清单**：
- [ ] 更新 Orchestrator 系统提示
- [ ] 标准化子代理任务模板
- [ ] 优化需求澄清提示
- [ ] 更新假设生成提示
- [ ] 添加验证和评估提示

### 6.3 Phase 2: 任务前验证系统

**任务清单**：
- [ ] 实现 PreTaskValidator
- [ ] 集成代码搜索功能
- [ ] 实现相似度计算
- [ ] 添加工作量估算
- [ ] 集成到编排器流程

### 6.4 Phase 3: 动态超时管理

**任务清单**：
- [ ] 实现 DynamicTimeoutManager
- [ ] 添加复杂度估算算法
- [ ] 实现超时申请/延长协议
- [ ] 集成监控和告警
- [ ] 更新 Dashboard 显示

### 6.5 Phase 4: 评估体系增强

**任务清单**：
- [ ] 实现 LLMJudge
- [ ] 增强 AutoValidator
- [ ] 实现人机协作评估
- [ ] 添加测试集成
- [ ] 实现安全扫描

### 6.6 Phase 5: 可靠性增强

**任务清单**：
- [ ] 增强持久化系统
- [ ] 实现错误恢复管理器
- [ ] 添加监控系统
- [ ] 增强 Dashboard
- [ ] 编写运维文档

---

## 7. 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| Prompt 变更影响现有功能 | 高 | 增量更新，保留回滚能力 |
| LLM-as-Judge 评估偏差 | 中 | 多模型交叉验证，人工抽检 |
| 动态超时估算不准 | 中 | 基于历史数据持续优化 |
| 任务前验证误判 | 中 | 设置相似度阈值，允许手动覆盖 |
| 监控系统性能开销 | 低 | 异步收集，采样策略 |

---

## 8. 成功指标

| 指标 | 当前值 | 目标值 | 衡量方式 |
|------|--------|--------|---------|
| 任务成功率 | ~70% | >90% | 完成任务数/总任务数 |
| Token 浪费率 | ~20% | <5% | 浪费tokens/总tokens |
| 平均执行时间 | 基线 | 减少30% | 任务平均完成时间 |
| 验证准确率 | ~60% | >85% | 正确验证/总验证 |
| 用户满意度 | N/A | >4.0/5.0 | 用户反馈评分 |

---

## 9. 参考资料

1. Anthropic: "How we built our multi-agent research system"
2. AOP 现有架构文档
3. PurifyAI 项目经验总结
4. best-practices.md

---

## 更新日志

- 2026-03-07: 初始版本，基于 Anthropic 经验对比分析
