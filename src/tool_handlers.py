"""APWA MCP Server - Per-Skill Tool Handlers.

Each handler:
  1. Validates that must-dependencies have completed outputs in ./skill_outputs/
  2. Loads upstream outputs and merges them with the incoming arguments
  3. Returns a structured response with TWO clearly-separated parts:
     a) 'system_message': the FULL, UNMODIFIED system prompt from the Skill's
        section 五 (### 五、系统提示词), verbatim — including role definition,
        execution steps, constraints, quality gates, and failure strategies.
     b) 'user_message': upstream data + user arguments, as context.
  4. If arguments contain a special "_store" key, saves output to skill_outputs/

The MCP client MUST use 'system_message' as the system instruction and
'user_message' as the task input — they are separated precisely so the
LLM receives quality-gate constraints as hard instructions, not as
background prose.
"""

import json
import re
from typing import Optional

from mcp import types as mcp_types

from config import OUTPUT_DIR, DELIVERY_DIR, THEORY_PAPER_TYPES, DANGEROUS_PATTERNS
from skill_registry import SkillRegistry
from checkpoint import (
    load_skill_output,
    load_skill_output_safe,
    save_skill_output,
    check_skill_status,
    save_checkpoint_state,
    clear_skill_state,
    CheckpointState,
    CheckpointAction,
    get_pipeline_status,
)


# Global registry instance (set at startup)
_registry: Optional[SkillRegistry] = None


def set_registry(registry: SkillRegistry) -> None:
    global _registry
    _registry = registry


def get_registry() -> SkillRegistry:
    if _registry is None:
        raise RuntimeError("SkillRegistry not initialized. Call set_registry() first.")
    return _registry


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def _validate_dependencies(skill_id: int) -> list[str]:
    """Check that all must-dependencies for a Skill have completed outputs.
    Returns a list of error messages (empty = all OK).
    """
    registry = get_registry()
    errors = []
    for dep_id in registry.get_must_dependencies(skill_id):
        state, _ = check_skill_status(dep_id)
        if state != CheckpointState.COMPLETED:
            skill_name = ""
            sk = registry.get_skill(dep_id)
            if sk:
                skill_name = sk.skill_name
            errors.append(
                f"❌ Skill {skill_id:02d} 依赖 Skill {dep_id:02d} ({skill_name})，"
                f"但其状态为 {state.value}。请先运行 Skill {dep_id:02d}。"
            )
    return errors


def _load_upstream_data(skill_id: int, skip_ids: set[int] | None = None) -> dict:
    """Load all upstream must-dependency outputs and return as a merged dict.
    Each upstream output is stored under key 'skill_XX_output'.
    """
    registry = get_registry()
    upstream: dict = {}
    skip = skip_ids or set()
    for dep_id in registry.get_all_dependencies(skill_id):
        if dep_id in skip:
            continue
        data = load_skill_output_safe(dep_id)
        if data is not None:
            upstream[f"skill_{dep_id:02d}_output"] = data
    return upstream


def _summarize_output(data: dict, max_chars: int = 800) -> str:
    """Extract key info from a Skill output for context-passing, not the whole thing.

    Strategy:
      - Prefer 'output_text' field (natural-language summary) → first max_chars chars
      - If no output_text, list top-level keys + key scalar values
      - For structured sub-objects, list their keys only
    Never returns more than ~max_chars.
    """
    if not isinstance(data, dict):
        return str(data)[:max_chars]

    # Golden path: output_text is the human-readable summary
    output_text = data.get("output_text", "")
    if output_text and isinstance(output_text, str) and len(output_text) > 20:
        if len(output_text) > max_chars:
            return output_text[:max_chars] + "...[截断]"
        return output_text

    # Fallback: build a compact key-value summary
    lines: list[str] = []
    char_budget = max_chars
    for key, value in data.items():
        if key.startswith("_"):
            continue
        if char_budget <= 0:
            break

        if isinstance(value, str):
            snippet = value[:120] + ("..." if len(value) > 120 else "")
            line = f"- {key}: {snippet}"
        elif isinstance(value, (int, float, bool)):
            line = f"- {key}: {value}"
        elif isinstance(value, list):
            n = len(value)
            line = f"- {key}: [{n} 项]"
            if value and isinstance(value[0], str) and char_budget > 100:
                preview = str(value[0])[:80]
                line += f" 如: {preview}"
        elif isinstance(value, dict):
            subkeys = [k for k in list(value.keys())[:5] if not k.startswith("_")]
            line = f"- {key}: {{{', '.join(subkeys)}{'...' if len(value) > 5 else ''}}}"
        else:
            line = f"- {key}: {type(value).__name__}"

        lines.append(line)
        char_budget -= len(line) + 1

    return "\n".join(lines) if lines else "(无摘要)"


