# agent/tools/llm_log_analyzer.py
"""
Tools for the agent to query and summarize its own LLM call history.
Reads from memory/llm-calls.log.jsonl (JSON Lines format).
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

LLM_LOG_PATH = Path.home() / "makobot" / "memory" / "llm-calls.log.jsonl"

def execute_llm_log_tool(tool_name: str, args: Dict[str, Any], current_goal_id: Optional[int] = None) -> str:
    """
    Dispatcher for LLM log analysis tools.
    """
    if tool_name == "summarize_llm_logs":
        return summarize_llm_logs(
            days_back=args.get("days_back", 7),
            limit=args.get("limit", 50)
        )
    elif tool_name == "query_llm_logs":
        return query_llm_logs(
            filter_expr=args.get("filter_expr", ""),
            limit=args.get("limit", 20)
        )
    else:
        return f"Unknown LLM log tool: {tool_name}"


# ─── Core Functions ─────────────────────────────────────────────────────────

def load_recent_logs(days_back: int = 7, limit: int = 200) -> List[Dict]:
    """Load the most recent log entries from JSONL file."""
    if not LLM_LOG_PATH.exists():
        return []

    cutoff = datetime.utcnow() - timedelta(days=days_back)
    logs = []

    with open(LLM_LOG_PATH, "r", encoding="utf-8") as f:
        for line in f:
            try:
                entry = json.loads(line.strip())
                ts = datetime.fromisoformat(entry["timestamp"].replace("Z", "+00:00"))
                if ts >= cutoff:
                    logs.append(entry)
            except (json.JSONDecodeError, KeyError, ValueError):
                continue  # skip malformed lines

    # Most recent first
    logs.sort(key=lambda x: x["timestamp"], reverse=True)
    return logs[:limit]


def summarize_llm_logs(days_back: int = 7, limit: int = 50) -> str:
    """Generate a human-readable summary of recent LLM calls."""
    logs = load_recent_logs(days_back, limit)

    if not logs:
        return f"No LLM calls found in the last {days_back} days."

    total_calls = len(logs)
    models = {}
    total_input_tokens = 0
    total_output_tokens = 0
    total_duration = 0
    success_count = 0
    tool_call_count = 0

    for entry in logs:
        model = entry.get("model", "unknown")
        models[model] = models.get(model, 0) + 1
        total_input_tokens += entry.get("input_tokens", 0) or 0
        total_output_tokens += entry.get("output_tokens", 0) or 0
        total_duration += entry.get("duration_sec", 0)
        if entry.get("success", False):
            success_count += 1
        tool_call_count += entry.get("tool_calls", 0)

    avg_duration = total_duration / total_calls if total_calls > 0 else 0
    success_rate = (success_count / total_calls * 100) if total_calls > 0 else 0

    summary = f"LLM Call Summary (last {days_back} days, up to {total_calls} calls):\n\n"
    summary += f"• Total calls: {total_calls}\n"
    summary += f"• Success rate: {success_rate:.1f}%\n"
    summary += f"• Average duration: {avg_duration:.2f} seconds\n"
    summary += f"• Total input tokens: {total_input_tokens:,}\n"
    summary += f"• Total output tokens: {total_output_tokens:,}\n"
    summary += f"• Total tool calls made: {tool_call_count}\n\n"
    summary += "Models used:\n"
    for m, count in sorted(models.items(), key=lambda x: x[1], reverse=True):
        summary += f"  - {m}: {count} calls\n"

    if logs:
        latest = logs[0]
        summary += f"\nMost recent call ({latest['timestamp']}):\n"
        summary += f"  Model: {latest.get('model')}\n"
        summary += f"  Prompt snippet: {latest.get('user_prompt_snippet', '—')}\n"
        summary += f"  Response snippet: {latest.get('response_snippet', '—')}\n"

    return summary


def query_llm_logs(filter_expr: str = "", limit: int = 20) -> str:
    """
    Query LLM logs with a simple text filter.
    Examples of filter_expr:
    - "model:Qwen duration>10"
    - "success:false"
    - "tool_calls>0"
    """
    logs = load_recent_logs(days_back=30, limit=500)  # wider window for queries

    if not logs:
        return "No logs available."

    results = []

    # Very simple keyword filtering (expand later with real query parser if needed)
    filters = filter_expr.lower().split()

    for entry in logs[:limit * 5]:  # overscan then slice
        match = True

        for f in filters:
            if ":" in f:
                key, val = f.split(":", 1)
                if key == "model" and val not in entry.get("model", "").lower():
                    match = False
                elif key == "duration" and ">" in val:
                    thresh = float(val.split(">")[1])
                    if entry.get("duration_sec", 0) <= thresh:
                        match = False
            elif "success:false" in f and entry.get("success", True):
                match = False
            elif "tool_calls" in f and ">" in f:
                thresh = int(f.split(">")[1])
                if entry.get("tool_calls", 0) <= thresh:
                    match = False

        if match:
            results.append(entry)
            if len(results) >= limit:
                break

    if not results:
        return f"No matching LLM calls found for filter: '{filter_expr}'"

    output = f"Found {len(results)} matching LLM calls:\n\n"
    for i, e in enumerate(results, 1):
        output += f"{i}. {e['timestamp']} | {e.get('model')} | "
        output += f"dur={e.get('duration_sec','—')}s | "
        output += f"tools={e.get('tool_calls',0)} | "
        output += f"in={e.get('input_tokens','—'):,} out={e.get('output_tokens','—'):,}\n"
        output += f"   Prompt: {e.get('user_prompt_snippet','—')}\n"
        output += f"   Response: {e.get('response_snippet','—')}\n\n"

    return output


# ─── Tool Schemas ──────────────────────────────────────────────────────────

LLM_LOG_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "summarize_llm_logs",
            "description": "Get a summary of recent LLM calls (models used, latency, tokens, success rate). Useful for performance review.",
            "parameters": {
                "type": "object",
                "properties": {
                    "days_back": {"type": "integer", "description": "Look back this many days", "default": 7},
                    "limit": {"type": "integer", "description": "Max calls to analyze", "default": 50}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_llm_logs",
            "description": "Search LLM call history with simple filters (e.g. 'model:Qwen duration>10 success:false'). Returns matching entries.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filter_expr": {"type": "string", "description": "Filter string (space-separated keywords or key:value)"},
                    "limit": {"type": "integer", "description": "Max results to return", "default": 20}
                }
            }
        }
    }
    ]
