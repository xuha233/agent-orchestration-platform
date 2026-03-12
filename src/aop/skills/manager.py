"""
Skill Manager - 技能管理器

负责加载、匹配和管理所有技能。
支持热加载，无需重启即可更新技能。
"""

from pathlib import Path
from typing import Dict, List, Optional, Type, Any
import importlib
import sys
from dataclasses import dataclass

from .base import SkillBase, SkillMeta, SkillContext, SkillPriority


@dataclass
class SkillMatch:
    """技能匹配结果"""
    skill: SkillBase
    relevance: float  # 0.0 - 1.0
    matched_triggers: List[str]


class SkillManager:
    """
    技能管理器
    
    负责技能的加载、匹配和上下文注入。
    
    使用示例：
        manager = SkillManager(Path("skills"))
        
        # 查找匹配的技能
        context = SkillContext(task="我想做一个电商系统")
        matching = manager.find_matching_skills(context)
        
        # 注入技能上下文到 Agent prompt
        prompt = manager.inject_skill_context(context)
    """
    
    def __init__(self, skills_dir: Optional[Path] = None):
        """
        初始化技能管理器
        
        Args:
            skills_dir: 技能目录路径，如果为 None 则不自动加载
        """
        self.skills: Dict[str, SkillBase] = {}
        self._skills_dir = skills_dir
        
        if skills_dir:
            self._load_skills(skills_dir)
    
    def _load_skills(self, skills_dir: Path) -> None:
        """
        加载技能目录中的所有技能
        
        Args:
            skills_dir: 技能目录路径
        """
        if not skills_dir.exists():
            return
        
        # 扫描目录中的 Python 模块
        for item in skills_dir.iterdir():
            if item.is_file() and item.suffix == ".py" and item.stem != "__init__":
                self._load_skill_from_module(item.stem, skills_dir)
            elif item.is_dir():
                # 支持目录形式的技能（包含 SKILL.md）
                skill_file = item / "skill.py"
                if skill_file.exists():
                    self._load_skill_from_module("skill", item)
    
    def _load_skill_from_module(self, module_name: str, base_path: Path) -> None:
        """
        从模块加载技能
        
        Args:
            module_name: 模块名
            base_path: 模块所在目录
        """
        try:
            # 动态导入模块
            if str(base_path) not in sys.path:
                sys.path.insert(0, str(base_path))
            
            # 重新加载以支持热更新
            if module_name in sys.modules:
                module = importlib.reload(sys.modules[module_name])
            else:
                module = importlib.import_module(module_name)
            
            # 查找所有 SkillBase 子类
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, SkillBase)
                    and attr is not SkillBase
                ):
                    skill_instance = attr()
                    meta = skill_instance.get_meta()
                    self.skills[meta.name] = skill_instance
                    
        except Exception as e:
            # 加载失败时记录日志，但不中断
            import traceback
            print(f"[SkillManager] Failed to load skill from {module_name}: {e}")
            traceback.print_exc()
    
    def register_skill(self, skill: SkillBase) -> None:
        """
        注册技能
        
        Args:
            skill: 技能实例
        """
        meta = skill.get_meta()
        self.skills[meta.name] = skill
    
    def unregister_skill(self, skill_name: str) -> bool:
        """
        注销技能
        
        Args:
            skill_name: 技能名称
            
        Returns:
            bool: 是否成功注销
        """
        if skill_name in self.skills:
            del self.skills[skill_name]
            return True
        return False
    
    def reload_skills(self) -> None:
        """
        重新加载所有技能（热更新）
        """
        if self._skills_dir:
            self.skills.clear()
            self._load_skills(self._skills_dir)
    
    def get_skill(self, skill_name: str) -> Optional[SkillBase]:
        """
        获取技能
        
        Args:
            skill_name: 技能名称
            
        Returns:
            Optional[SkillBase]: 技能实例，如果不存在则返回 None
        """
        return self.skills.get(skill_name)
    
    def get_skill_prompt(self, skill_name: str) -> Optional[str]:
        """
        获取技能的完整提示词
        
        Args:
            skill_name: 技能名称
            
        Returns:
            Optional[str]: 技能提示词，如果技能不存在则返回 None
        """
        skill = self.get_skill(skill_name)
        if skill:
            return skill.get_prompt()
        return None
    
    def find_matching_skills(self, context: SkillContext) -> List[SkillMatch]:
        """
        找到所有匹配当前上下文的技能
        
        Args:
            context: 当前执行上下文
            
        Returns:
            List[SkillMatch]: 匹配的技能列表，按优先级和相关性排序
        """
        matches: List[SkillMatch] = []
        
        for skill in self.skills.values():
            if skill.matches(context):
                # 计算相关性分数
                meta = skill.get_meta()
                matched_triggers = [
                    t for t in meta.triggers
                    if t.lower() in context.task.lower()
                ]
                
                # 相关性 = 匹配的触发词数量 / 总触发词数量
                relevance = len(matched_triggers) / len(meta.triggers) if meta.triggers else 1.0
                
                matches.append(SkillMatch(
                    skill=skill,
                    relevance=relevance,
                    matched_triggers=matched_triggers,
                ))
        
        # 按优先级和相关性排序
        matches.sort(
            key=lambda m: (m.skill.get_meta().priority.value, m.relevance),
            reverse=True
        )
        
        return matches
    
    def inject_skill_context(self, context: SkillContext) -> str:
        """
        注入匹配技能的上下文到 Agent prompt
        
        Args:
            context: 当前执行上下文
            
        Returns:
            str: 注入的上下文文本
        """
        matches = self.find_matching_skills(context)
        
        if not matches:
            return ""
        
        parts = []
        parts.append("<SKILLS_CONTEXT>")
        parts.append("以下是当前任务相关的技能指南。请按照这些指南执行任务。")
        parts.append("")
        
        for match in matches:
            skill = match.skill
            meta = skill.get_meta()
            
            parts.append(f"## 技能: {meta.name}")
            parts.append(f"**描述**: {meta.description}")
            parts.append(f"**优先级**: {meta.priority.name}")
            
            if match.matched_triggers:
                parts.append(f"**匹配触发词**: {', '.join(match.matched_triggers)}")
            
            parts.append("")
            
            # 铁律
            iron_law = skill.get_iron_law()
            if iron_law:
                parts.append(f"### ⚠️ Iron Law (强制执行)")
                parts.append(f"```")
                parts.append(iron_law)
                parts.append(f"```")
                parts.append("")
            
            # 技能 prompt
            parts.append("### 详细指南")
            parts.append(skill.get_prompt())
            parts.append("")
            
            # 反模式
            red_flags = skill.get_red_flags()
            if red_flags:
                parts.append("### 🚫 Red Flags (应避免)")
                for flag in red_flags:
                    parts.append(f"- {flag}")
                parts.append("")
            
            # 检查清单
            checklist = skill.get_checklist()
            if checklist:
                parts.append("### ✅ 检查清单")
                for item in checklist:
                    parts.append(f"- [ ] {item}")
                parts.append("")
            
            parts.append("---")
            parts.append("")
        
        parts.append("</SKILLS_CONTEXT>")
        
        return "\n".join(parts)
    
    def check_all_red_flags(self, text: str) -> Dict[str, List[str]]:
        """
        检查所有技能的反模式
        
        Args:
            text: 要检查的文本
            
        Returns:
            Dict[str, List[str]]: 技能名 -> 匹配的反模式列表
        """
        results = {}
        for skill in self.skills.values():
            matched = skill.check_red_flags(text)
            if matched:
                results[skill.get_meta().name] = matched
        return results
    
    def get_all_iron_laws(self) -> Dict[str, str]:
        """
        获取所有技能的铁律
        
        Returns:
            Dict[str, str]: 技能名 -> 铁律
        """
        results = {}
        for skill in self.skills.values():
            iron_law = skill.get_iron_law()
            if iron_law:
                results[skill.get_meta().name] = iron_law
        return results
    
    def list_skills(self) -> List[SkillMeta]:
        """
        列出所有技能
        
        Returns:
            List[SkillMeta]: 技能元信息列表
        """
        return [s.get_meta() for s in self.skills.values()]
    
    def __len__(self) -> int:
        return len(self.skills)
    
    def __contains__(self, skill_name: str) -> bool:
        return skill_name in self.skills