def _build_context_messages(skill_id: int, arguments: dict, upstream: dict) -> dict:
    """Build CLEANLY SEPARATED system and user messages for the client LLM.

    Returns a dict with two keys:
      - 'system_message':  the FULL, verbatim section 五 from the Skill .md
      - 'user_message':    upstream data summaries + user arguments, as one block
    """
    registry = get_registry()
    skill = registry.get_skill(skill_id)
    if not skill:
        raise ValueError(f"Skill {skill_id} not found in registry.")

    # Side A: the unmodified system prompt
    system_message = skill.system_prompt

    # Side B: user context — upstream data summaries + arguments
    user_lines = [
        f"# 任务: {skill.skill_name} (Skill-{skill_id:02d})",
        "",
        skill.description_raw,
        "",
    ]

    if upstream:
        user_lines.append("## 上游 Skill 输出摘要")
        user_lines.append("以下是从前置 Skill 加载的数据摘要，完整数据在 ./skill_outputs/ 中。")
        user_lines.append("如需深入细节，请引用对应的 skill_XX_output.json 文件。")
        user_lines.append("")
        for key, data in upstream.items():
            sid_str = key.replace("skill_", "").replace("_output", "")
            try:
                sid_int = int(sid_str)
                dep_skill = registry.get_skill(sid_int)
                dep_name = dep_skill.skill_name if dep_skill else key
            except ValueError:
                dep_name = key
            user_lines.append(f"### 📂 {dep_name} ({key}.json)")
            summary = _summarize_output(data, max_chars=800)
            user_lines.append("```")
            user_lines.append(summary)
            user_lines.append("```")
            top_keys = [k for k in data if not k.startswith("_")]
            if top_keys:
                user_lines.append(f"可用顶层字段: {', '.join(top_keys)}")
            user_lines.append("")

    user_lines.append("## 用户输入参数")
    user_lines.append("```json")
    user_lines.append(json.dumps(arguments, ensure_ascii=False, indent=2))
    user_lines.append("```")
    user_lines.append("")

    user_lines.append("## 执行要求")
    user_lines.append(f"请严格按照系统指令（system message）完成 {skill.skill_name} 的所有步骤。")
    user_lines.append("产出结构化 JSON 结果，字段与 Skill 定义中的输出格式一致。")
    user_lines.append("完成后，以 _store 参数将 JSON 结果保存。")

    return {
        "system_message": system_message,
        "user_message": "\n".join(user_lines),
    }


def _build_context_prompt(skill_id: int, arguments: dict, upstream: dict) -> str:
    """DEPRECATED: kept for orchestrator compatibility.
    New code should use _build_context_messages.
    """
    ctx = _build_context_messages(skill_id, arguments, upstream)
    return (
        "# 系统指令 (SYSTEM MESSAGE — 必须严格遵守)\n\n"
        + ctx["system_message"]
        + "\n\n---\n\n"
        + "# 用户输入 (USER MESSAGE)\n\n"
        + ctx["user_message"]
    )


def _check_and_handle_checkpoint(skill_id: int) -> dict | None:
    """Check if a Skill has existing output and return a checkpoint prompt if so.
    Returns None if execution should proceed normally.
    """
    state, existing = check_skill_status(skill_id)
    if state in (CheckpointState.COMPLETED, CheckpointState.IN_PROGRESS):
        return {
            "checkpoint_required": True,
            "skill_id": skill_id,
            "status": state.value,
            "message": (
                f"Skill {skill_id:02d} 已有 {state.value} 状态的输出。"
                f"请使用 checkpoint_decision 工具选择操作：\n"
                f"  - skip: 跳过，使用已有输出\n"
                f"  - rerun: 清空已有数据并重新执行\n"
                f"  - continue: 基于已有材料继续执行（仅 in_progress 状态可用）"
            ),
            "existing_output_keys": (
                [k for k in existing if k != "_meta"] if existing else None
            ),
        }
    return None


