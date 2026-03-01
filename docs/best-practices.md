# AOP 最佳实践

> 基于 PurifyAI 项目的实际开发经验总结

---

## 📊 超时配置

### 问题发现
在 PurifyAI 开发过程中，子 Agent 经常因超时失败：
- Agent-UI-001: 3 分钟超时，消耗 817k tokens
- Agent-Integration-001: 3 分钟超时，消耗 783k tokens

### 推荐配置

```yaml
# .aop.yaml
defaults:
  timeout: 600  # 10 分钟

subagent:
  default_timeout: 600  # 10 分钟
  complex_task_timeout: 1800  # 30 分钟
```

### 超时时间建议

| 任务类型 | 建议超时 | 说明 |
|---------|---------|------|
| 简单代码审查 | 300s (5分钟) | 单文件或小范围检查 |
| UI 组件开发 | 600s (10分钟) | 单个组件创建或修改 |
| 功能集成 | 900s (15分钟) | 多组件集成 |
| 复杂重构 | 1800s (30分钟) | 大范围代码重构 |
| 端到端测试 | 1200s (20分钟) | 完整流程测试 |

---

## 🔍 任务前验证

### 问题发现
子 Agent 超时后，Orchestrator 检查发现任务已完成：
- H-014 模式切换 UI - 代码已存在
- H-015 报告集成 - 代码已存在

浪费了 ~1.6M tokens。

### 解决方案：任务前验证

```python
# 在分配任务前检查
def should_assign_task(task_description: str, project_path: Path) -> ValidationResult:
    """
    检查任务是否需要分配
    
    Returns:
        ValidationResult:
            - should_assign: 是否需要分配
            - reason: 原因
            - existing_files: 已存在的相关文件
    """
    # 1. 提取任务关键词
    keywords = extract_keywords(task_description)
    
    # 2. 搜索相关代码
    existing_files = search_code(project_path, keywords)
    
    # 3. 判断是否已存在
    if existing_files:
        return ValidationResult(
            should_assign=False,
            reason="相关代码已存在",
            existing_files=existing_files
        )
    
    return ValidationResult(should_assign=True)
```

### 推荐配置

```yaml
# .aop.yaml
validation:
  check_existing_code: true
  check_duplicate_tasks: true
  estimate_timeout: true
```

---

## 🤖 Orchestrator 职责

### 核心职责

```
┌─────────────────────────────────────────┐
│         Orchestrator (主 Agent)          │
├─────────────────────────────────────────┤
│                                         │
│  1. 创建假设                             │
│     └─ 定义明确的目标和成功标准          │
│                                         │
│  2. 任务前验证 ⭐ 新增                   │
│     └─ 检查代码是否已存在                │
│     └─ 检查是否重复任务                  │
│     └─ 估算超时时间                      │
│                                         │
│  3. 分配任务                             │
│     └─ 并行分配多个子 Agent              │
│     └─ 设置合理的超时时间                │
│                                         │
│  4. 监控执行                             │
│     └─ 检测超时                          │
│     └─ 检测失败                          │
│                                         │
│  5. 超时接管 ⭐ 重要                     │
│     └─ 子 Agent 超时后接管任务           │
│     └─ 评估是否继续或跳过                │
│                                         │
│  6. 验证结果                             │
│     └─ 检查代码质量                      │
│     └─ 验证功能完整性                    │
│                                         │
│  7. 捕获学习                             │
│     └─ 记录什么有效                      │
│     └─ 记录什么失败                      │
│     └─ 提出改进建议                      │
│                                         │
└─────────────────────────────────────────┘
```

### 超时接管策略

```python
class Orchestrator:
    def handle_subagent_timeout(self, agent_id: str, task: Task):
        """处理子 Agent 超时"""
        
        # 1. 检查任务是否已完成
        if self._check_task_completed(task):
            return  # 已完成，无需处理
        
        # 2. 评估是否值得重试
        if self._should_retry(task):
            # 重新分配，增加超时时间
            self._reassign_with_longer_timeout(task)
        else:
            # Orchestrator 接管
            self._take_over_task(task)
    
    def _check_task_completed(self, task: Task) -> bool:
        """检查任务是否已完成"""
        # 搜索相关代码
        # 检查功能是否存在
        pass
    
    def _should_retry(self, task: Task) -> bool:
        """判断是否应该重试"""
        # 考虑因素：
        # - 任务复杂度
        # - 已消耗 token 数
        # - 重试次数
        pass
```

---

## 📈 并行执行

### 推荐并行度

```yaml
subagent:
  max_parallel: 3  # 同时最多 3 个子 Agent
```

### 并行策略

| 场景 | 并行度 | 说明 |
|------|--------|------|
| UI + Backend | 2 | 前后端分离开发 |
| 多模块开发 | 3-4 | 独立模块并行 |
| 测试 + 开发 | 2 | 开发和测试并行 |
| 大型重构 | 1 | 单 Agent 避免 conflict |

---

## 📝 学习捕获模板

```markdown
# 学习日志 - [Run ID]

## YYYY-MM-DD HH:MM - [任务名称]

### ✅ 有效的做法
1. ...
2. ...

### ❌ 失败的做法
1. ...
2. ...

### 💡 洞察
1. ...
2. ...

### 🔄 改进建议
1. ...
2. ...
```

---

## 🛠 工具推荐

### 代码搜索

```bash
# 使用 ripgrep 搜索代码
rg "pattern" --type py -l

# 使用 grep
grep -r "pattern" --include="*.py" -l
```

### 文件监控

```bash
# 监控文件变化
watchexec -e py "pytest tests/"
```

---

## 📚 参考资料

- [AAIF 框架](https://github.com/xuha233/agent-team-template)
- [MCO 执行引擎](https://github.com/xuha233/mco)
- [PurifyAI 项目](https://github.com/xuha233/purifyai)

---

## 更新日志

- 2026-03-02: 基于 PurifyAI Run 006 经验创建
