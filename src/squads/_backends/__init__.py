"""The agent backend interface, its registry and the managed-region wrapper."""

from squads._backends._base import AgentBackend as AgentBackend
from squads._backends._base import BackendContext as BackendContext
from squads._backends._claude_code import render_skill_pointer as render_skill_pointer
from squads._backends._registry import get_backend as get_backend
