# WORKFLOW.md - 工作流程

## 核心方法论

**AAIF 循环 + 假设驱动开发 + 多 Agent 并行**

```
┌─────────────────────────────────────────────────────┐
│                    AAIF 循环                         │
│                                                     │
│   探索 (Explore)                                    │
│   └─ 理解需求 → 搜索代码 → 生成假设                  │
│          ↓                                          │
│   构建 (Build)                                      │
│   └─ 分解任务 → 并行委派 → 整合结果                  │
│          ↓                                          │
│   验证 (Validate)                                   │
│   └─ 运行测试 → 检查质量 → 验证假设                  │
│          ↓                                          │
│   学习 (Learn)                                      │
│   └─ 提取经验 → 更新记忆 → 优化策略                  │
│          ↓                                          │
│   (回到探索，继续迭代)                               │
└─────────────────────────────────────────────────────┘
```

---

## 1. 探索 (Explore)

### 目标
- 理解用户需求
- 搜索代码库了解上下文
- 生成可验证的假设

### 假设格式

```
假设: 如果 [行动]，那么 [预期结果]
优先级: P0/P1/P2/P3
验证标准: [如何验证]
状态: pending/testing/validated/refuted
```

### 示例

```
假设: 如果添加 Redis 缓存，那么 API 响应时间降低 50%
优先级: P1
验证标准: 压测对比前后响应时间
状态: pending
```

### 行动

```
# 搜索相关代码
Grep("cache")
Glob("*.py")

# 理解现有架构
Read("src/api/handlers.py")
Read("src/db/queries.py")

# 生成假设
```

---

## 2. 构建 (Build)

### 任务分解

**根据复杂度决定分解策略**：

| 复杂度 | 特征 | 分解策略 |
|--------|------|---------|
| 简单 | 单文件、单功能 | 1 个 Developer Agent |
| 中等 | 多文件、多模块 | 2-4 个 Developer Agent（按模块） |
| 复杂 | 大型功能、重构 | 5+ Agent（Developer + Reviewer + Tester） |

### 并行委派

**同时启动多个子 Agent**：

```
# 示例：实现用户认证系统

# 阶段 1：并行开发（3 个 Developer）
Task(
  name="dev-auth",
  prompt="""
【目标】实现认证核心逻辑
【输出】auth.py 的修改
【边界】只实现 login/logout，不处理注册

立即开始执行。
""",
  subagent_type="general-purpose"
)

Task(
  name="dev-api",
  prompt="""
【目标】实现认证 API 路由
【输出】routes/auth.py 的修改
【边界】只定义路由，调用 dev-auth 的接口

立即开始执行。
""",
  subagent_type="general-purpose"
)

Task(
  name="dev-middleware",
  prompt="""
【目标】实现认证中间件
【输出】middleware/auth.py 的修改
【边界】只做 token 验证

立即开始执行。
""",
  subagent_type="general-purpose"
)
```

### 结果整合

**Lead Agent 收集所有子 Agent 输出**：

```
# 等待所有 Developer 完成
# 整合结果：
# - dev-auth: auth.py 已修改
# - dev-api: routes/auth.py 已修改
# - dev-middleware: middleware/auth.py 已修改

# 检查是否有冲突
# 决定是否需要调整
```

---

## 3. 验证 (Validate)

### 测试验证

```
# 启动 Tester Agent
Task(
  name="tester",
  prompt="""
【目标】验证用户认证功能
【输出】测试结果报告
【工具】Bash(pytest)

测试用例：
1. 登录成功返回 token
2. 登录失败返回 401
3. token 过期返回 401

立即开始执行。
""",
  subagent_type="general-purpose"
)
```

### 代码审查

```
# 启动 Reviewer Agent
Task(
  name="reviewer",
  prompt="""
【目标】审查认证模块代码质量
【输出】问题列表 + 改进建议
【工具】Read/Grep

审查维度：
1. 安全性：是否有 SQL 注入、XSS 风险
2. 性能：是否有 N+1 查询
3. 可维护性：代码结构是否清晰

立即开始执行。
""",
  subagent_type="general-purpose"
)
```

### 假设验证

```
# 更新假设状态
假设: 如果添加 Redis 缓存，那么 API 响应时间降低 50%
状态: validated  # 测试数据支持假设
证据: 响应时间从 200ms 降到 85ms
```

---

## 4. 学习 (Learn)

### 提取经验

```
# 记录学到的东西
1. Redis 缓存对读密集型 API 效果显著
2. 需要注意缓存失效策略
3. 并行 Agent 开发模式适合独立模块
```

### 更新记忆

```
# 更新项目记忆文件
- 记录有效的模式
- 记录失败的教训
- 记录可复用的解决方案
```

### 优化策略

```
# 下次类似任务
- 可以复用相同的分解策略
- 可以复用相同的测试用例模板
- 避免重复踩坑
```

---

## 工作流示例

### 示例 1：新功能开发

```
# 1. 探索
假设: 如果添加搜索功能，用户能更快找到内容
优先级: P1

# 2. 构建（分解为 3 个并行任务）
Task(name="dev-search-api", prompt="实现搜索 API...")
Task(name="dev-search-ui", prompt="实现搜索界面...")
Task(name="dev-search-index", prompt="实现索引构建...")

# 3. 验证
Task(name="reviewer", prompt="审查搜索模块...")
Task(name="tester", prompt="测试搜索功能...")

# 4. 学习
# 记录：全文搜索用 Elasticsearch 效果好
```

### 示例 2：Bug 修复

```
# 1. 探索
假设: 如果修复 X，bug Y 会消失
优先级: P0

# 2. 构建
Task(name="developer", prompt="修复 bug...")

# 3. 验证
Task(name="tester", prompt="验证修复...")

# 4. 学习
# 记录：bug 的根因和预防方法
```

### 示例 3：代码重构

```
# 1. 探索
假设: 如果重构 X 模块，可维护性提升 50%
优先级: P2

# 2. 构建（按子模块分解）
Task(name="dev-refactor-core", prompt="重构核心...")
Task(name="dev-refactor-utils", prompt="重构工具...")
Task(name="dev-refactor-tests", prompt="更新测试...")

# 3. 验证
Task(name="reviewer", prompt="检查重构质量...")
Task(name="tester", prompt="确保功能不变...")

# 4. 学习
# 记录：重构的最佳实践
```

---

## 最佳实践（来自 Anthropic）

1. **教会 Lead Agent 如何委派**
   - 详细描述：目标、输出格式、工具、边界

2. **根据复杂度调整努力**
   - 简单任务少投入，复杂任务多投入

3. **并行化提速**
   - 同时启动子 Agent
   - 减少等待时间

4. **先宽后窄**
   - 先探索整体，再深入细节

5. **让 Agent 自我改进**
   - 记录失败模式
   - 优化 prompt 和工具

---

## ⛔ 禁止使用 TeamCreate

TeamCreate → `in-process` 后端 → Agent idle

使用原生 Task → 独立后端 → 正常执行 ✅
