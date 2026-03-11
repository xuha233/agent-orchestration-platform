# AOP Dashboard 改进实施计划

> 文档创建时间：2026-03-11
> 状态：规划阶段

## 目录

1. [需求分析](#需求分析)
2. [技术方案](#技术方案)
3. [实施步骤](#实施步骤)
4. [依赖关系](#依赖关系)
5. [风险评估](#风险评估)
6. [验收标准](#验收标准)

---

## 需求分析

### 1. 开发者控制台改名

**需求描述**：
将侧边栏和页面标题中的"开发者控制台"改名为"调试日志"。

**当前实现**：
- 文件位置：`src/aop/dashboard/app.py`
- 相关代码：
  - `render_sidebar()` 函数中的导航项定义
  - `page_dev_console()` 页面标题

**影响范围**：
- 侧边栏导航项文本
- 页面标题
- 设置页面的开关文本

**复杂度**：⭐（低）

---

### 2. 首页快速启动改进

**需求描述**：
首页工作区快速启动功能需要两个改进：
1. 点击启动按钮时，应启动全局设置的 agent（而非固定 `main`）
2. 快速启动后，AOP 应自动切换到启动的工作区（保持同步）

**当前实现**：
```python
# 当前代码 (app.py:808-828)
response = requests.post(
    "http://127.0.0.1:18789/hooks/agent",
    headers={...},
    json={
        "message": "你好，请汇报项目状态",
        "agentId": "main",  # 问题：固定为 "main"
        "wakeMode": "now"
    },
    timeout=5
)
```

**问题分析**：
1. `agentId` 硬编码为 `"main"`，未使用全局设置的 `primary_agent`
2. 启动后没有自动切换工作区的逻辑
3. Webhook 响应处理已修复（`{"ok": true}` 识别为成功）

**影响范围**：
- `page_home()` 函数中的快速启动逻辑
- 需要与 `SettingsManager` 集成

**复杂度**：⭐⭐（中低）

---

### 3. 项目进度实时监控

**需求描述**：
首页需要显示项目进度实时监控面板，需要支持三种主 Agent 环境：
- Claude Code
- OpenCode  
- OpenClaw

**监控指标建议**：
- 假设数量和状态（pending/testing/validated）
- 学习记录数量
- 测试状态（如果有测试框架）
- Git 状态（当前分支、未提交更改）
- Sprint 进度

**当前实现**：
- 已有 `get_hypotheses_data()` 函数获取假设数据
- 已有 `get_sprint_data()` 函数获取 Sprint 数据
- 已有 `get_project_stats()` 函数获取项目统计
- 已有基本的进度显示（`page_home()` 中的"项目进度报告"部分）

**缺失功能**：
1. 实时刷新机制（当前需手动刷新页面）
2. 三种 Agent 的差异化状态获取
3. 测试状态集成
4. Git 状态集成

**复杂度**：⭐⭐⭐（中等）

---

### 4. 已完成的修复

| 修复项 | 状态 | 文件位置 |
|--------|------|----------|
| 修复 datetime 局部变量问题 | ✅ 已完成 | `app.py:1159` - 添加了 `from datetime import datetime` 导入 |
| 修复 Webhook 响应处理 | ✅ 已完成 | `app.py:820-828` - 正确处理 `{"ok": true}` 响应 |
| 移除敏捷教练页面的快速启动栏目 | ✅ 已完成 | `page_coach()` 已移除快速启动，保留启动 CLI 栏目 |

---

## 技术方案

### 1. 开发者控制台改名

**方案**：直接文本替换

```python
# render_sidebar() 中
pages = ["🏠 首页", "💬 敏捷教练", "📚 项目记忆", "📁 工作区", "⚙️ 设置"]
if show_dev_console:
    pages.append("🖥️ 调试日志")  # 改名

# page_dev_console() 中
st.title("🖥️ 调试日志")  # 改名

# page_settings() 中
st.markdown("### 调试日志")  # 改名
```

---

### 2. 首页快速启动改进

**方案 A：使用全局设置的 Agent**

```python
def quick_launch_workspace(ws):
    """快速启动工作区"""
    sm = st.session_state.settings_manager
    primary_agent = sm.get_primary_agent()
    
    # 映射 primary_agent 到 Webhook agentId
    agent_mapping = {
        "openclaw": "main",  # OpenClaw 的默认 agent
        "claude_code": "claude",
        "opencode": "opencode",
    }
    agent_id = agent_mapping.get(primary_agent, "main")
    
    # 切换当前工作区
    st.session_state.current_workspace = ws
    wm.set_current_workspace(ws.id)
    
    # 调用 Webhook
    response = requests.post(
        "http://127.0.0.1:18789/hooks/agent",
        headers={...},
        json={
            "message": "你好，请汇报项目状态",
            "agentId": agent_id,
            "wakeMode": "now"
        },
        timeout=5
    )
    
    # 处理响应
    if response.status_code == 200:
        result = response.json()
        if result.get("ok") or result.get("status") == "ok":
            st.toast(f"已启动: {ws.name}", icon="✅")
            # 自动切换工作区后刷新页面
            st.rerun()
```

**方案 B：自动切换工作区**

在快速启动按钮点击后：
1. 设置 `st.session_state.current_workspace`
2. 调用 `wm.set_current_workspace(ws.id)`
3. 调用 Webhook 启动 agent
4. 显示 toast 通知
5. 调用 `st.rerun()` 刷新页面

---

### 3. 项目进度实时监控

**架构设计**：

```
┌─────────────────────────────────────────────────────────────┐
│                    项目进度监控面板                           │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐            │
│  │  假设进度    │ │  学习记录    │ │  Git 状态   │            │
│  │  ────────   │ │  ────────   │ │  ────────   │            │
│  │  ✅ 3/5     │ │  📚 12 条    │ │  🌿 main   │            │
│  │  🔬 1 测试中 │ │  最新: 1h前  │ │  2 uncommit│            │
│  └─────────────┘ └─────────────┘ └─────────────┘            │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐            │
│  │  测试状态    │ │  Agent 状态  │ │  Sprint     │            │
│  │  ────────   │ │  ────────   │ │  ────────   │            │
│  │  ✅ 288/288 │ │  🟢 运行中   │ │  🚀 进行中  │            │
│  │  100% 通过  │ │  CPU: 12%   │ │  任务: 2/5  │            │
│  └─────────────┘ └─────────────┘ └─────────────┘            │
└─────────────────────────────────────────────────────────────┘
```

**数据源映射**：

| 指标 | 数据源 | 获取方式 |
|------|--------|----------|
| 假设数量/状态 | `.aop/hypotheses.json` | `get_hypotheses_data()` |
| 学习记录 | `.aop/learning.json` | 读取 JSON 文件 |
| Git 状态 | `git status` | 调用 Git 命令 |
| 测试状态 | pytest 输出 | 解析测试结果文件 |
| Agent 状态 | Agent CLI | 各 Agent API/命令 |
| Sprint 进度 | `.aop/sprints/` | `get_sprint_data()` |

**三种 Agent 的差异化实现**：

**Claude Code**：
```python
def get_claude_code_status(project_path: str) -> dict:
    """获取 Claude Code 项目状态"""
    # 1. 读取 .claude 目录
    claude_dir = Path(project_path) / ".claude"
    
    # 2. 检查会话文件
    sessions = list(claude_dir.glob("sessions/*.json"))
    
    # 3. 读取 CLAUDE.md 中的系统提示
    
    return {
        "active_sessions": len(sessions),
        "last_activity": ...,
    }
```

**OpenCode**：
```python
def get_opencode_status(project_path: str) -> dict:
    """获取 OpenCode 项目状态"""
    # OpenCode 使用不同的配置目录
    opencode_dir = Path(project_path) / ".opencode"
    
    return {
        "config_exists": opencode_dir.exists(),
        # ...
    }
```

**OpenClaw**：
```python
def get_openclaw_status(project_path: str) -> dict:
    """获取 OpenClaw 项目状态"""
    # 通过 Gateway API 获取状态
    try:
        response = requests.get("http://127.0.0.1:18789/api/status")
        return response.json()
    except:
        return {"status": "offline"}
```

**实时刷新机制**：

使用 Streamlit 的 `st.rerun()` 配合定时器：

```python
import streamlit.components.v1 as components

def render_progress_panel():
    """渲染进度面板（带自动刷新）"""
    # 自动刷新间隔（毫秒）
    refresh_interval = 30000  # 30秒
    
    # 使用 JavaScript 定时刷新
    components.html(f"""
        <script>
            setTimeout(function() {{
                window.parent.location.reload();
            }}, {refresh_interval});
        </script>
    """, height=0)
    
    # 渲染进度指标
    render_metrics()
```

---

## 实施步骤

### 优先级排序

| 优先级 | 任务 | 预估时间 | 依赖 |
|--------|------|----------|------|
| P0 | 开发者控制台改名 | 10分钟 | 无 |
| P1 | 首页快速启动改进 | 30分钟 | 无 |
| P2 | 项目进度监控-基础版 | 2小时 | 无 |
| P3 | 项目进度监控-Agent差异化 | 2小时 | P2 |
| P3 | 项目进度监控-实时刷新 | 1小时 | P2 |

### 详细步骤

#### 任务 1：开发者控制台改名（P0）

1. **修改侧边栏导航**
   - 文件：`src/aop/dashboard/app.py`
   - 函数：`render_sidebar()`
   - 行为：将 `"🖥️ 开发者控制台"` 改为 `"🖥️ 调试日志"`

2. **修改页面标题**
   - 函数：`page_dev_console()`
   - 行为：将 `st.title("🖥️ 开发者控制台")` 改为 `st.title("🖥️ 调试日志")`

3. **修改设置页面**
   - 函数：`page_settings()`
   - 行为：将 `"开发者控制台"` 相关文本改为 `"调试日志"`

#### 任务 2：首页快速启动改进（P1）

1. **获取全局设置的 Agent**
   ```python
   sm = st.session_state.settings_manager
   primary_agent = sm.get_primary_agent()
   ```

2. **映射 Agent ID**
   ```python
   agent_mapping = {
       "openclaw": "main",
       "claude_code": "claude", 
       "opencode": "opencode",
       None: "main"  # 默认
   }
   agent_id = agent_mapping.get(primary_agent, "main")
   ```

3. **修改 Webhook 调用**
   - 替换硬编码的 `"main"` 为动态 `agent_id`

4. **添加自动切换逻辑**
   - 在 Webhook 调用成功后刷新页面
   - 确保 `st.session_state.current_workspace` 已更新

#### 任务 3：项目进度监控-基础版（P2）

1. **创建监控数据获取函数**
   ```python
   def get_project_progress_data(project_path: str) -> dict:
       """获取项目进度数据"""
       return {
           "hypotheses": get_hypotheses_stats(project_path),
           "learnings": get_learning_stats(project_path),
           "git": get_git_status(project_path),
           "tests": get_test_status(project_path),
       }
   ```

2. **实现各指标获取函数**
   - `get_hypotheses_stats()` - 读取 `.aop/hypotheses.json`
   - `get_learning_stats()` - 读取 `.aop/learning.json`
   - `get_git_status()` - 调用 `git status --porcelain`
   - `get_test_status()` - 检查 pytest 结果

3. **创建进度面板组件**
   ```python
   def render_progress_metrics(data: dict):
       """渲染进度指标"""
       col1, col2, col3 = st.columns(3)
       with col1:
           st.metric("假设", f"{data['hypotheses']['validated']}/{data['hypotheses']['total']}")
       # ...
   ```

#### 任务 4：项目进度监控-Agent差异化（P3）

1. **检测当前 Agent 类型**
   ```python
   def get_current_agent_type() -> str:
       sm = st.session_state.settings_manager
       return sm.get_primary_agent() or "claude_code"
   ```

2. **实现 Agent 特定状态获取**
   - `get_claude_code_status()`
   - `get_opencode_status()`
   - `get_openclaw_status()`

3. **整合到进度面板**
   ```python
   agent_type = get_current_agent_type()
   agent_status = get_agent_status(agent_type, project_path)
   render_agent_status_card(agent_status)
   ```

#### 任务 5：项目进度监控-实时刷新（P3）

1. **添加自动刷新组件**
   ```python
   def auto_refresh(interval_ms: int = 30000):
       """自动刷新页面"""
       components.html(f"""
           <script>
               setTimeout(() => window.parent.location.reload(), {interval_ms});
           </script>
       """, height=0)
   ```

2. **添加手动刷新按钮**
   ```python
   if st.button("🔄 刷新"):
       st.rerun()
   ```

3. **添加刷新间隔设置**
   ```python
   refresh_interval = st.select_slider(
       "刷新间隔",
       options=[10, 30, 60, 120],
       value=30
   )
   ```

---

## 依赖关系

```
依赖图:

P0: 开发者控制台改名 ──→ 完成
P1: 首页快速启动改进 ──→ 完成

P2: 项目进度监控-基础版
    ├──→ P3: Agent差异化
    └──→ P3: 实时刷新
         └──→ 完成
```

**依赖说明**：
- P0、P1 任务相互独立，可并行执行
- P3 任务依赖 P2 完成
- 建议按优先级顺序执行

---

## 风险评估

### 风险矩阵

| 风险 | 可能性 | 影响 | 等级 | 缓解措施 |
|------|--------|------|------|----------|
| Webhook API 兼容性 | 中 | 中 | 🟡 | 添加版本检查和回退逻辑 |
| Git 命令执行失败 | 低 | 低 | 🟢 | 捕获异常，返回默认值 |
| 大型项目性能问题 | 中 | 中 | 🟡 | 添加缓存和分页 |
| Agent 状态 API 不稳定 | 中 | 低 | 🟢 | 添加超时和重试 |
| Streamlit 刷新导致状态丢失 | 低 | 中 | 🟡 | 使用 session_state 持久化 |

### 详细风险分析

#### 1. Webhook API 兼容性

**风险描述**：不同版本的 OpenClaw Gateway 可能有不同的 API 格式。

**缓解措施**：
- 检测 Gateway 版本
- 提供多种 API 格式支持
- 添加详细的错误日志

#### 2. 大型项目性能问题

**风险描述**：大型项目的文件统计可能耗时较长。

**缓解措施**：
- 限制文件扫描深度
- 使用异步加载
- 添加进度指示器
- 缓存结果

#### 3. Streamlit 刷新导致状态丢失

**风险描述**：自动刷新可能导致用户输入丢失。

**缓解措施**：
- 使用 `st.session_state` 持久化关键状态
- 提供暂停刷新选项
- 保存草稿

---

## 验收标准

### 1. 开发者控制台改名

| 验收项 | 预期结果 | 测试方法 |
|--------|----------|----------|
| 侧边栏显示 | 显示"🖥️ 调试日志" | 启动 Dashboard，检查侧边栏 |
| 页面标题 | 显示"🖥️ 调试日志" | 点击进入页面，检查标题 |
| 设置页面 | 显示"调试日志"开关 | 进入设置页面，检查文本 |

### 2. 首页快速启动改进

| 验收项 | 预期结果 | 测试方法 |
|--------|----------|----------|
| 使用全局 Agent | 启动时使用设置的主 Agent | 设置主 Agent 为 OpenClaw，点击快速启动 |
| 自动切换工作区 | 启动后当前工作区变更 | 点击其他工作区的启动按钮，检查是否切换 |
| Webhook 成功响应 | `{"ok": true}` 识别为成功 | 模拟 Webhook 响应，检查 toast 通知 |
| 离线提示 | Gateway 未运行时显示错误 | 停止 Gateway，点击快速启动 |

### 3. 项目进度实时监控

| 验收项 | 预期结果 | 测试方法 |
|--------|----------|----------|
| 假设统计 | 显示正确数量和状态 | 创建假设，检查统计 |
| 学习记录 | 显示最近学习 | 添加学习记录，检查显示 |
| Git 状态 | 显示分支和更改 | 修改文件，检查状态 |
| Agent 差异化 | 不同 Agent 显示不同信息 | 切换主 Agent，检查显示 |
| 自动刷新 | 定时刷新数据 | 等待刷新间隔，检查更新 |
| 手动刷新 | 点击刷新按钮更新 | 点击刷新，检查更新 |

### 集成测试清单

- [ ] 启动 Dashboard，检查所有页面加载正常
- [ ] 设置主 Agent，检查首页显示正确
- [ ] 点击快速启动，检查工作区切换
- [ ] 修改假设状态，检查进度更新
- [ ] 提交 Git 更改，检查状态变化
- [ ] 切换主 Agent，检查进度面板变化
- [ ] 启用自动刷新，检查定时更新

---

## 附录

### 相关文件清单

| 文件 | 说明 |
|------|------|
| `src/aop/dashboard/app.py` | Dashboard 主应用 |
| `src/aop/dashboard/logger.py` | 日志处理器 |
| `src/aop/dashboard/streaming.py` | 流式输出支持 |
| `src/aop/primary/workspace.py` | 工作区管理 |
| `src/aop/workflow/hypothesis.py` | 假设管理 |

### 参考资料

- [Streamlit 文档](https://docs.streamlit.io/)
- [AOP 架构设计](../README.md)
- [OpenClaw Gateway API](https://github.com/open-claw/open-claw)

---

> 文档维护：AOP 开发团队  
> 最后更新：2026-03-11

---

## 快速复制指南

由于无法直接写入 `G:\docker\aop\docs\` 目录，请将此文件内容复制并手动保存到：

```
G:\docker\aop\docs\dashboard-improvement-plan-2026-03-11.md
```

或者使用以下命令从工作区复制：

```bash
cp ~/.openclaw/workspace/dashboard-improvement-plan-2026-03-11.md G:/docker/aop/docs/
```
