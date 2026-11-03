#!/usr/bin/env python3
"""APWA MCP Server — Academic Paper Writing Agent.

MCP (Model Context Protocol) stdio server that wraps 14 academic paper-writing
Skills as individual MCP tools, with pipeline orchestration, checkpoint-resume,
and delivery package generation.

Usage:
    python server.py          # Start in stdio mode (default)
    python server.py --test   # Run internal diagnostics
"""

import asyncio
import json
import sys
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool
from mcp import types as mcp_types

from skill_parser import parse_all_skills
from skill_registry import SkillRegistry
from checkpoint import (
    check_skill_status,
    CheckpointState,
    save_skill_output,
    save_checkpoint_state,
    clear_skill_state,
    load_skill_output_safe,
    get_pipeline_status,
)
from tool_handlers import (
    set_registry,
    get_handler,
    SKILL_HANDLERS,
    handle_checkpoint_decision,
    handle_confirm_skill_01,
)
from orchestrator import handle_run_pipeline
from delivery import handle_generate_delivery


# ---------------------------------------------------------------------------
# Global registry (loaded at startup)
# ---------------------------------------------------------------------------

registry: SkillRegistry | None = None


def _init_registry() -> SkillRegistry:
    global registry
    if registry is None:
        print(f"[apwa] Loading SkillRegistry, SKILL_DIR from config...", file=sys.stderr, flush=True)
        try:
            registry = SkillRegistry()
            print(f"[apwa] Loaded {len(registry)} skills, {len(registry.get_tool_list())} tools", file=sys.stderr)
        except Exception as e:
            import traceback
            print(f"[apwa] ERROR loading registry: {e}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            # Create empty registry but don't fail
            registry = SkillRegistry()
        set_registry(registry)
    return registry


# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------

server = Server(
    name="apwa-pipeline",
    version="1.0.0",
    instructions=(
        "APWA — 多阶段 Agent 工作流（MCP Server）。\n"
        "把 14 个专业阶段封装为 MCP 工具，支持依赖拓扑编排、断点续跑与交付包生成。\n\n"
        "每个阶段带独立的 inputSchema / outputSchema 与 must_deps / opt_deps 声明；\n"
        "run_pipeline 依据依赖图返回拓扑执行序，checkpoint_decision 处理中断与重跑，\n"
        "pipeline_status 查看全部阶段状态，generate_delivery 汇总产物为交付包。\n\n"
        "阶段序列: Skill-01(需求采集) → Skill-02(文献预检索) → Skill-03(选题) → "
        "Skill-04(精准检索) → Skill-05(综述) → Skill-06(实验设计) → Skill-07(代码生成) → "
        "Skill-08(实验执行) → Skill-09(结果分析) → Skill-10(大纲设计) → "
        "Skill-11(论文撰写) → Skill-12(评阅) → Skill-13(修改) → Skill-14(终检)"
    ),
)


@server.list_tools()
async def list_tools() -> list[Tool]:
    """Register all tools with the MCP server."""
    reg = _init_registry()
    tools = reg.get_tool_list()
    return tools


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[mcp_types.TextContent]:
    """Dispatch MCP tool calls to their handlers."""
    reg = _init_registry()

    # Skill tools: skill_01 through skill_14
    if name.startswith("skill_"):
        try:
            skill_id = int(name.split("_")[1])
        except (IndexError, ValueError):
            return [mcp_types.TextContent(type="text", text=f"Unknown tool: {name}")]

        handler = get_handler(skill_id)
        if handler:
            return await handler(arguments)
        return [mcp_types.TextContent(type="text", text=f"No handler for {name}")]

    # Pipeline orchestration
    elif name == "run_pipeline":
        return await handle_run_pipeline(arguments, reg)

    # Checkpoint decision
    elif name == "checkpoint_decision":
        return await handle_checkpoint_decision(arguments)

    # Confirm Skill-01 requirements
    elif name == "confirm_skill_01":
        return await handle_confirm_skill_01(arguments)

    # Delivery generation
    elif name == "generate_delivery":
        return await handle_generate_delivery()

    # Pipeline status
    elif name == "pipeline_status":
        statuses = get_pipeline_status()
        return [mcp_types.TextContent(
            type="text",
            text=json.dumps(statuses, ensure_ascii=False, indent=2),
        )]

    else:
        return [mcp_types.TextContent(type="text", text=f"Unknown tool: {name}")]


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

async def main():
    """Start the MCP server in stdio mode."""
    # Initialize registry on startup
    _init_registry()

    print(f"[apwa] Server starting, registry has {len(registry)} skills", file=sys.stderr, flush=True)

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


def run_test():
    """Internal diagnostic: test parser, registry, checkpoint system."""
    print("=" * 60)
    print("APWA MCP Server — Diagnostics")
    print("=" * 60)

    # 1. Skill parsing
    print("\n[1] Parsing Skill files...")
    skills = parse_all_skills()
    print(f"    OK — {len(skills)} Skills parsed")

    for s in skills:
        print(f"    Skill {s.skill_id:02d}: {s.skill_name}")
        print(f"      must_deps: {s.dependencies_must}")
        print(f"      opt_deps:  {s.dependencies_optional}")
        print(f"      slim_inputSchema props: {len(s.tool_input_schema.get('properties', {}))}")
        print(f"      full_inputSchema props: {len(s.full_input_schema.get('properties', {}))}")
        print(f"      outputSchema keys: {list(s.output_schema.keys())[:5]}...")
        print(f"      system_prompt: {len(s.system_prompt)} chars")

    # 2. Registry
    print("\n[2] Building SkillRegistry...")
    reg = _init_registry()
    print(f"    OK — {len(reg)} Skills registered")

    # 3. Tool list
    print("\n[3] Generating tool list...")
    tools = reg.get_tool_list()
    print(f"    OK — {len(tools)} tools generated")
    for t in tools:
        print(f"    Tool: {t.name} — {t.title}")

    # 4. Topological order
    print("\n[4] Topological order (01→14):")
    order = reg.get_topological_order(1, 14)
    print(f"    {order}")

    # 5. Checkpoint system
    print("\n[5] Checkpoint system...")
    print(f"    Pipeline status: {get_pipeline_status()['_summary']}")
    print("    OK — checkpoint system functional")

    # 6. Tool list verification
    print("\n[6] Tool name verification:")
    expected = [f"skill_{i:02d}" for i in range(1, 15)]
    expected += ["confirm_skill_01", "run_pipeline", "checkpoint_decision", "pipeline_status", "generate_delivery"]
    tool_names = [t.name for t in tools]
    all_ok = True
    for ename in expected:
        ok = ename in tool_names
        if not ok:
            all_ok = False
        print(f"    {'OK' if ok else 'MISSING'} {ename}")
    if all_ok:
        print("    All 19 tools registered correctly.")

    print("\n" + "=" * 60)
    print("Diagnostics complete. Server is ready.")
    print("=" * 60)


if __name__ == "__main__":
    if "--test" in sys.argv:
        run_test()
    else:
        asyncio.run(main())