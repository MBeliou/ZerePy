import json
from pathlib import Path

from pydantic import BaseModel
from dataclasses import dataclass
from typing import Dict, List, Optional

from src.matriarch.models.configuration import AgentConfig


class ServerState:
    def __init__(self, config_dir: str = "agents"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        print(f"Config directory is located: {self.config_dir}")

        self.agents: Dict[str, AgentConfig] = self._load_agents()

    def _load_agents(self):
        agents = {}
        for config_file in filter(lambda x: x.stem != "general", self.config_dir.glob("*.json")):
            try:
                with open(config_file, "r") as f:
                    config_data = json.load(f)
                    # print(config_data)
                    agent_config = AgentConfig(**config_data)

                    agents[agent_config] = agent_config

            except Exception as e:
                print(f"Error loading {config_file}: {e}")
        return agents

    def add_agent(self, agent: AgentConfig):
        self.agents[agent.id] = agent

    def get_agent(self, agent_id: str) -> Optional[AgentConfig]:
        return self.agents.get(agent_id)

    def get_all_agents(self) -> List[AgentConfig]:
        return list(self.agents.values())

    def delete_agent(self, agent_name: str) -> bool:
        return False
