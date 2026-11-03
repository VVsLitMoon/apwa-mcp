"""APWA MCP Server - Skill Registry.

Central registry that holds all 14 parsed SkillDefs, maintains the dependency
graph, and generates MCP Tool definitions.
"""

from collections import deque
from pathlib import Path

from mcp.types import Tool

from skill_parser import (
    SkillDef,
    parse_all_skills,
    discover_skill_files,
)
from config import TOTAL_SKILLS


class SkillRegistry:
    """Holds all parsed SkillDefs, dependency graph, and tool generation."""

    def __init__(self, skill_dir: str | None = None):
        self.skills: dict[int, SkillDef] = {}
        self.dep_graph: dict[int, list[int]] = {}
        self.reverse_deps: dict[int, list[int]] = {}
        self._load_all(skill_dir)
        self._build_dep_graph()

    def _load_all(self, skill_dir: str | None) -> None:
        if skill_dir:
            files = discover_skill_files(skill_dir)
        else:
            files = discover_skill_files()
        for f in files:
            from skill_parser import parse_skill_file
            skill = parse_skill_file(f)
            self.skills[skill.skill_id] = skill

    def _build_dep_graph(self) -> None:
        for sid, skill in self.skills.items():
            self.dep_graph[sid] = list(skill.dependencies_must)
        for sid in self.skills:
            self.reverse_deps[sid] = []
        for sid, deps in self.dep_graph.items():
            for dep_id in deps:
                if dep_id in self.reverse_deps:
                    self.reverse_deps[dep_id].append(sid)

    def get_tool_list(self):
        from mcp.types import Tool
        tools = []
        for sid in sorted(self.skills.keys()):
            skill = self.skills[sid]
            tools.append(Tool(
                name=f'skill_{sid:02d}',
                title=skill.skill_name,
                description=skill.short_description,
                inputSchema=skill.tool_input_schema,
            ))
        tools.append(Tool(
            name='run_pipeline', title='Pipeline Execution',
            description='按依赖拓扑序串联执行多个Skill',
            inputSchema={'type': 'object', 'properties': {
                'start_skill': {'type': 'integer', 'description': '起始Skill编号(1-14)', 'minimum': 1, 'maximum': 14},
                'end_skill': {'type': 'integer', 'description': '终止Skill编号(1-14)', 'minimum': 1, 'maximum': 14},
                'initial_input': {'type': 'object', 'description': '首个Skill的初始输入数据'},
            }, 'required': ['start_skill', 'end_skill', 'initial_input']},
        ))
        tools.append(Tool(
            name='checkpoint_decision', title='Checkpoint Decision',
            description='断点决策:skip/rerun/continue',
            inputSchema={'type': 'object', 'properties': {
                'skill_id': {'type': 'integer', 'description': 'Skill编号(1-14)', 'minimum': 1, 'maximum': 14},
                'action': {'type': 'string', 'enum': ['skip', 'rerun', 'continue'], 'description': 'skip/rerun/continue'},
            }, 'required': ['skill_id', 'action']},
        ))
        tools.append(Tool(
            name='confirm_skill_01', title='Confirm Skill-01 Requirements',
            description='确认Skill-01产出的需求基线，解锁下游所有Skill',
            inputSchema={'type': 'object', 'properties': {
                'requirements_baseline': {'type': 'object', 'description': '需求基线对象'},
                'template_analysis': {'type': 'object', 'description': '模板分析结果(可选)'},
                'workspace_files_summary': {'type': 'object', 'description': '工作空间文件扫描结果(可选)'},
                'environment_report': {'type': 'object', 'description': '环境检查报告(可选)'},
                'output_text': {'type': 'string', 'description': '自由文本确认摘要'},
                'completeness_flag': {'type': 'string', 'enum': ['green', 'yellow', 'red'], 'description': '完整度标识'},
                'followup_questions': {'type': 'array', 'description': '待澄清问题列表(可选)'},
                'auto_fill_notes': {'type': 'string', 'description': '自动补全记录(可选)'},
            }, 'required': ['requirements_baseline']},
        ))
        tools.append(Tool(
            name='pipeline_status', title='Pipeline Status',
            description='查看全部14个Skill的执行状态',
            inputSchema={'type': 'object', 'properties': {}, 'required': []},
        ))
        tools.append(Tool(
            name='generate_delivery', title='Generate Delivery Package',
            description='生成最终交付包',
            inputSchema={'type': 'object', 'properties': {}, 'required': []},
        ))
        return tools

    def get_topological_order(self, start: int, end: int) -> list[int]:
        relevant: set[int] = set()
        to_visit = [start]
        while to_visit:
            sid = to_visit.pop()
            if sid in relevant:
                continue
            relevant.add(sid)
            for dep_on_me in self.reverse_deps.get(sid, []):
                if dep_on_me <= end:
                    to_visit.append(dep_on_me)
        changed = True
        while changed:
            changed = False
            for sid in list(relevant):
                for dep_id in self.dep_graph.get(sid, []):
                    if dep_id >= start and dep_id not in relevant:
                        relevant.add(dep_id)
                        changed = True
        relevant = {s for s in relevant if start <= s <= end}
        in_degree = {}
        for sid in relevant:
            deps_in_range = [d for d in self.dep_graph.get(sid, []) if d in relevant]
            in_degree[sid] = len(deps_in_range)
        queue = deque([s for s in relevant if in_degree.get(s, 0) == 0])
        result = []
        while queue:
            queue_sorted = sorted(queue)
            queue = deque(queue_sorted)
            sid = queue.popleft()
            result.append(sid)
            for rev_id in self.reverse_deps.get(sid, []):
                if rev_id in relevant and rev_id in in_degree:
                    in_degree[rev_id] -= 1
                    if in_degree[rev_id] == 0:
                        queue.append(rev_id)
        if len(result) != len(relevant):
            for sid in sorted(relevant - set(result)):
                result.append(sid)
        return result

    def get_skill(self, skill_id: int):
        return self.skills.get(skill_id)

    def get_must_dependencies(self, skill_id: int) -> list[int]:
        return self.dep_graph.get(skill_id, [])

    def get_optional_dependencies(self, skill_id: int) -> list[int]:
        skill = self.skills.get(skill_id)
        if skill:
            return list(skill.dependencies_optional)
        return []

    def get_all_dependencies(self, skill_id: int) -> list[int]:
        skill = self.skills.get(skill_id)
        if not skill:
            return []
        return sorted(set(skill.dependencies_must + skill.dependencies_optional))

    def __len__(self) -> int:
        return len(self.skills)
