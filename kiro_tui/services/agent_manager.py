"""Agent Manager - Manages agent information and state"""
from dataclasses import dataclass
from typing import Optional
from .cli_executor import CLIExecutor


@dataclass
class Agent:
    """Agent information"""
    name: str
    is_active: bool = False
    
    def display_name(self) -> str:
        return f"{'● ' if self.is_active else ''}{self.name}"


class AgentManager:
    """Manages agents and their state"""
    
    def __init__(self, cli_executor: Optional[CLIExecutor] = None):
        self.cli_executor = cli_executor or CLIExecutor()
        self.active_agent: Optional[str] = None
    
    def list_agents(self) -> list[Agent]:
        """List all available agents with badges"""
        success, output, agent_tuples = self.cli_executor.agent_list()
        
        if not success or not agent_tuples:
            return []
        
        agents = []
        for name, is_active in agent_tuples:
            if is_active and not self.active_agent:
                self.active_agent = name
            active = (name == self.active_agent) if self.active_agent else is_active
            agents.append(Agent(name=name, is_active=active))
        
        return agents
    
    def _is_local_agent(self, name: str) -> bool:
        """Check if agent is local (in .kiro/agents/)"""
        import os
        return os.path.exists(f".kiro/agents/{name}.json")
    
    def _is_global_agent(self, name: str) -> bool:
        """Check if agent is global (in ~/.kiro/agents/)"""
        import os
        home = os.path.expanduser("~")
        return os.path.exists(f"{home}/.kiro/agents/{name}.json")
    
    def swap_agent(self, agent_name: str) -> tuple[bool, str]:
        """Swap to a different agent"""
        success, output = self.cli_executor.agent_swap(agent_name)
        if success:
            self.active_agent = agent_name
        return success, output
    
    def get_active_agent(self) -> Optional[str]:
        """Get currently active agent"""
        return self.active_agent

    def get_allowed_tools(self) -> set:
        """Read allowedTools from active agent config. Returns expanded tool names."""
        import os, json
        name = self.active_agent
        if not name:
            return set()
        for base in [".kiro/agents", os.path.expanduser("~/.kiro/agents")]:
            path = os.path.join(base, f"{name}.json")
            if os.path.exists(path):
                try:
                    with open(path, encoding="utf-8") as f:
                        return set(json.load(f).get("allowedTools", []))
                except Exception:
                    pass
        return set()
