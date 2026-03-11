# AOP 跨平台兼容性检查报告

**检查日期**: 2026-03-11  
**项目路径**: G:\docker\aop  
**检查范围**: src/, tests/

---

## 总体评估

| 指标 | 评分 | 说明 |
|------|------|------|
| **整体兼容性** | ⭐⭐⭐⭐☆ (良好) | 项目已经做了大量的跨平台处理，但仍有一些问题需要修复 |
| **路径处理** | ⭐⭐⭐⭐☆ | 主要使用 `pathlib.Path` 和 `os.path.join`，但有少量硬编码 |
| **进程管理** | ⭐⭐⭐⭐☆ | 有完善的跨平台进程终止逻辑，但 `shell=True` 使用需审查 |
| **平台检测** | ⭐⭐⭐⭐⭐ | `sys.platform` 检测使用正确，覆盖 Windows/macOS/Linux |
| **临时文件** | ⭐⭐⭐⭐⭐ | 正确使用 `tempfile` 模块 |
| **测试代码** | ⭐⭐⭐☆☆ | 测试代码中有硬编码路径 |

---

## 问题列表（按严重程度排序）

### 🔴 高优先级问题

#### 问题 1: 测试代码硬编码 Unix 风格路径

**文件位置**: 
- `tests/core/adapter/test_shim.py:62`
- `tests/test_primary_agent.py:26,34,43,50`
- `tests/report/test_formatters.py:13`

**问题描述**:
测试代码中硬编码了 `/tmp/` 路径，这在 Windows 上不存在，会导致测试失败。

**代码示例**:
```python
# tests/core/adapter/test_shim.py:62
artifact_path="/tmp/artifacts",

# tests/test_primary_agent.py:26
ctx = AgentContext(workspace_path=Path("/tmp/test"))

# tests/report/test_formatters.py:13
artifact_root: str = "/tmp/artifacts/test-task-001"
```

**影响平台**: Windows

**修复建议**:
```python
# 使用 tempfile 或 os.path.join(tempfile.gettempdir(), "artifacts")
import tempfile
artifact_path = os.path.join(tempfile.gettempdir(), "artifacts")

# 或使用 pathlib
from pathlib import Path
workspace_path = Path(tempfile.gettempdir()) / "test"
```

---

#### 问题 2: Dashboard 启动使用 `shell=True` 执行平台特定命令

**文件位置**: `src/aop/dashboard/__init__.py:70,90`

**问题描述**:
使用 `shell=True` 执行 shell 命令存在安全风险，且命令字符串拼接不够安全。

**代码示例**:
```python
# Line 70
subprocess.run(full_cmd, shell=True)

# Line 90
cmd = f'nohup "{sys.executable}" -m streamlit run "{app_path}"...'
subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
```

**影响平台**: 全平台

**修复建议**:
对于 Windows，使用列表形式参数避免 shell 注入：
```python
# Windows: 使用 subprocess.Popen 列表参数
subprocess.Popen(
    [sys.executable, "-m", "streamlit", "run", str(app_path),
     "--server.port", str(port), "--server.headless", "true"],
    creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0
)

# Unix: 使用 nohup 时仍需 shell=True，但确保命令字符串安全
# 或考虑使用 python-daemon 库实现后台运行
```

---

### 🟡 中优先级问题

#### 问题 3: Windows 终端启动使用字符串拼接命令

**文件位置**: `src/aop/dashboard/app.py:1119-1123, 1336-1340`

**问题描述**:
Windows 终端启动使用字符串拼接构建命令，可能导致引号转义问题和注入风险。

**代码示例**:
```python
# Line 1119-1123
cmd = f'openclaw tui --session {session_name} --message "{safe_msg}"'
subprocess.Popen(
    f'start "AOP 敏捷教练 - {safe_title}" cmd /k "{cmd}"',
    shell=True
)

# Line 1336-1340
subprocess.Popen(
    'start "AOP 敏捷教练 - ' + project_name + '" powershell -NoExit -ExecutionPolicy Bypass -File "' + ps1_file + '"',
    shell=True
)
```

**影响平台**: Windows

