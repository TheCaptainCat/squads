from squads._backends._agents_md._backend import AgentsMdBackend
from squads._backends._registry import register

register(AgentsMdBackend)

__all__ = ["AgentsMdBackend"]
