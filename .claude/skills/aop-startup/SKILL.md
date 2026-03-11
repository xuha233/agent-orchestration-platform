---
name: aop-startup
description: "AOP 启动流程 - 当用户说 启动、开始、init、status 时触发。显示项目状态和环境检查。"
user-invocable: true
disable-model-invocation: false
---

# AOP 启动流程

执行以下检查并显示状态面板：

## Step 1: 环境检查

检查 AOP CLI、Git、Python 是否可用。

## Step 2: 项目检测

检测 .aop 目录是否存在，读取项目记忆。

## Step 3: 显示状态面板

显示项目状态、环境信息、活跃假设数量等。

## 未初始化项目处理

如果 .aop 目录不存在，提示用户是否执行 aop init 初始化。