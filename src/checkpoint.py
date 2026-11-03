"""APWA MCP Server - Checkpoint Resume Mechanism.

Implements the "execution lock / checkpoint resume" pattern described in
mcp-checkpoint-resume.md. Each Skill that has been partially or fully
executed gets its state persisted so users can resume after interruption.
"""

import json
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional

from config import OUTPUT_DIR


class CheckpointState(Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class CheckpointAction(Enum):
    SKIP = "skip"          # Output exists, user wants to skip
    RERUN = "rerun"        # Output exists, user wants to redo
    CONTINUE = "continue"  # Partial output exists, user wants to resume
    FRESH = "fresh"        # No output exists, normal execution


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def _ensure_output_dir() -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return OUTPUT_DIR


def _output_path(skill_id: int) -> Path:
    return _ensure_output_dir() / f"skill_{skill_id:02d}_output.json"


def _state_path(skill_id: int) -> Path:
    return _ensure_output_dir() / f"skill_{skill_id:02d}_state.json"


def _partial_path(skill_id: int, checkpoint_label: str) -> Path:
    return _ensure_output_dir() / f"skill_{skill_id:02d}_checkpoint_{checkpoint_label}.json"


# ---------------------------------------------------------------------------
# Output persistence
# ---------------------------------------------------------------------------

def load_skill_output(skill_id: int) -> dict:
    """Load a previous Skill's output JSON.  Raises FileNotFoundError if absent."""
    path = _output_path(skill_id)
    if not path.exists():
        raise FileNotFoundError(
            f"Skill {skill_id} 的输出文件不存在: {path}\n"
            f"请先运行 Skill {skill_id}。"
        )
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_skill_output_safe(skill_id: int) -> dict | None:
    """Load output without raising.  Returns None if absent or corrupted."""
    try:
        return load_skill_output(skill_id)
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        return None


def save_skill_output(skill_id: int, output: dict) -> None:
    """Save a Skill's output to JSON, appending metadata."""
    output["_meta"] = {
        "skill_id": skill_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0",
    }
    path = _output_path(skill_id)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Checkpoint state persistence
# ---------------------------------------------------------------------------

def check_skill_status(skill_id: int) -> tuple[CheckpointState, dict | None]:
    """Check if a Skill's output exists and its state.

    Returns (state, output_data_or_None).
    """
    output_path = _output_path(skill_id)
    state_path = _state_path(skill_id)

    # 1. Check state file first (authoritative)
    if state_path.exists():
        try:
            with open(state_path, "r", encoding="utf-8") as f:
                state = json.load(f)
            status = state.get("status", "not_started")

            if status == "in_progress":
                # Partial output may exist
                partial = None
                if output_path.exists():
                    try:
                        with open(output_path, "r", encoding="utf-8") as f:
                            partial = json.load(f)
                    except json.JSONDecodeError:
                        pass
                return CheckpointState.IN_PROGRESS, partial

            if status == "blocked":
                # Load partial/error output if present
                partial = None
                if output_path.exists():
                    try:
                        with open(output_path, "r", encoding="utf-8") as f:
                            partial = json.load(f)
                    except json.JSONDecodeError:
                        pass
                return CheckpointState.BLOCKED, partial

            if status == "failed":
                return CheckpointState.FAILED, None

            if status == "completed":
                if output_path.exists():
                    try:
                        with open(output_path, "r", encoding="utf-8") as f:
                            return CheckpointState.COMPLETED, json.load(f)
                    except json.JSONDecodeError:
                        return CheckpointState.FAILED, None
                return CheckpointState.IN_PROGRESS, None

        except (json.JSONDecodeError, KeyError):
            pass

    # 2. Fallback: check output file
    if output_path.exists():
        try:
            with open(output_path, "r", encoding="utf-8") as f:
                output = json.load(f)
            if "_meta" in output:
                return CheckpointState.COMPLETED, output
            return CheckpointState.IN_PROGRESS, output
        except json.JSONDecodeError:
            return CheckpointState.FAILED, None

    return CheckpointState.NOT_STARTED, None


def save_checkpoint_state(
    skill_id: int,
    status: str,
    checkpoint_data: dict | None = None,
    checkpoint_label: str = "",
) -> None:
    """Save/update the checkpoint state file.

    Args:
        skill_id: Skill ID (1-14).
        status: "not_started", "in_progress", "completed", or "failed".
        checkpoint_data: Optional data about the current checkpoint.
        checkpoint_label: If set, also saves a partial file for resume.
    """
    _ensure_output_dir()

    state = {
        "skill_id": skill_id,
        "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checkpoint_data": checkpoint_data or {},
    }
    path = _state_path(skill_id)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

    # Also save a named checkpoint for detailed resume
    if checkpoint_label and checkpoint_data:
        ckpt_path = _partial_path(skill_id, checkpoint_label)
        with open(ckpt_path, "w", encoding="utf-8") as f:
            json.dump(checkpoint_data, f, ensure_ascii=False, indent=2)


def load_checkpoint_data(skill_id: int, checkpoint_label: str) -> dict | None:
    """Load a saved checkpoint partial file."""
    path = _partial_path(skill_id, checkpoint_label)
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return None


def clear_skill_state(skill_id: int) -> None:
    """Remove all state and output files for a Skill (for rerun)."""
    for path in [
        _output_path(skill_id),
        _state_path(skill_id),
    ]:
        if path.exists():
            path.unlink()
    # Also remove any partial checkpoint files
    base = _ensure_output_dir()
    for p in base.glob(f"skill_{skill_id:02d}_checkpoint_*.json"):
        p.unlink()


def clear_all_states() -> None:
    """Remove all state and output files (full reset)."""
    base = _ensure_output_dir()
    for p in base.glob("skill_*_*.json"):
        p.unlink()


# ---------------------------------------------------------------------------
# Pipeline status report
# ---------------------------------------------------------------------------

def get_pipeline_status() -> dict:
    """Get the current status of all 14 Skills."""
    statuses: dict = {}
    for sid in range(1, 15):
        state, output = check_skill_status(sid)
        entry: dict = {
            "status": state.value,
            "skill_id": sid,
        }
        if output and "_meta" in output:
            entry["timestamp"] = output["_meta"].get("timestamp", "unknown")
            # Include top-level keys as a summary
            entry["output_keys"] = [k for k in output if k != "_meta"]
        statuses[f"skill_{sid:02d}"] = entry

    # Add overall progress
    completed = sum(1 for s in statuses.values() if s["status"] == "completed")
    in_progress = sum(1 for s in statuses.values() if s["status"] == "in_progress")
    failed = sum(1 for s in statuses.values() if s["status"] == "failed")
    statuses["_summary"] = {
        "total": 14,
        "completed": completed,
        "in_progress": in_progress,
        "failed": failed,
        "not_started": 14 - completed - in_progress - failed,
    }

    return statuses