**修复建议**:
考虑使用更安全的方式启动新终端窗口：
```python
import subprocess

# 方案1: 使用 creationflags 创建新窗口
if sys.platform == "win32":
    subprocess.Popen(
        ["cmd", "/c", "start", "AOP Dashboard", "powershell", "-NoExit", 
         "-ExecutionPolicy", "Bypass", "-File", ps1_file],
        creationflags=subprocess.CREATE_NEW_CONSOLE
    )

# 方案2: 使用 PowerShell 启动脚本（当前已实现部分）
# 保持现有的 PowerShell 脚本方式，但确保参数安全
```

---

#### 问题 4: 路径分隔符硬编码替换

**文件位置**: `src/aop/core/engine/review.py:109`

**问题描述**:
硬编码替换路径分隔符，应使用 `os.path.normpath()` 或 `pathlib.Path`。

**代码示例**:
```python
# Line 109
_normalize_for_dedupe(item.evidence.file.replace("\\", "/")),
```

**影响平台**: 全平台（轻微）

**修复建议**:
```python
import os
# 或使用 pathlib
from pathlib import Path
normalized_path = str(Path(item.evidence.file).as_posix())
# 或
normalized_path = os.path.normpath(item.evidence.file).replace(os.sep, "/")
```

---

#### 问题 5: macOS/Linux 终端启动命令构建

**文件位置**: `src/aop/dashboard/app.py:1364-1396`

**问题描述**:
macOS 和 Linux 终端启动逻辑较为复杂，使用了字符串拼接构建 AppleScript 和 bash 命令。

**代码示例**:
```python
# macOS
apple_script = 'tell application "Terminal" to do script "cd \"' + project_path + '\" && ' + full_cmd + '"'
subprocess.Popen(["osascript", "-e", apple_script])

# Linux
subprocess.Popen([
    terminal, "--working-directory", project_path, "--", "bash", "-c",
    full_cmd + "; exec bash"
])
```

**影响平台**: macOS, Linux

**修复建议**:
使用列表形式参数，并确保路径正确转义：
```python
# macOS: 使用 subprocess.run 列表参数
subprocess.Popen([
    "osascript", "-e",
    f'tell application "Terminal" to do script "cd \'{project_path}\' && {full_cmd}"'
])

# Linux: 已经使用列表形式，但确保命令安全
# 当前实现基本正确，只需确保 full_cmd 中没有用户输入的特殊字符
```

---

### 🟢 低优先级问题

#### 问题 6: 兼容性模块路径转换

**文件位置**: `src/aop/core/compat/__init__.py:137-138`

**问题描述**:
`normalize_path` 方法简单替换路径分隔符，可能不处理所有边缘情况。

**代码示例**:
```python
# Line 137-138
if self.is_windows():
    return path.replace("/", "\\")
return path.replace("\\", "/")
```

**影响平台**: 全平台（轻微）

**修复建议**:
```python
import os
from pathlib import Path

def normalize_path(self, path: str) -> str:
    """Normalize path separators for the current platform."""
    # 使用 pathlib 进行更可靠的路径规范化
    return str(Path(path))
    # 或
    return os.path.normpath(path)
```

---

## ✅ 良好实践（值得肯定）

### 1. 跨平台进程终止

**文件位置**: `src/aop/core/adapter/shim.py:275-320`

项目正确实现了跨平台的进程终止逻辑：

```python
def _terminate_process(self, process: subprocess.Popen[str]) -> None:
    """Terminate a process in a cross-platform way."""
    if sys.platform == "win32":
        process.terminate()
    else:
        # POSIX: send signal to process group
        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
```

### 2. 临时文件处理

**文件位置**: 多处

项目正确使用 `tempfile` 模块处理临时文件：
- `src/aop/core/adapter/shim.py:145` - 使用 `tempfile.gettempdir()`
- `src/aop/agent/orchestrator.py:616` - 使用 `tempfile.NamedTemporaryFile`
- `src/aop/dashboard/app.py:1260` - 使用 `tempfile.gettempdir()`

### 3. 平台检测

**文件位置**: 多处

项目正确使用 `sys.platform` 进行平台检测：
- `if sys.platform == "win32":` - Windows 检测
- `elif sys.platform == "darwin":` - macOS 检测
- `else:` - Linux/Unix 检测

### 4. 路径处理（主要代码）

**文件位置**: 多处