def _should_skip_for_theory(skill_id: int) -> bool:
    """Check if skill should be skipped for theory/humanities papers."""
    if skill_id not in (7, 8):
        return False
    try:
        skill_01 = load_skill_output(1)
        paper_type = (
            skill_01.get("requirements_baseline", {}).get("paper_type", "")
        )
        return paper_type in THEORY_PAPER_TYPES
    except FileNotFoundError:
        return False


# ---------------------------------------------------------------------------
# Individual Skill Handlers
# ---------------------------------------------------------------------------

async def _standard_handler(skill_id: int, arguments: dict) -> list[mcp_types.TextContent]:
    """Standard handler template for most Skills.
    On exception: writes error JSON to skill_outputs/, sets state to BLOCKED,
    returns a clear interrupt message. Never deletes upstream outputs.
    """
    try:
        return await _standard_handler_impl(skill_id, arguments)
    except Exception as exc:
        import traceback
        registry = get_registry()
        skill = registry.get_skill(skill_id)
        name = skill.skill_name if skill else f"Skill-{skill_id:02d}"

        tb = traceback.format_exc()
        error_output = {
            "_error": True,
            "skill_id": skill_id,
            "error_type": type(exc).__name__,
            "error_message": str(exc),
            "traceback": tb[-3000:],
        }
        save_skill_output(skill_id, error_output)
        save_checkpoint_state(skill_id, "blocked", {
            "error_type": type(exc).__name__,
            "error_message": str(exc),
        })

        return [mcp_types.TextContent(
            type="text",
            text=json.dumps({
                "status": "blocked",
                "skill_id": skill_id,
                "skill_name": name,
                "error_type": type(exc).__name__,
                "error_message": str(exc),
                "message": (
                    f"🚫 Skill {skill_id:02d} ({name}) 执行异常中断。\n\n"
                    f"错误类型: {type(exc).__name__}\n"
                    f"错误信息: {exc}\n\n"
                    f"状态已设为 BLOCKED。修复问题后使用 checkpoint_decision(skill_id={skill_id}, action='rerun') "
                    f"清除错误状态，然后重新调用 skill_{skill_id:02d} 继续。\n\n"
                    f"注意: 上游 Skill 的输出文件未被修改，数据安全。"
                ),
                "traceback_tail": tb[-1500:],
            }, ensure_ascii=False, indent=2),
        )]


async def _standard_handler_impl(skill_id: int, arguments: dict) -> list[mcp_types.TextContent]:
    """Inner implementation — see _standard_handler for the try/except wrapper."""
    registry = get_registry()

    # Handle storage mode: if arguments contain _store, save output
    if "_store" in arguments:
        store_data = arguments["_store"]
        save_skill_output(skill_id, store_data)
        save_checkpoint_state(skill_id, "completed", store_data)
        return [mcp_types.TextContent(
            type="text",
            text=json.dumps({
                "status": "stored",
                "skill_id": skill_id,
                "message": f"Skill {skill_id:02d} 输出已保存到 ./skill_outputs/",
                "output_keys": list(store_data.keys()),
            }, ensure_ascii=False, indent=2),
        )]

    # Checkpoint check
    checkpoint = _check_and_handle_checkpoint(skill_id)
    if checkpoint:
        return [mcp_types.TextContent(type="text", text=json.dumps(checkpoint, ensure_ascii=False, indent=2))]

    # Theory paper skip for Skills 07/08
    if _should_skip_for_theory(skill_id):
        skip_output = {
            "_skipped": True,
            "_reason": "paper_type 为理论推演或综述论文，本 Skill 不适用",
            "output_text": "由于论文类型为理论推演或综述论文，本实验环节自动跳过。",
        }
        save_skill_output(skill_id, skip_output)
        save_checkpoint_state(skill_id, "completed", skip_output)
        return [mcp_types.TextContent(
            type="text",
            text=json.dumps({
                "status": "skipped",
                "skill_id": skill_id,
                "reason": "paper_type 为理论推演或综述论文",
                "message": "本 Skill 已自动跳过。下游 Skill 将收到跳过标记。",
            }, ensure_ascii=False, indent=2),
        )]

    # Validate dependencies
    errors = _validate_dependencies(skill_id)
    if errors:
        return [mcp_types.TextContent(type="text", text="\n".join(errors))]

    # Load upstream data
    upstream = _load_upstream_data(skill_id)

    # Mark as in_progress
    save_checkpoint_state(skill_id, "in_progress", {"step": "execution_started"})

    # Build separated system and user messages
    ctx = _build_context_messages(skill_id, arguments, upstream)

    return [mcp_types.TextContent(type="text", text=json.dumps(ctx, ensure_ascii=False, indent=2))]


