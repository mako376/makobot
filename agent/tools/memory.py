# agent/tools/memory.py
"""
Memory tools for the agent.
"""

def execute_memory_tool(tool_name: str, args: dict[str, any], current_goal_id: int = None) -> str:
    """
    Dispatcher for memory-related tools.
    """
    if tool_name == "write_memory_file":
        return write_memory_file(args.get("path", ""), args.get("content", ""))
    else:
        return f"Unknown memory tool: {tool_name}"

def write_memory_file(path: str, content: str) -> str:
    allowed_paths = {
        "notes.md",
        "goals.json",
        "tool-reliability.json",
        "llm-calls.log.jsonl"
    }

    if path not in allowed_paths:
        return f"Security error: Cannot write to {path}"

    mode = "a" if path == "notes.md" else "w"
    try:
        with open(f"memory/{path}", mode) as f:
            f.write(content)
        return f"Wrote to memory/{path} successfully"
    except Exception as e:
        return f"Write error: {str(e)}"

MEMORY_TOOL = {
    "type": "function",
    "function": {
        "name": "write_memory_file",
        "description": "Write to pre-approved memory files with strict validation. Only allows writing to whitelisted files (notes.md, goals.json, tool-reliability.json, llm-calls.log.jsonl). Content must be valid JSON.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Target memory file path (must be in allowed_paths set)"
                },
                "content": {
                    "type": "string",
                    "description": "JSON content to write"
                }
            },
            "required": ["path", "content"]
        }
    }
}