主要代码正确使用 `pathlib.Path` 和 `os.path.join`：
- `src/aop/dashboard/app.py` - 广泛使用 `Path()`
- `src/aop/core/adapter/shim.py` - 使用 `Path` 对象

### 5. 二进制查找

**文件位置**: `src/aop/orchestrator/claude_code_orchestrator.py:49-75`

项目实现了跨平台的二进制文件查找逻辑，处理了 Windows 上 `.cmd`/`.bat` 扩展名的问题：

```python
def _find_binary(binary_name: str) -> Optional[str]:
    result = shutil.which(binary_name)
    if result:
        return result
    
    if platform.system() == "Windows":
        # 检查 PATHEXT 环境变量指定的扩展名
        pathext = os.environ.get("PATHEXT", ".COM;.EXE;.BAT;.CMD").split(";")
        for npm_path in NPM_GLOBAL_PATHS:
            for ext in pathext:
                candidate = npm_path / f"{binary_name}{ext}"
                if candidate.exists():
                    return str(candidate)
```

---

## 需要优先修复的问题

| 优先级 | 问题 | 文件 | 影响 |
|--------|------|------|------|
| 🔴 高 | 测试代码硬编码 `/tmp/` 路径 | tests/ | 测试在 Windows 上失败 |
| 🔴 高 | `shell=True` 安全风险 | dashboard/__init__.py | 潜在安全漏洞 |
| 🟡 中 | Windows 终端启动字符串拼接 | dashboard/app.py | 引号转义问题 |

---

## 修复建议总结

1. **测试代码**: 将所有硬编码的 `/tmp/` 路径改为使用 `tempfile.gettempdir()` 或 `pathlib.Path(tempfile.gettempdir())`

2. **Dashboard 启动**: 考虑使用 `subprocess.CREATE_NEW_CONSOLE` 标志代替 `cmd /c start`，或保持 PowerShell 脚本方式但确保参数安全

3. **shell=True 使用**: 尽量避免 `shell=True`，使用列表形式参数传递命令

4. **路径规范化**: 使用 `pathlib.Path` 或 `os.path.normpath()` 代替手动替换路径分隔符

---

## 结论

AOP 项目在跨平台兼容性方面已经做了大量工作，主要功能代码的兼容性良好。主要问题集中在：

1. **测试代码** - 硬编码 Unix 风格路径，需要优先修复
2. **终端启动** - 字符串拼接命令，存在潜在安全风险
3. **shell=True** - 应谨慎使用，考虑更安全的替代方案

建议按优先级逐步修复这些问题，以确保项目在 Windows、macOS 和 Linux 上都能正常运行。

---

**报告生成者**: AOP 跨平台兼容性检查助手  
**生成时间**: 2026-03-11

---

## 修复记录

### 已修复的问题 (2026-03-11)

#### ✅ 测试代码硬编码路径问题

**修复文件**:
- `tests/core/adapter/test_shim.py`
- `tests/test_primary_agent.py`
- `tests/report/test_formatters.py`

**修复内容**:
1. 添加了 `import os` 和 `import tempfile` 导入
2. 将硬编码的 `/tmp/` 路径改为使用 `tempfile.gettempdir()` 跨平台获取临时目录

**修复前**:
```python
artifact_path="/tmp/artifacts"
workspace_path=Path("/tmp/test")
artifact_root: str = "/tmp/artifacts/test-task-001"
```

**修复后**:
```python
artifact_path=os.path.join(tempfile.gettempdir(), "artifacts")
workspace_path=Path(tempfile.gettempdir()) / "test"
artifact_root: str = os.path.join(tempfile.gettempdir(), "artifacts", "test-task-001")
```

**验证结果**: 所有 47 个相关测试用例通过

---

## 待修复问题

以下问题仍需在后续版本中修复：

| 优先级 | 问题 | 文件 | 状态 |
|--------|------|------|------|
| ~~🔴 高~~ | 测试代码硬编码 `/tmp/` 路径 | tests/ | ✅ 已修复 |
| 🔴 高 | `shell=True` 安全风险 | dashboard/__init__.py | ⏳ 待修复 |
| 🟡 中 | Windows 终端启动字符串拼接 | dashboard/app.py | ⏳ 待修复 |
| 🟢 低 | 路径分隔符硬编码替换 | core/engine/review.py | ⏳ 待修复 |

---

**报告更新时间**: 2026-03-11
