"""APWA MCP Server - Skill Markdown Parser.

Parses ../Skill-XX-*.md files into structured SkillDef dataclasses,
extracting the 7-part structure and converting to MCP-compatible formats.
"""

import re
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from config import SKILL_DIR, TOTAL_SKILLS


@dataclass
class SkillDef:
    """Parsed representation of one Skill .md file.

    Separates 'meta' (registered in MCP Tool) from 'execution' (used by handler at call time).
    """
    skill_id: int
    skill_name: str                          # Chinese name from title
    file_path: str                           # Absolute path to source .md

    # --- Meta (registered to MCP Tool) ---
    short_description: str = ""              # 20-50 char one-line summary
    dependencies_must: list[int] = field(default_factory=list)
    dependencies_optional: list[int] = field(default_factory=list)
    tool_input_schema: dict = field(default_factory=dict)   # Slim JSON Schema (≤5 fields)

    # --- Execution (used by handler at call time) ---
    description_raw: str = ""                # Full section 一 text
    full_input_schema: dict = field(default_factory=dict)    # Complete JSON Schema from section 三
    output_schema: dict = field(default_factory=dict)        # Expected output structure from section 四
    system_prompt: str = ""
    failure_strategies: str = ""
    examples: str = ""
    raw_markdown: str = ""


# ---------------------------------------------------------------------------
# File discovery
# ---------------------------------------------------------------------------

def discover_skill_files(base_dir: str | None = None) -> list[str]:
    """Glob ../Skill-*.md, return sorted list of absolute paths."""
    base = Path(base_dir) if base_dir else SKILL_DIR
    files = sorted(base.glob("Skill-*.md"))
    return [str(f.absolute()) for f in files]


# ---------------------------------------------------------------------------
# Section extraction helpers
# ---------------------------------------------------------------------------

_SECTION_PATTERN = re.compile(
    r"^#{1,3}\s*(一|二|三|四|五|六|七)、(.+)$", re.MULTILINE
)

_SECTION_NAMES = {
    "一": "description",
    "二": "dependencies",
    "三": "input_format",
    "四": "output_format",
    "五": "system_prompt",
    "六": "failure_strategies",
    "七": "examples",
}


def _split_sections(text: str) -> dict[str, str]:
    """Split markdown text into 7 named sections."""
    sections: dict[str, str] = {}
    matches = list(_SECTION_PATTERN.finditer(text))

    for i, match in enumerate(matches):
        num = match.group(1)
        key = _SECTION_NAMES.get(num)
        if key is None:
            continue
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        sections[key] = text[start:end].strip()

    return sections


def _extract_json_block(section_text: str) -> Optional[dict]:
    """Extract the first ```json ... ``` code fence and parse as dict.

    Returns None if no code fence found or JSON is malformed.
    """
    # Match ```json ... ``` (with optional language tag)
    match = re.search(r"```(?:json)?\s*\n(.*?)```", section_text, re.DOTALL)
    if not match:
        return None

    json_text = match.group(1).strip()

    # Remove JS-style // comments
    json_text = re.sub(r"//.*$", "", json_text, flags=re.MULTILINE)
    # Remove trailing commas before closing braces/brackets
    json_text = re.sub(r",(\s*[}\]])", r"\1", json_text)

    try:
        return json.loads(json_text)
    except json.JSONDecodeError:
        # Try to recover: find the outermost { } or [ ]
        brace_start = json_text.find("{")
        bracket_start = json_text.find("[")
        if brace_start >= 0 and (brace_start < bracket_start or bracket_start < 0):
            # Find matching closing brace (naive but works for well-formed)
            depth = 0
            end = brace_start
            for j in range(brace_start, len(json_text)):
                if json_text[j] == "{":
                    depth += 1
                elif json_text[j] == "}":
                    depth -= 1
                    if depth == 0:
                        end = j + 1
                        break
            extracted = json_text[brace_start:end]
        elif bracket_start >= 0:
            depth = 0
            end = bracket_start
            for j in range(bracket_start, len(json_text)):
                if json_text[j] == "[":
                    depth += 1
                elif json_text[j] == "]":
                    depth -= 1
                    if depth == 0:
                        end = j + 1
                        break
            extracted = json_text[bracket_start:end]
        else:
            return None

        try:
            return json.loads(extracted)
        except json.JSONDecodeError:
            return None