# ---------------------------------------------------------------------------
# Skill 01 - 通用论文需求采集与初始化
# ---------------------------------------------------------------------------

async def handle_skill_01(arguments: dict) -> list[mcp_types.TextContent]:
    """采集用户学术论文的全部边界条件，检查本地运行环境，输出需求基线文档。

    Two-phase flow:
      Phase 1 (first call): returns system+user messages → LLM generates
        requirements_baseline and presents confirmation summary to user.
      Phase 2 (after user confirms): user calls confirm_skill_01 to save.
        Subsequent skill_01 calls return the cached confirmed baseline.
    """
    state, existing = check_skill_status(1)
    if state == CheckpointState.COMPLETED and existing and existing.get("user_confirmed"):
        return [mcp_types.TextContent(
            type="text",
            text=json.dumps({
                "status": "already_confirmed",
                "skill_id": 1,
                "message": (
                    "Skill-01 需求基线已确认。下游 Skill 可直接使用。"
                    "如需修改，请使用 checkpoint_decision(skill_id=1, action='rerun') 重新采集。"
                ),
                "requirements_summary": {
                    k: v for k, v in existing.get("requirements_baseline", {}).items()
                },
            }, ensure_ascii=False, indent=2),
        )]

    return await _standard_handler(1, arguments)


# ---------------------------------------------------------------------------
# confirm_skill_01 — 确认 Skill-01 需求基线
# ---------------------------------------------------------------------------

async def handle_confirm_skill_01(arguments: dict) -> list[mcp_types.TextContent]:
    """Confirm and persist the Skill-01 requirements baseline after user review.

    Required: requirements_baseline (dict with at minimum paper_level,
              research_domain, paper_type, language).
    """
    requirements = arguments.get("requirements_baseline", {})

    required_fields = ["paper_level", "research_domain", "paper_type", "language"]
    missing = [f for f in required_fields if not requirements.get(f)]
    if missing:
        return [mcp_types.TextContent(
            type="text",
            text=json.dumps({
                "status": "error",
                "skill_id": 1,
                "message": (
                    f"requirements_baseline 缺少必填字段: {', '.join(missing)}。"
                    f"请补全后重新调用 confirm_skill_01。"
                ),
                "missing_fields": missing,
            }, ensure_ascii=False, indent=2),
        )]

    # Enrich with defaults
    if "reference_minimum" not in requirements or not requirements["reference_minimum"]:
        level_map = {"本科毕业论文": 30, "硕士毕业论文": 50, "博士毕业论文": 80,
                     "期刊论文": 30, "会议论文": 20}
        requirements["reference_minimum"] = level_map.get(requirements["paper_level"], 30)

    if "quality_threshold" not in requirements or not requirements.get("quality_threshold"):
        q_map = {"本科毕业论文": 70, "硕士毕业论文": 80, "博士毕业论文": 85,
                 "期刊论文": 80, "会议论文": 75}
        requirements["quality_threshold"] = q_map.get(requirements["paper_level"], 75)

    if "word_count" not in requirements or not requirements.get("word_count"):
        wc_map = {"本科毕业论文": "8000-15000", "硕士毕业论文": "20000-40000",
                  "博士毕业论文": "50000-100000"}
        requirements["word_count"] = wc_map.get(requirements["paper_level"], "")

    output = {
        "requirements_baseline": requirements,
        "user_confirmed": True,
        "output_text": arguments.get("output_text", "需求基线已由用户确认。"),
        "completeness_flag": arguments.get("completeness_flag", "green"),
        "template_analysis": arguments.get("template_analysis", {}),
        "workspace_files_summary": arguments.get("workspace_files_summary", {}),
        "environment_report": arguments.get("environment_report", {}),
        "followup_questions": arguments.get("followup_questions", []),
        "auto_fill_notes": arguments.get("auto_fill_notes", ""),
    }

    save_skill_output(1, output)
    save_checkpoint_state(1, "completed", output)

    return [mcp_types.TextContent(
        type="text",
        text=json.dumps({
            "status": "confirmed",
            "skill_id": 1,
            "skill_name": "通用论文需求采集与初始化",
            "message": "✅ Skill-01 需求基线已确认并保存。所有下游 Skill 现在可以开始执行。",
            "requirements_summary": {
                "paper_level": requirements.get("paper_level"),
                "research_domain": requirements.get("research_domain"),
                "paper_type": requirements.get("paper_type"),
                "language": requirements.get("language"),
                "target_score": requirements.get("target_score", "未指定"),
                "quality_threshold": requirements.get("quality_threshold"),
            },
        }, ensure_ascii=False, indent=2),
    )]


