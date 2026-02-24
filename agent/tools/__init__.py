# defines:
# ALL_TOOLS: list of tool JSON schemas
# execute_tool(name, args, current_goal_id=None): dispatcher that calls the real function and returns string result

from .github import GITHUB_TOOLS, execute_github_tool
from .llm_log_analyzer import LLM_LOG_TOOLS, execute_llm_log_tool
from .reliability import RELIABILITY_TOOLS, execute_reliability_tool
from .shell import SHELL_TOOLS, execute_shell_tool
from .memory import MEMORY_TOOL, execute_memory_tool

ALL_TOOLS = SHELL_TOOLS
ALL_TOOLS.extend(GITHUB_TOOLS) # extend with other modules later
ALL_TOOLS.extend(LLM_LOG_TOOLS)
ALL_TOOLS.extend(RELIABILITY_TOOLS)
ALL_TOOLS.extend([MEMORY_TOOL])

def execute_tool(name: str, args: dict, current_goal_id=None):
    if name == "write_memory_file":
        return execute_memory_tool("write_memory_file", args)
    elif name in [t["function"]["name"] for t in RELIABILITY_TOOLS]:
        return execute_reliability_tool(name, args, current_goal_id)
    elif name in [t["function"]["name"] for t in LLM_LOG_TOOLS]:
        return execute_llm_log_tool(name, args, current_goal_id)
    elif name in [t["function"]["name"] for t in SHELL_TOOLS]:
        return execute_shell_tool(name, args, current_goal_id)
    elif name in [t["function"]["name"] for t in GITHUB_TOOLS]:
        return execute_github_tool(name, args, current_goal_id)
    return f"Tool '{name}' not implemented in any module yet."
