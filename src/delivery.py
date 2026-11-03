"""APWA MCP Server - Delivery Package Generation.

Assembles all upstream Skill outputs into a final delivery package
in ./delivery/, suitable for submission or archival.
"""

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from mcp import types as mcp_types

from config import DELIVERY_DIR, OUTPUT_DIR, TOTAL_SKILLS
from checkpoint import (
    load_skill_output_safe,
    check_skill_status,
    CheckpointState,
    get_pipeline_status,
)


def _ensure_delivery_dir() -> Path:
    DELIVERY_DIR.mkdir(parents=True, exist_ok=True)
    return DELIVERY_DIR


def _generate_thesis_final() -> str:
    """Extract the final thesis content from Skill 11 and/or Skill 13-14."""
    lines: list[str] = []

    # Prefer Skill 14 revised thesis
    skill_14 = load_skill_output_safe(14)
    if skill_14 and "revised_thesis" in skill_14:
        rt = skill_14["revised_thesis"]
        if isinstance(rt, dict) and "output_text" in rt:
            lines.append(rt["output_text"])
        elif isinstance(rt, str):
            lines.append(rt)

    # Fallback to Skill 13
    skill_13 = load_skill_output_safe(13)
    if not lines and skill_13 and "revised_thesis" in skill_13:
        rt = skill_13["revised_thesis"]
        if isinstance(rt, dict) and "output_text" in rt:
            lines.append(rt["output_text"])
        elif isinstance(rt, str):
            lines.append(rt)

    # Fallback to Skill 11
    skill_11 = load_skill_output_safe(11)
    if not lines and skill_11:
        ft = skill_11.get("full_thesis", {})
        if isinstance(ft, dict):
            lines.append(ft.get("output_text", ""))
        elif isinstance(ft, str):
            lines.append(ft)

    return "\n\n".join(lines) if lines else "（论文内容尚未生成，请先执行 Skill 11。）"


def _generate_skill_execution_report(statuses: dict) -> str:
    """Generate a markdown report of Skill execution history."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines = [
        "# APWA Skill Execution Report",
        f"生成时间: {ts}",
        "",
        "## 执行状态总览",
        "",
        "| Skill | 名称 | 状态 | 时间戳 |",
        "|-------|------|------|--------|",
    ]

    from skill_parser import parse_all_skills
    try:
        skills = parse_all_skills()
        name_map = {s.skill_id: s.skill_name for s in skills}
    except Exception:
        name_map = {}

    for sid in range(1, TOTAL_SKILLS + 1):
        key = f"skill_{sid:02d}"
        entry = statuses.get(key, {})
        status = entry.get("status", "unknown")
        ts_val = entry.get("timestamp", "-")
        if ts_val and ts_val != "-":
            ts_val = str(ts_val)[:19]
        name = name_map.get(sid, f"Skill-{sid:02d}")
        status_emoji = {
            "completed": "✅",
            "in_progress": "🔄",
            "failed": "❌",
            "not_started": "⬜",
        }.get(status, "❓")
        lines.append(f"| Skill-{sid:02d} | {name} | {status_emoji} {status} | {ts_val} |")

    summary = statuses.get("_summary", {})
    lines.append("")
    lines.append(f"**总计**: {summary.get('total', 14)} | "
                 f"完成: {summary.get('completed', 0)} | "
                 f"进行中: {summary.get('in_progress', 0)} | "
                 f"失败: {summary.get('failed', 0)} | "
                 f"未开始: {summary.get('not_started', 0)}")

    return "\n".join(lines)


def _generate_ai_usage_record(statuses: dict) -> str:
    """Generate AI usage record documenting which Skills used AI."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# AI 使用记录 (AI Usage Record)",
        f"生成时间: {ts}",
        "",
        "本论文写作过程使用了 APWA (Academic Paper Writing Agent) MCP 服务，",
        "以下记录了各阶段 AI 辅助的具体内容。",
        "",
        "## 各阶段 AI 使用说明",
        "",
    ]

    from skill_parser import parse_all_skills
    try:
        skills = parse_all_skills()
        name_map = {s.skill_id: (s.skill_name, s.description[:200]) for s in skills}
    except Exception:
        name_map = {}

    for sid in range(1, TOTAL_SKILLS + 1):
        key = f"skill_{sid:02d}"
        entry = statuses.get(key, {})
        status = entry.get("status", "unknown")
        name_desc = name_map.get(sid, (f"Skill-{sid:02d}", ""))
        name = name_desc[0]
        desc = name_desc[1]

        if status == "completed":
            lines.append(f"### Skill {sid:02d}: {name}")
            lines.append(f"> {desc}")
            lines.append("")
            lines.append(f"- **执行状态**: ✅ 已完成")
            lines.append(f"- **AI 角色**: 本阶段的系统提示词指导了全部的 {name} 工作")
            lines.append(f"- **人工监督**: 用户在每个检查点进行确认")
            lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## 声明")
    lines.append("")
    lines.append("本文档记录了 AI 工具在本论文写作过程中的辅助角色。")
    lines.append("所有最终学术判断和内容责任均由论文作者承担。")
    return "\n".join(lines)