# ---------------------------------------------------------------------------
# Skills 02-11 and 13-14 — standard handlers
# ---------------------------------------------------------------------------

async def handle_skill_02(arguments): return await _standard_handler(2, arguments)
async def handle_skill_03(arguments): return await _standard_handler(3, arguments)
async def handle_skill_04(arguments): return await _standard_handler(4, arguments)
async def handle_skill_05(arguments): return await _standard_handler(5, arguments)
async def handle_skill_06(arguments): return await _standard_handler(6, arguments)
async def handle_skill_07(arguments): return await _standard_handler(7, arguments)

async def handle_skill_08(arguments: dict) -> list[mcp_types.TextContent]:
    """在本地沙箱环境中自动运行实验代码，验证其可复现性和有效性。含安全检查。"""
    try:
        if "_store" not in arguments:
            skill_07 = load_skill_output_safe(7)
            if skill_07:
                code_package = skill_07.get("code_package", {})
                code_files = code_package.get("code_files", [])
                violations = []
                for cf in code_files:
                    content = cf.get("content", "") if isinstance(cf, dict) else str(cf)
                    for pattern, desc in DANGEROUS_PATTERNS:
                        if re.search(pattern, content):
                            violations.append({
                                "file": cf.get("file_path", "unknown") if isinstance(cf, dict) else "unknown",
                                "violation": desc,
                                "pattern": pattern,
                            })
                if violations:
                    return [mcp_types.TextContent(
                        type="text",
                        text=json.dumps({
                            "status": "security_blocked",
                            "skill_id": 8,
                            "message": "安全检查：在 Skill 07 生成的代码中检测到危险模式。拒绝执行。",
                            "violations": violations,
                            "action_required": "确认安全后可在 arguments 中设置 force_security_bypass: true。",
                        }, ensure_ascii=False, indent=2),
                    )]
        return await _standard_handler(8, arguments)
    except Exception:
        return await _standard_handler(8, arguments)

async def handle_skill_09(arguments): return await _standard_handler(9, arguments)
async def handle_skill_10(arguments): return await _standard_handler(10, arguments)
async def handle_skill_11(arguments): return await _standard_handler(11, arguments)

async def handle_skill_12(arguments: dict) -> list[mcp_types.TextContent]:
    """以审稿人视角对论文初稿进行五维度严格评分和诊断。
    特殊逻辑: 如果 pass=false 且 round < 3，自动提示触发 Skill 13 修改循环。
    """
    try:
        if "_store" in arguments:
            store_data = arguments["_store"]
            skill_id = 12
            save_skill_output(skill_id, store_data)
            save_checkpoint_state(skill_id, "completed", store_data)

            eval_report = store_data.get("evaluation_report", {})
            if not eval_report.get("pass", False):
                round_num = arguments.get("round", 1)
                max_rounds = store_data.get("max_review_rounds", 3)
                if round_num < max_rounds:
                    return [mcp_types.TextContent(
                        type="text",
                        text=json.dumps({
                            "status": "stored_and_loop",
                            "skill_id": skill_id,
                            "message": (
                                f"评阅未通过 (轮次 {round_num}/{max_rounds})。"
                                f"需要执行 Skill 13 进行修改。\n"
                                f"请调用 skill_13，传入 evaluation_report 和 rewrite_priority。"
                            ),
                            "next_action": "run_skill_13",
                            "rewrite_priority": eval_report.get("rewrite_priority", []),
                        }, ensure_ascii=False, indent=2),
                    )]
                else:
                    return [mcp_types.TextContent(
                        type="text",
                        text=json.dumps({
                            "status": "stored_max_rounds",
                            "skill_id": skill_id,
                            "message": f"评阅已执行 {max_rounds} 轮仍未通过。建议人工介入审查。",
                            "next_action": "manual_review_required",
                        }, ensure_ascii=False, indent=2),
                    )]

            return [mcp_types.TextContent(
                type="text",
                text=json.dumps({
                    "status": "stored",
                    "skill_id": skill_id,
                    "message": f"Skill {skill_id:02d} 评阅已通过！可继续执行 Skill 14。",
                }, ensure_ascii=False, indent=2),
            )]

        return await _standard_handler(12, arguments)
    except Exception:
        return await _standard_handler(12, arguments)

