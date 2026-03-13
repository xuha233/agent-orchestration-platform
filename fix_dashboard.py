import re

# 读取文件
with open('src/aop/dashboard/app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 替换函数
old_func = '''def read_aop_file(filename: str) -> Optional[str]:
    """读取 .aop 目录下的文件内容（带文件锁处理）"""
    aop_dir = get_aop_dir()
    file_path = aop_dir / filename
    if file_path.exists():
        try:
            return file_path.read_text(encoding="utf-8")
        except PermissionError:
            # 文件被其他进程锁定，返回 None
            return None
        except Exception:
            return None
    return None'''

new_func = '''def read_aop_file(filename: str) -> Optional[str]:
    """读取 .aop 目录下的文件内容（带文件锁处理）
    
    支持两种存储格式：
    1. 文件格式: .aop/hypotheses.json
    2. 目录格式: .aop/hypotheses.json/hypotheses.json (CLI PersistenceManager)
    """
    aop_dir = get_aop_dir()
    file_path = aop_dir / filename
    
    # 如果是目录，尝试读取目录内的同名文件
    if file_path.is_dir():
        inner_file = file_path / filename
        if inner_file.exists():
            file_path = inner_file
        else:
            return None
    
    if file_path.exists():
        try:
            return file_path.read_text(encoding="utf-8")
        except PermissionError:
            # 文件被其他进程锁定，返回 None
            return None
        except Exception:
            return None
    return None'''

content = content.replace(old_func, new_func)

# 写回文件
with open('src/aop/dashboard/app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Dashboard read_aop_file function updated')
