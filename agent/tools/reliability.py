# agent/tools/reliability.py
"""
Tools for recording and querying the reliability of tool calls.
Stores data in agent-memory/tool-reliability.json
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional

RELIABILITY_FILE = Path.home() / "makobot" / "memory" / "tool-reliability.json"

def execute_reliability_tool(tool_name: str, args: Dict[str, Any], current_goal_id: Optional[int] = None) -> str:
    """
    Dispatcher for reliability-related tools.
    """
    if tool_name == "record_tool_reliability":
        return record_tool_reliability(
            tool_name=args.get("tool_name"),
            goal_id=args.get("goal_id", current_goal_id),
            success=args.get("success", False),
            helpfulness=args.get("helpfulness", 0.5),
            notes=args.get("notes", "")
        )
    elif tool_name == "list_tool_reliability":
        return list_tool_reliability(
            goal_id=args.get("goal_id"),
            include_global=args.get("include_global", True)
        )
    else:
        return f"Unknown reliability tool: {tool_name}"


# ─── Core Functions ─────────────────────────────────────────────────────────

def load_reliability_data() -> Dict:
    """Load or initialize the reliability JSON."""
    if RELIABILITY_FILE.exists():
        try:
            with open(RELIABILITY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    # Default empty structure
    return {
        "global": {},
        "per_goal": {}
    }


def save_reliability_data(data: Dict):
    """Save updated reliability stats."""
    RELIABILITY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(RELIABILITY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def record_tool_reliability(
    tool_name: str,
    goal_id: Optional[int],
    success: bool,
    helpfulness: float,  # 0.0 to 1.0
    notes: str = ""
) -> str:
    """Record reliability metrics after a tool call."""
    if not tool_name:
        return "Error: tool_name required"

    data = load_reliability_data()

    # Global stats
    if tool_name not in data["global"]:
        data["global"][tool_name] = {
            "calls": 0,
            "success_count": 0,
            "helpfulness_sum": 0.0,
            "notes": []
        }
    g = data["global"][tool_name]
    g["calls"] += 1
    if success:
        g["success_count"] += 1
    g["helpfulness_sum"] += max(0.0, min(1.0, helpfulness))
    if notes:
        g["notes"].append(notes)

    # Per-goal stats (if goal_id provided)
    if goal_id is not None:
        goal_key = str(goal_id)
        if goal_key not in data["per_goal"]:
            data["per_goal"][goal_key] = {}
        if tool_name not in data["per_goal"][goal_key]:
            data["per_goal"][goal_key][tool_name] = {
                "calls": 0,
                "success_count": 0,
                "helpfulness_sum": 0.0
            }
        p = data["per_goal"][goal_key][tool_name]
        p["calls"] += 1
        if success:
            p["success_count"] += 1
        p["helpfulness_sum"] += max(0.0, min(1.0, helpfulness))

    save_reliability_data(data)

    success_pct = (g["success_count"] / g["calls"] * 100) if g["calls"] > 0 else 0
    avg_help = g["helpfulness_sum"] / g["calls"] if g["calls"] > 0 else 0

    return (
        f"Reliability recorded for '{tool_name}': "
        f"success={success}, helpfulness={helpfulness:.2f}\n"
        f"Global stats: {g['calls']} calls, {success_pct:.1f}% success, "
        f"avg helpfulness {avg_help:.2f}"
    )


def list_tool_reliability(goal_id: Optional[int] = None, include_global: bool = True) -> str:
    """Show reliability stats for tools, optionally filtered to a specific goal."""
    data = load_reliability_data()

    lines = []

    if include_global and data["global"]:
        lines.append("Global tool reliability:")
        for tool, stats in sorted(data["global"].items(), key=lambda x: x[1]["calls"], reverse=True):
            calls = stats["calls"]
            success_pct = (stats["success_count"] / calls * 100) if calls > 0 else 0
            avg_help = stats["helpfulness_sum"] / calls if calls > 0 else 0
            lines.append(
                f"  • {tool}: {calls} calls, {success_pct:.1f}% success, "
                f"avg helpfulness {avg_help:.2f}"
            )
        lines.append("")

    if goal_id is not None:
        goal_key = str(goal_id)
        if goal_key in data["per_goal"] and data["per_goal"][goal_key]:
            lines.append(f"Goal {goal_id} specific tool reliability:")
            for tool, stats in sorted(data["per_goal"][goal_key].items(), key=lambda x: x[1]["calls"], reverse=True):
                calls = stats["calls"]
                success_pct = (stats["success_count"] / calls * 100) if calls > 0 else 0
                avg_help = stats["helpfulness_sum"] / calls if calls > 0 else 0
                lines.append(
                    f"  • {tool}: {calls} calls, {success_pct:.1f}% success, "
                    f"avg helpfulness {avg_help:.2f}"
                )
        else:
            lines.append(f"No per-goal data for goal {goal_id} yet.")

    if not lines:
        return "No tool reliability data recorded yet."

    return "\n".join(lines)


# ─── Tool Schemas ──────────────────────────────────────────────────────────

RELIABILITY_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "record_tool_reliability",
            "description": "After using a tool, record how successful and helpful it was for the current goal.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tool_name": {"type": "string", "description": "Name of the tool used"},
                    "goal_id": {"type": "integer", "description": "ID of the current focus goal (optional but recommended)"},
                    "success": {"type": "boolean", "description": "Did the tool succeed without critical error?"},
                    "helpfulness": {"type": "number", "minimum": 0, "maximum": 1, "description": "0.0–1.0 how much it advanced the goal"},
                    "notes": {"type": "string", "description": "Optional short observation"}
                },
                "required": ["tool_name", "success", "helpfulness"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_tool_reliability",
            "description": "View aggregated reliability stats for tools (global and/or per-goal).",
            "parameters": {
                "type": "object",
                "properties": {
                    "goal_id": {"type": "integer", "description": "Specific goal ID to filter on (optional)"},
                    "include_global": {"type": "boolean", "description": "Include global stats", "default": True}
                }
            }
        }
    }
]
