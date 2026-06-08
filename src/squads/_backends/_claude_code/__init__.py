from squads._backends._claude_code._backend import ClaudeCodeBackend
from squads._backends._registry import register

register(ClaudeCodeBackend)

__all__ = ["ClaudeCodeBackend"]