# ---------------------------------------------------------------------------
# Dependency parsing (section 二)
# ---------------------------------------------------------------------------

def _build_skill_name_id_map(skill_dir: Path) -> dict[str, int]:
    """Build mapping from Chinese skill name to skill ID from filenames.

    Filename format: Skill-XX-中文名称.md
    """
    name_map: dict[str, int] = {}
    for f in sorted(skill_dir.glob("Skill-*.md")):
        match = re.match(r"Skill-(\d{2})-(.+)\.md", f.name)
        if match:
            sid = int(match.group(1))
            chinese_name = match.group(2)
            name_map[chinese_name] = sid
    return name_map


def _parse_dependencies(section_text: str, name_map: dict[str, int]) -> tuple[list[int], list[int]]:
    """Parse 二、前置依赖 section into must and optional dependency ID lists.

    Expected format:
      - 必须完成：<skill name>（...additional notes...）
      - 可选依赖：<skill name>
    """
    must: list[int] = []
    optional: list[int] = []

    # Try to find skill names in the text
    for chinese_name, sid in name_map.items():
        if chinese_name in section_text:
            # Determine if must or optional
            # Find the position of the name
            pos = section_text.find(chinese_name)
            # Look backwards for context: "必须完成" or "可选依赖"
            preceding = section_text[:pos]
            # Get the line containing this name
            line_start = preceding.rfind("\n")
            if line_start < 0:
                line_start = 0
            context_line = preceding[line_start:]

            if "必须完成" in context_line:
                if sid not in must:
                    must.append(sid)
            elif "可选依赖" in context_line:
                if sid not in optional:
                    optional.append(sid)

    return must, optional


# ---------------------------------------------------------------------------
# Shared helpers (used by both slim and full schema builders)
# ---------------------------------------------------------------------------

def _parse_field_description(raw_value: str) -> tuple[str, str, bool]:
    """Parse a Skill input field value like '必填 - 论文级别' into components.

    Returns: (cleaned_value, description, is_required)
    """
    is_required = "必填" in raw_value
    # Remove the 必填/可选 prefix to get description
    description = re.sub(r"^(必填|可选)\s*[-—–]\s*", "", raw_value).strip()
    return raw_value, description, is_required


# ---------------------------------------------------------------------------
# Meta factories — slim Tool registration
# ---------------------------------------------------------------------------

# Per-skill short descriptions (manual, 20–50 chars each)
_SKILL_SHORT_DESC: dict[int, str] = {
    1: "采集论文需求基线：论文级别、研究领域、目标分数、语言偏好等，自动补全缺失参数",
    2: "领域文献全景扫描：检索热点方向、研究空白、基线方法、核心学术团队",
    3: "生成3-5个分梯度选题方案，四维评估创新点/可行性/文献支撑/难度，支持多轮打磨",
    4: "针对已确认选题的高精度文献检索与深度研读，产出结构化阅读笔记与知识地图",
    5: "将深度研读文献组织为学术叙事式结构化综述初稿，梳理脉络、辨析流派",
    6: "设计严谨可复现的研究方法与实验方案：框架/数据/模型/评估/稳健性全链路",
    7: "根据实验方案自动生成完整可运行的实验代码包（模块化/可配置/有错误处理）",
    8: "在本地沙箱中自动运行实验代码，循环执行-诊断-修复直到所有质量门禁通过",
    9: "对实验产出数据进行深度解读、统计表格与学术图表可视化、结果意义阐释",
    10: "设计完整论文论证骨架与章节大纲（段落级施工蓝图），避免返工",
    11: "将所有上游材料撰写为逻辑连贯、语言严谨的完整论文初稿（非拼接，重整合）",
    12: "以审稿人视角对论文进行五维度评分与诊断，得分低于门槛自动触发修改循环",
    13: "根据评阅报告进行外科手术式定向修改（段落级before/after），产出新版论文",
    14: "出版级学术规范与格式终检：格式/语言/引用/重复率/伦理/交付包完整性",
}


