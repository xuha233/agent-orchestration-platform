# OpenClaw 集成指南

本文档说明如何在 OpenClaw 中使用 AOP 命令系统。

## 快速开始

当主 Agent 设置为 OpenClaw 时，可以通过以下命令格式与 AOP 系统交互。

## 命令格式

支持三种命令前缀：

```
-aop <command> [args]    # 标准格式
aop <command> [args]     # 简写格式
@aop <command> [args]    # @ 提及格式
```

## 支持的命令

### run - 运行任务

启动一个开发任务，让 Agent 按流程执行。

```
-aop run 实现用户登录功能
aop run --task "添加分页查询"
@aop run 修复登录页面的样式问题
```

### review - 代码审查

对代码进行审查，支持指定关注点。

```
-aop review 检查安全性问题
aop review 关注性能优化
@aop review 检查这个 PR 的代码质量
```

### hypothesis - 假设管理

创建和管理假设，用于实验性开发。

```
-aop hypothesis create "如果添加 Redis 缓存，API 响应时间将降低 50%"
aop hypothesis test H001
@aop hypothesis list
```

子命令：
- `create <statement>` - 创建新假设
- `test <id>` - 测试假设
- `list` - 列出所有假设
- `resolve <id>` - 标记假设已解决

### status - 查看状态

查看当前项目和 Agent 状态。

```
-aop status
aop status
@aop status
```

### dashboard - Dashboard 操作

打开或控制 AOP Dashboard。

```
-aop dashboard open
aop dashboard logs
@aop dashboard clear
```

## 使用示例

### 场景 1：启动新任务

```
用户: -aop run 实现用户注册功能
OpenClaw: 好的，我来启动任务...
[调用 aop run --task "实现用户注册功能"]
任务已提交，Dashboard 监听中...
```

### 场景 2：代码审查

```
用户: -aop review 检查这个模块的安全性
OpenClaw: 收到，开始代码审查...
[调用 aop review -p "检查这个模块的安全性"]
审查结果：
- 发现 2 个潜在安全问题
- 建议添加输入验证
```

### 场景 3：创建假设

```
用户: -aop hypothesis create "使用 WebSocket 可以提高实时通信效率"
OpenClaw: 假设已创建：H003
状态：待验证
建议验证方法：对比测试
```

## 与 Dashboard 的关系

当使用 AOP 命令时：

1. 命令会被解析并提交到 Dashboard 监听器
2. Dashboard 显示命令执行状态
3. 结果可在 Dashboard 的「项目记忆」页面查看

## 注意事项

- 命令参数支持引号包裹，适用于包含空格的内容
- 不支持的命令会提示帮助信息
- 命令执行是异步的，不会阻塞对话

## 进阶用法

### 组合命令

可以在一条消息中包含多个命令：

```
-aop status && -aop review 快速检查
```

### 任务模板

常用任务可以保存为模板：

```
-aop run template:daily-check
-aop run template:deploy
```

## 故障排除

**命令无响应**

1. 检查 Dashboard 是否运行：`aop status`
2. 查看日志：`aop dashboard logs`

**命令格式错误**

确保使用正确的命令格式，参考上面的示例。