async def handle_skill_13(arguments): return await _standard_handler(13, arguments)
async def handle_skill_14(arguments): return await _standard_handler(14, arguments)


# ---------------------------------------------------------------------------
# Checkpoint Decision Handler
# ---------------------------------------------------------------------------

async def handle_checkpoint_decision(arguments: dict) -> list[mcp_types.TextContent]:
    """Process a checkpoint decision: skip, rerun, or continue."""
    skill_id = arguments.get("skill_id", 0)
    action_str = arguments.get("action", "")

    if not (1 <= skill_id <= 14):
        return [mcp_types.TextContent(type="text", text=f"Invalid skill_id: {skill_id}")]

    try:
        action = CheckpointAction(action_str)
    except ValueError:
        return [mcp_types.TextContent(
            type="text",
            text=f"Invalid action: {action_str}. Must be: skip, rerun, continue",
        )]

    state, _ = check_skill_status(skill_id)

    if action == CheckpointAction.RERUN:
        clear_skill_state(skill_id)
        save_checkpoint_state(skill_id, "not_started")
        return [mcp_types.TextContent(
            type="text",
            text=json.dumps({
                "status": "cleared",
                "skill_id": skill_id,
                "message": f"Skill {skill_id:02d} 的已有输出已清空。请重新调用 skill_{skill_id:02d} 开始执行。",
            }, ensure_ascii=False, indent=2),
        )]

    elif action == CheckpointAction.SKIP:
        if state == CheckpointState.COMPLETED:
            return [mcp_types.TextContent(
                type="text",
                text=json.dumps({
                    "status": "skipped",
                    "skill_id": skill_id,
                    "message": f"Skill {skill_id:02d} 已跳过。下游 Skill 将使用已有输出文件。",
                }, ensure_ascii=False, indent=2),
            )]
        else:
            return [mcp_types.TextContent(
                type="text",
                text=json.dumps({
                    "status": "error",
                    "skill_id": skill_id,
                    "message": f"Skill {skill_id:02d} 当前状态为 {state.value}，没有完整输出可跳过。",
                }, ensure_ascii=False, indent=2),
            )]

    elif action == CheckpointAction.CONTINUE:
        if state in (CheckpointState.IN_PROGRESS, CheckpointState.BLOCKED):
            existing = load_skill_output_safe(skill_id)
            return [mcp_types.TextContent(
                type="text",
                text=json.dumps({
                    "status": "continuing",
                    "skill_id": skill_id,
                    "message": (
                        f"Skill {skill_id:02d} 将从断点继续执行。"
                        f"已有部分数据已加载，请调用 skill_{skill_id:02d} 继续。"
                    ),
                    "existing_data_keys": [k for k in existing if k != "_meta"] if existing else [],
                }, ensure_ascii=False, indent=2),
            )]
        else:
            return [mcp_types.TextContent(
                type="text",
                text=json.dumps({
                    "status": "error",
                    "skill_id": skill_id,
                    "message": f"Skill {skill_id:02d} 当前状态为 {state.value}，没有进行中的执行可继续。",
                }, ensure_ascii=False, indent=2),
            )]

    return [mcp_types.TextContent(type="text", text="Unknown action.")]


# ---------------------------------------------------------------------------
# Handler dispatch table
# ---------------------------------------------------------------------------

SKILL_HANDLERS = {
    1: handle_skill_01,
    2: handle_skill_02,
    3: handle_skill_03,
    4: handle_skill_04,
    5: handle_skill_05,
    6: handle_skill_06,
    7: handle_skill_07,
    8: handle_skill_08,
    9: handle_skill_09,
    10: handle_skill_10,
    11: handle_skill_11,
    12: handle_skill_12,
    13: handle_skill_13,
    14: handle_skill_14,
}


def get_handler(skill_id: int):
    """Get the handler function for a given skill ID."""
    return SKILL_HANDLERS.get(skill_id)