def _build_short_description(skill_id: int) -> str:
    """Return a 20–50 char one-line summary for Tool registration."""
    return _SKILL_SHORT_DESC.get(skill_id, f"Skill {skill_id:02d}")


# Max number of top-level fields to expose in the slim MCP inputSchema
_SLIM_SCHEMA_MAX_FIELDS = 5


def _build_slim_input_schema(full_input_json: dict | None) -> dict:
    """Build a trimmed JSON Schema suitable for MCP Tool registration.

    - Exposes at most _SLIM_SCHEMA_MAX_FIELDS top-level properties.
    - Keeps only core required fields (up to 5).
    - Nested objects become {type: "object", additionalProperties: true}.
    - All remaining raw args go into an opaque 'context' string field.
    """
    if not full_input_json or not isinstance(full_input_json, dict):
        return {"type": "object", "properties": {}, "required": []}

    properties: dict[str, dict] = {}
    required: list[str] = []
    count = 0

    for key, value in full_input_json.items():
        if count >= _SLIM_SCHEMA_MAX_FIELDS:
            break

        prop: dict = {}
        if isinstance(value, str):
            _, description, is_req = _parse_field_description(value)
            prop["type"] = "string"
            prop["description"] = description
            # Keep enum for choice fields
            enum_candidates = re.split(r"\s*/\s*", description)
            enum_values = [e.strip() for e in enum_candidates
                           if 0 < len(e.strip()) < 20]
            if (len(enum_values) >= 2 and len(enum_values) <= 8
                    and all(len(e) < 20 for e in enum_values)
                    and not any("(" in e or "（" in e or "如" in e or "例" in e
                                for e in enum_values)):
                prop["enum"] = enum_values
            if is_req:
                required.append(key)
        elif isinstance(value, bool):
            prop["type"] = "boolean"
            prop["description"] = key
        elif isinstance(value, int):
            prop["type"] = "integer"
            prop["description"] = key
        elif isinstance(value, float):
            prop["type"] = "number"
            prop["description"] = key
        elif isinstance(value, dict):
            # Don't expand nested objects — opaque
            prop["type"] = "object"
            prop["description"] = key
            prop["additionalProperties"] = True
        elif isinstance(value, list):
            prop["type"] = "array"
            prop["description"] = key
        else:
            prop["type"] = "string"
            prop["description"] = str(value)

        properties[key] = prop
        count += 1

    # Always add a 'context' field for everything else
    if "context" not in properties:
        properties["context"] = {
            "type": "string",
            "description": "自由文本 - 用户对论文的任何额外描述、已有想法、准备程度等（含上游Skill输出）",
        }

    schema: dict = {"type": "object", "properties": properties}
    if required:
        schema["required"] = required
    return schema


