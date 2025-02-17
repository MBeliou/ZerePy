import json
import threading
from pathlib import Path

from typing import Dict, List, Optional, final
import logging

from src.agent import ZerePyAgent
from src.matriarch.models.configuration import AgentConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("matriarch/server")


class ServerState:
    def __init__(self, config_dir: str = "agents"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        logger.info(f"Config directory is located: {self.config_dir}")

        self.agent_configs: Dict[str, AgentConfig] = self._load_agents()
        self.agent_loops: Dict[str, Optional[AgentController]] = {}

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
                logger.error(f"Error loading {config_file}: {e}")
        return agents

    def _save_agent(self, config: AgentConfig):
        exists = any(f"{config.name}.json" for f in self.config_dir.glob("*.json"))

    def add_agent(self, agent: AgentConfig):
        self.agent_configs[agent.id] = agent

    def get_agent(self, agent_id: str) -> Optional[AgentConfig]:
        return self.agent_configs.get(agent_id)

    def get_all_agents(self) -> List[AgentConfig]:
        return list(self.agent_configs.values())

    def delete_agent(self, agent_name: str) -> bool:
        agent_config = self.agent_configs.get(agent_name)
        if agent_config is None:
            return False

        agent_controller = self.agent_loops.get(agent_name)
        if agent_controller is None:
            return False

        # Stop loop then delete agent
        agent_controller.stop_agent_loop()
        del self.agent_loops[agent_name]

        config_path = self._make_agent_file_path(agent_name)
        if config_path.exists():
            config_path.unlink()

        return True

    @staticmethod
    def _make_agent_file_name(agent_name: str):
        return f"{agent_name.replace(' ', '_').lower()}.json"

    def _make_agent_file_path(self, agent_name: str):
        return self.config_dir / self._make_agent_file_name(agent_name)

    def start_agent(self, agent_name: str) -> bool:
        # Make sure agent config actually exists
        agent = self.agent_configs.get(agent_name)
        if agent is None:
            return False

        # Make sure it isn't already running
        agent_loop = self.agent_loops.get(agent_name)
        if agent_loop is not None:
            return False

        try:
            agent = ZerePyAgent(agent_name)
            self.agent_loops[agent_name] = AgentController(agent)

            return True

        except Exception as e:
            logger.error(f"Couldn't start agent loop: {e}")
            return False


class AgentController:
    def __init__(self, agent: ZerePyAgent):
        if agent is None:
            raise ValueError("Agent cannot be None")
        self.agent: final = agent

        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._running_lock = threading.Lock()

    @property
    def is_running(self) -> bool:
        """Thread-safe way to check if the agent loop is running"""
        with self._running_lock:
            return self._thread is not None and self._thread.is_alive()

    def _run_agent_loop(self):
        """Run agent loop in a separate thread"""
        try:
            while not self._stop_event.is_set():
                try:
                    # Agent loop logic here
                    logger.info("Loop iteration")

                    # Add a small sleep to prevent tight loop
                    if self._stop_event.wait(timeout=0.1):
                        break

                except Exception as e:
                    logger.error(f"Error in agent action: {e}")
                    if self._stop_event.wait(timeout=5):
                        break

        except Exception as e:
            logger.error(f"Error in agent loop thread: {e}")
        finally:
            with self._running_lock:
                self._thread = None
                logger.info("Agent loop stopped")

    def start_agent_loop(self):
        with self._running_lock:
            if self.is_running:
                raise ValueError(f"Agent {self.agent.name} is already running")

            self._stop_event.clear()

            self._thread = threading.Thread(target=self._run_agent_loop())
            self._thread.daemon = True  # Allows exiting the app even if the agent is still running
            self._thread.start()

    def stop_agent_loop(self, timeout: float = 5.0) -> bool:
        thread = None
        with self._running_lock:
            if not self.is_running:
                return True
            thread = self._thread

        self._stop_event.set()
        thread.join(timeout)

        with self._running_lock:
            stopped = not self.is_running
            if not stopped:
                logger.error(f"Failed to stop agent {self.agent.name}'s loop within timeout")
            return stopped
