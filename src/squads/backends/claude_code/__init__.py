from squads.backends.claude_code.backend import ClaudeCodeBackend
from squads.backends.registry import register

register(ClaudeCodeBackend)

__all__ = ["ClaudeCodeBackend"]