def _build_full_input_schema(input_json: dict | None) -> dict:
    """Build the complete JSON Schema from section 三 (for handler-side validation).

    This is the same as the old _build_input_schema.
    """
    if not input_json or not isinstance(input_json, dict):
        return {"type": "object", "properties": {}, "required": []}

    properties: dict[str, dict] = {}
    required: list[str] = []

    for key, value in input_json.items():
        prop: dict = {}

        if isinstance(value, str):
            _, description, is_req = _parse_field_description(value)
            prop["type"] = "string"
            prop["description"] = description

            # Enum detection
            enum_candidates = re.split(r"\s*/\s*", description)
            enum_values = [e.strip() for e in enum_candidates
                           if len(e.strip()) < 20 and len(e.strip()) > 0]
            if (len(enum_values) >= 2
                    and len(enum_values) <= 8
                    and all(len(e) < 20 for e in enum_values)
                    and not any("(" in e or "（" in e or "如" in e or "例" in e for e in enum_values)):
                prop["enum"] = enum_values

            if is_req:
                required.append(key)

        elif isinstance(value, bool):
            prop["type"] = "boolean"
            prop["description"] = key
            prop["default"] = value

        elif isinstance(value, int):
            prop["type"] = "integer"
            prop["description"] = key
            prop["default"] = value

        elif isinstance(value, float):
            prop["type"] = "number"
            prop["description"] = key
            prop["default"] = value

        elif isinstance(value, list):
            prop["type"] = "array"
            prop["description"] = key
            if value and isinstance(value[0], dict):
                prop["items"] = {"type": "object"}

        elif isinstance(value, dict):
            prop["type"] = "object"
            prop["description"] = key
            nested = _build_full_input_schema(value)
            prop["properties"] = nested.get("properties", {})

        else:
            prop["type"] = "string"
            prop["description"] = str(value)

        properties[key] = prop

    schema: dict = {
        "type": "object",
        "properties": properties,
    }
    if required:
        schema["required"] = required

    return schema


# ---------------------------------------------------------------------------
# Main parser
# ---------------------------------------------------------------------------

def _extract_skill_name(raw_markdown: str) -> str:
    """Extract skill name from the H1 title."""
    match = re.search(r"^#\s+(.+)$", raw_markdown, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return "Unknown"


def _extract_skill_id(file_path: str) -> int:
    """Extract skill ID (01-14) from filename."""
    match = re.search(r"Skill-(\d{2})", file_path)
    if match:
        return int(match.group(1))
    return 0


def parse_skill_file(file_path: str) -> SkillDef:
    """Parse one Skill .md file into a SkillDef dataclass.

    Args:
        file_path: Absolute path to a Skill-XX-*.md file.

    Returns:
        Fully parsed SkillDef object.
    """
    path = Path(file_path)
    # Use errors="replace" to handle truncated multi-byte UTF-8 sequences
    raw = path.read_text(encoding="utf-8", errors="replace")

    skill_id = _extract_skill_id(file_path)
    skill_name = _extract_skill_name(raw)

    # Split into 7 sections
    sections = _split_sections(raw)

    # Section 一: Raw description (full text)
    description_raw = sections.get("description", "")

    # Section 二: Dependencies — parse using filenames as name map
    name_map = _build_skill_name_id_map(path.parent)
    must, optional = _parse_dependencies(
        sections.get("dependencies", ""), name_map
    )

    # Section 三: Input format → both slim (meta) and full (execution) schemas
    input_json = _extract_json_block(sections.get("input_format", ""))
    full_input_schema = _build_full_input_schema(input_json) if input_json else {
        "type": "object", "properties": {}, "required": []
    }
    slim_input_schema = _build_slim_input_schema(input_json)

    # Section 四: Output format (keep as-is for handler reference)
    # Don't register outputSchema in Tool metadata to keep it slim
    output_schema = _extract_json_block(sections.get("output_format", "")) or {}

    # Section 五: System prompt
    system_prompt = sections.get("system_prompt", "")

    # Section 六: Failure strategies
    failure_strategies = sections.get("failure_strategies", "")

    # Section 七: Examples
    examples = sections.get("examples", "")

    return SkillDef(
        skill_id=skill_id,
        skill_name=skill_name,
        file_path=str(path.absolute()),
        # Meta
        short_description=_build_short_description(skill_id),
        dependencies_must=must,
        dependencies_optional=optional,
        tool_input_schema=slim_input_schema,
        # Execution
        description_raw=description_raw,
        full_input_schema=full_input_schema,
        output_schema=output_schema,
        system_prompt=system_prompt,
        failure_strategies=failure_strategies,
        examples=examples,
        raw_markdown=raw,
    )


def parse_all_skills() -> list[SkillDef]:
    """Discover and parse all Skill .md files, return sorted by skill_id."""
    files = discover_skill_files()
    skills = [parse_skill_file(f) for f in files]
    skills.sort(key=lambda s: s.skill_id)
    return skills
