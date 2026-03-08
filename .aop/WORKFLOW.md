# WORKFLOW.md - 工作流程

## 核心方法论

**AAIF 循环 + Agent Teams 并行协作**

```
┌─────────────────────────────────────────────────────┐
│                    AAIF 循环                         │
│                                                     │
│   探索 (Explore)                                    │
│   └─ 理解需求 → 搜索代码 → 生成假设                  │
│          ↓                                          │
│   构建 (Build)                                      │
│   └─ 创建团队 → 分配任务（详细上下文）→ 并行执行     │
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
```

---

## 2. 构建 (Build)

### 创建团队

**用自然语言创建团队**：

```
创建一个 agent team 来开发商品盘点功能：

- 队友A（数据层）：负责 Model 实体类 + DAL 数据访问层
  文件范围：OSModel/Entities/、OSModel/Requests/、OSDAL/
  参考：InboundOrderDAL 风格
  交付物：实体类、DAL 类
  边界：只做数据层

- 队友B（业务层）：负责 Interface 接口定义 + BLL 业务逻辑
  文件范围：OSInterface/、OSBLL/
  参考：InboundOrderBLL 风格
  交付物：接口定义、BLL 类
  边界：调用队友A的接口

- 队友C（API层）：负责 Controller + 路由配置
  文件范围：OSAPI/Controllers/
  参考：GoodsInboundOrderController 风格
  交付物：Controller 类
  边界：只做路由和参数验证

- 队友D（测试）：负责单元测试 + 集成测试
  文件范围：Tests/UnitTests/、Tests/IntegrationTests/
  交付物：测试文件

Use Sonnet for each teammate.
```

### ⚠️ 关键：提供详细上下文

**队友不继承你的对话历史！**

每个队友的描述必须包含：
1. **角色定位** - 数据层/业务层/API层/测试
2. **文件范围** - 负责哪些文件
3. **参考代码** - 参考哪个现有模块的风格
4. **交付物** - 期望输出什么
5. **边界** - 做什么、不做什么

### 任务粒度原则

| 粒度 | 问题 |
|------|------|
| 太小 | 协调开销大于收益 |
| 太大 | 没有检查点，浪费精力 |
| 适中 | 自包含的工作单元，有明确交付物 ✅ |

---

## 3. 验证 (Validate)

### 监控进展

```
# 切换到不同队友查看进展
Shift+Up/Down

# 或发送消息询问
Ask teammate A about their progress
```

### 运行测试

```
# 让测试队友运行测试
Ask the tester teammate to run all tests
```

### 代码审查

```
# 创建审查队友
创建一个 agent team 来审查代码：
- 队友A（安全审查）：检查 SQL 注入、XSS 等
- 队友B（性能审查）：检查 N+1 查询、内存泄漏
- 队友C（代码质量）：检查命名、结构、注释
```

---

## 4. 学习 (Learn)

### 提取经验

```
# 记录学到的东西
1. 按层分配队友比按文件分配更有效
2. 提供参考代码风格可以减少返工
3. 明确边界可以避免文件冲突
```

### 更新记忆

```
# 更新项目记忆文件
- 记录有效的模式
- 记录失败的教训
- 记录可复用的解决方案
```

---

## 工作流示例

### 示例 1：新功能开发（4-5 个队友）

```
# 1. 探索
假设: 如果添加搜索功能，用户能更快找到内容
优先级: P1

# 2. 构建（创建团队）
创建一个 agent team 来开发搜索功能：

- 队友A（数据层）：负责索引构建、查询优化
  文件范围：src/search/indexer.py、src/search/querier.py
  参考：现有的数据库查询风格

- 队友B（业务层）：负责搜索逻辑、结果排序
  文件范围：src/services/search_service.py
  参考：现有的 service 风格

- 队友C（API层）：负责搜索 API 端点
  文件范围：src/api/search_routes.py
  参考：现有的路由风格

- 队友D（测试）：负责测试用例
  文件范围：tests/test_search.py

Use Sonnet for each teammate.

# 3. 验证（创建审查团队）
创建一个 agent team 来审查搜索功能：
- 队友A：检查性能（索引大小、查询延迟）
- 队友B：检查边界情况（空搜索、特殊字符）

# 4. 学习
# 记录：全文搜索用 Elasticsearch 效果好
```

### 示例 2：跨模块重构（3-4 个队友）

```
# 1. 探索
假设: 如果统一错误码，API 响应更一致
优先级: P2

# 2. 构建（按模块分组）
创建一个 agent team 来统一错误码：

- 队友A：负责 商品管理 + 分类 模块
  文件：goods_controller.py、category_controller.py
  
- 队友B：负责 采购 + 入库 + 库存 模块
  文件：purchase_controller.py、inbound_controller.py
  
- 队友C：负责 销售 + 团购 模块
  文件：sales_controller.py、wholesale_controller.py

- 队友D：负责更新文档
  文件：docs/error_codes.md

# 3. 验证
# 运行所有测试确保没有破坏功能

# 4. 学习
# 记录：按模块分组避免文件冲突
```

### 示例 3：复杂 Bug 调查（3 个队友）

```
# 1. 探索
假设: 库存扣减不准确可能是并发问题
优先级: P0

# 2. 构建（竞争性假设）
创建一个 agent team 来调查库存问题：

- 队友A（入口追踪）：从 Controller → BLL → DAL 追踪流程
  重点：请求处理流程、事务边界
  
- 队友B（数据验证）：检查数据库一致性
  重点：库存余额 vs 流水合计
  
- 队友C（并发分析）：检查锁机制、MQ 幂等性
  重点：并发控制、异步处理

# 3. 验证
# 队友之间竞争验证，找出真正的根因

# 4. 学习
# 记录：多队友竞争验证比单 Agent 更快定位 Bug
```

### 示例 4：发版前质量验证（3 个队友）

```
# 创建一个 agent team 来进行发版前检查：

- 队友A（单元测试）：运行所有单元测试，修复失败用例
- 队友B（集成测试）：运行所有集成测试，验证端到端流程
- 队友C（数据库验证）：检查关键表的数据完整性

# 等待所有队友完成
Wait for your teammates to complete their tasks before proceeding.
```

---

## 最佳实践（来自 Claude Code 官方）

1. **给队友足够的上下文** - 他们不继承你的对话历史
2. **任务粒度适中** - 自包含的工作单元，有明确交付物
3. **避免文件冲突** - 不同队友负责不同文件
4. **从简单场景入手** - 先做研究/评审，再做并行开发
5. **定期检查进展** - Shift+Up/Down 查看队友状态
6. **指定模型** - 用 Sonnet 降低成本
7. **按层分配 > 按文件分配** - 分层架构天然适合多队友
8. **复杂模块才用 Teams** - 简单 CRUD 用单 Agent 即可

---

## 常用指令

```
# 让特定队友停止工作
Ask the [name] teammate to shut down

# 等待所有队友完成
Wait for your teammates to complete their tasks before proceeding

# 清理团队
Clean up the team
```
