"""APWA MCP Server - Pipeline Orchestrator.

Handles the run_pipeline tool which executes Skills in dependency order
from start_skill to end_skill, auto-managing checkpoint state and data flow.
"""

import json
from typing import Optional

from mcp import types as mcp_types

from config import MAX_REVIEW_ROUNDS
from skill_registry import SkillRegistry
from checkpoint import (
    CheckpointState,
    check_skill_status,
    save_skill_output,
    save_checkpoint_state,
    load_skill_output_safe,
)
from tool_handlers import get_handler


async def handle_run_pipeline(
    arguments: dict,
    registry: Optional[SkillRegistry] = None,
) -> list[mcp_types.TextContent]:
    """Execute Skills in topological order from start_skill to end_skill.

    The pipeline:
      1. Computes topological order
      2. For each Skill in order:
         a. Checks checkpoint — skips COMPLETED, warns on IN_PROGRESS
         b. Validates dependencies (must-load upstream outputs)
         c. Dispatches to the Skill handler
         d. The handler returns the prompt; caller processes and stores

    Note: In the MCP stdio model, the pipeline can only coordinate data flow.
    The actual LLM reasoning happens in the client. So this tool returns
    a structured execution plan that the client iterates through.
    """
    start = arguments.get("start_skill", 1)
    end = arguments.get("end_skill", 14)
    initial_input = arguments.get("initial_input", {})

    if not (1 <= start <= end <= 14):
        return [mcp_types.TextContent(
            type="text",
            text=f"Error: Invalid skill range ({start}-{end}). Both must be 1-14 and start <= end.",
        )]

    if registry is None:
        from tool_handlers import get_registry
        registry = get_registry()

    # Get topological order
    order = registry.get_topological_order(start, end)

    if not order:
        return [mcp_types.TextContent(
            type="text",
            text=f"Error: No execution path found from Skill {start:02d} to Skill {end:02d}.",
        )]

    # First pass: check all must-dependencies before start
    first_skill = order[0]
    if first_skill > start:
        # The first skill may have deps outside the range
        skill_obj = registry.get_skill(first_skill)
        if skill_obj:
            for dep_id in skill_obj.dependencies_must:
                if dep_id < start:
                    state, _ = check_skill_status(dep_id)
                    if state != CheckpointState.COMPLETED:
                        return [mcp_types.TextContent(
                            type="text",
                            text=(
                                f"Error: Skill {first_skill:02d} (pipeline first) depends on "
                                f"Skill {dep_id:02d} which is outside the pipeline range and "
                                f"has status '{state.value}'. Please run Skill {dep_id:02d} first."
                            ),
                        )]

    # Build execution plan
    plan_lines = [
        f"# Pipeline Execution Plan: Skill {start:02d} → Skill {end:02d}",
        "",
        f"拓扑执行序: {order}",
        f"共 {len(order)} 个 Skill",
        "",
        "## 执行说明",
        "",
        "本管道按以下顺序执行每个 Skill。请依次调用每个 skill_XX 工具，",
        "将 LLM 的推理结果通过 `_store` 参数保存，然后继续下一个。",
        "",
        "---",
        "",
    ]

    # Check each Skill's status and build plan
    skills_to_run: list[int] = []
    for sid in order:
        state, _ = check_skill_status(sid)
        skill = registry.get_skill(sid)
        name = skill.skill_name if skill else f"Skill-{sid:02d}"

        if state == CheckpointState.COMPLETED:
            plan_lines.append(f"### ⏭ Skill {sid:02d}: {name} — 已完成，自动跳过")
        elif state == CheckpointState.BLOCKED:
            plan_lines.append(
                f"### 🚫 Skill {sid:02d}: {name} — 异常中断（BLOCKED），需修复后输入 continue 继续。管道暂停。"
            )
            skills_to_run.append(sid)
        elif state == CheckpointState.IN_PROGRESS:
            plan_lines.append(
                f"### ⚠ Skill {sid:02d}: {name} — 进行中（需确认 continue/rerun）"
            )
            skills_to_run.append(sid)
        else:
            deps_str = ""
            if skill and skill.dependencies_must:
                dep_names = []
                for d in skill.dependencies_must:
                    ds = registry.get_skill(d)
                    dn = ds.skill_name if ds else f"Skill-{d:02d}"
                    dep_names.append(dn)
                deps_str = f" (依赖: {', '.join(dep_names)})"
            plan_lines.append(f"### ▶ Skill {sid:02d}: {name}{deps_str}")
            skills_to_run.append(sid)

    plan_lines.append("")
    plan_lines.append("---")
    plan_lines.append("")

    if skills_to_run:
        plan_lines.append("## 立即执行")
        plan_lines.append("")
        first = skills_to_run[0]
        plan_lines.append(f"请先调用 `skill_{first:02d}` 开始执行。")
    else:
        plan_lines.append("## 全部完成")
        plan_lines.append("所有 Skill 均已执行完毕。可调用 `generate_delivery` 生成交付包。")

    return [mcp_types.TextContent(type="text", text="\n".join(plan_lines))]