def _generate_citation_verification() -> str:
    """Verify citations from Skill 04 data."""
    skill_04 = load_skill_output_safe(4)
    if not skill_04:
        return "（Skill 04 未执行，无法生成引用验证报告。）"

    annotated = skill_04.get("annotated_bibliography", [])
    lines = [
        "# 引用验证报告 (Citation Verification)",
        "",
        f"验证引用数: {len(annotated)}",
        "",
        "| # | 文献标题 | 来源类型 | 验证状态 |",
        "|---|----------|----------|----------|",
    ]

    for i, entry in enumerate(annotated, 1):
        if isinstance(entry, dict):
            title = entry.get("title", "N/A")
            source = entry.get("source_type", "unknown")
            source_trace = entry.get("source_trace", {})
            verified = "✅ 可复现" if source_trace else "⚠ 需人工验证"
        else:
            title = str(entry)[:80]
            source = "unknown"
            verified = "⚠ 需人工验证"

        lines.append(f"| {i} | {title[:60]} | {source} | {verified} |")

    lines.append("")
    lines.append("---")
    lines.append("*注: 可复现 = 文献可通过 source_trace 中记录的检索方式重新获取。*")
    return "\n".join(lines)


async def handle_generate_delivery() -> list[mcp_types.TextContent]:
    """Generate the complete delivery package in ./delivery/."""
    _ensure_delivery_dir()

    # Get current pipeline status
    statuses = get_pipeline_status()

    files_created: list[str] = []

    # 1. Thesis final
    thesis_path = DELIVERY_DIR / "thesis_final.md"
    thesis_content = _generate_thesis_final()
    thesis_path.write_text(thesis_content, encoding="utf-8")
    files_created.append(str(thesis_path.name))

    # 2. Skill execution report
    report_path = DELIVERY_DIR / "skill_execution_report.md"
    report_content = _generate_skill_execution_report(statuses)
    report_path.write_text(report_content, encoding="utf-8")
    files_created.append(str(report_path.name))

    # 3. AI usage record
    ai_path = DELIVERY_DIR / "ai_usage_record.md"
    ai_content = _generate_ai_usage_record(statuses)
    ai_path.write_text(ai_content, encoding="utf-8")
    files_created.append(str(ai_path.name))

    # 4. Citation verification
    cite_path = DELIVERY_DIR / "citation_verification.md"
    cite_content = _generate_citation_verification()
    cite_path.write_text(cite_content, encoding="utf-8")
    files_created.append(str(cite_path.name))

    # 5. Copy experiment code (Skill 07 output)
    skill_07 = load_skill_output_safe(7)
    if skill_07 and not skill_07.get("_skipped"):
        code_dir = DELIVERY_DIR / "experiment_code"
        code_dir.mkdir(exist_ok=True)
        code_package = skill_07.get("code_package", {})
        code_files = code_package.get("code_files", [])
        for cf in code_files:
            if isinstance(cf, dict):
                fname = cf.get("file_path", "unknown.py")
                content = cf.get("content", "")
                # Sanitize filename
                fname = str(fname).replace("\\", "/").split("/")[-1]
                (code_dir / fname).parent.mkdir(parents=True, exist_ok=True)
                (code_dir / fname).write_text(str(content), encoding="utf-8")
                files_created.append(f"experiment_code/{fname}")
        if not code_files:
            (code_dir / "README.md").write_text(
                "实验代码未在 Skill 07 中生成，或因论文类型原因跳过。", encoding="utf-8"
            )
        files_created.append("experiment_code/")

    # 6. Figures directory (metadata from Skill 09)
    skill_09 = load_skill_output_safe(9)
    if skill_09 and not skill_09.get("_skipped"):
        figures_dir = DELIVERY_DIR / "figures_and_tables"
        figures_dir.mkdir(exist_ok=True)
        figures_list = skill_09.get("figures_and_tables", [])
        if figures_list:
            (figures_dir / "figures_manifest.json").write_text(
                json.dumps(figures_list, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        else:
            (figures_dir / "README.md").write_text(
                "图表清单由 Skill 09 生成。图表源文件可能已嵌入论文正文。", encoding="utf-8"
            )
        files_created.append("figures_and_tables/")

    # 7. Copy skill outputs as archive
    archive_dir = DELIVERY_DIR / "skill_outputs_archive"
    archive_dir.mkdir(exist_ok=True)
    for sid in range(1, TOTAL_SKILLS + 1):
        output = load_skill_output_safe(sid)
        if output:
            fname = f"skill_{sid:02d}_output.json"
            (archive_dir / fname).write_text(
                json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8"
            )
    files_created.append("skill_outputs_archive/")

    # Summary
    summary = {
        "status": "delivery_generated",
        "delivery_path": str(DELIVERY_DIR.absolute()),
        "files_created": files_created,
        "message": f"✅ 交付包已生成到 ./delivery/ 目录，包含 {len(files_created)} 个文件/目录。",
    }

    return [mcp_types.TextContent(
        type="text",
        text=json.dumps(summary, ensure_ascii=False, indent=2),
    )]
