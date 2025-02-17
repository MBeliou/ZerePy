import json
import threading
import time
from pathlib import Path

from typing import Dict, List, Optional, final, IO
import logging

import asyncio

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

                    agents[self._make_safe_agent_name(config_data["name"])] = agent_config

            except Exception as e:
                logger.error(f"Error loading {config_file}: {e}")

        return agents

    def _save_agent_config(self, config: AgentConfig):
        exists = any(f"{config.name}.json" for f in self.config_dir.glob("*.json"))

    def add_agent(self, agent: AgentConfig):
        safe_name = self._make_safe_agent_name(agent.name)
        config_path = self._make_agent_file_path(safe_name)
        with open(config_path, "w") as f:
            json.dump(agent.model_dump(), f, indent=2)

        self.agent_configs[safe_name] = agent

    def get_agent(self, agent_id: str) -> Optional[AgentConfig]:
        safe_name = self._make_safe_agent_name(agent_id)
        return self.agent_configs.get(safe_name)

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
    def _make_safe_agent_name(agent_name: str):
        return agent_name.replace(' ', '_').lower()

    @staticmethod
    def _make_agent_file_name(agent_name: str):
        return f"{ServerState._make_safe_agent_name(agent_name)}.json"

    def _make_agent_file_path(self, agent_name: str):
        return self.config_dir / self._make_agent_file_name(agent_name)

    async def start_agent(self, agent_name: str) -> bool:
        logger.info(f"Attempting to start agent: {agent_name}")

        # Make sure agent config actually exists
        safe_name = self._make_safe_agent_name(agent_name)
        agent = self.agent_configs.get(safe_name)
        if agent is None:
            logger.error(f"No config found for agent: {safe_name}")
            return False

        # Make sure it isn't already running
        agent_loop = self.agent_loops.get(safe_name)
        if agent_loop is not None:
            is_running = await agent_loop.is_running()
            if is_running:
                logger.info(f"Agent {safe_name} is already running")
                return False

        try:
            logger.info(f"Creating new agent and controller for {safe_name}")
            agent = ZerePyAgent(agent_name)
            controller = AgentController(agent)
            self.agent_loops[safe_name] = controller

            logger.info(f"Starting agent loop for {safe_name}")
            await controller.start_agent_loop()

            logger.info(f"Successfully started agent {safe_name}")
            return True

        except Exception as e:
            logger.error(f"Couldn't start agent loop for {safe_name}: {e}", exc_info=True)
            return False

    async def stop_agent(self, agent_name: str) -> bool:
        safe_name = self._make_safe_agent_name(agent_name)
        agent_loop = self.agent_loops.get(safe_name)

        if agent_loop is not None:
            await agent_loop.stop_agent_loop()
            return True

        return True


class AgentController:
    def __init__(self, agent: "ZerePyAgent"):
        if agent is None:
            raise ValueError("Agent cannot be None")
        self.agent: final = agent

        self._stop_event = asyncio.Event()
        self._task: Optional[asyncio.Task] = None
        self._running_lock = asyncio.Lock()

    async def is_running(self) -> bool:
        """Check if the agent loop is running"""
        return self._task is not None and not self._task.done()

    async def _run_agent_loop(self):
        """Run agent loop in asyncio task"""
        try:
            logger.info(f"Agent loop starting for {self.agent.name}")
            while not self._stop_event.is_set():
                try:
                    logger.info(f"Loop iteration for {self.agent.name}")
                    logger.info(f"Stop event status: {self._stop_event.is_set()}")

                    try:
                        await asyncio.wait_for(self._stop_event.wait(), timeout=0.1)
                        logger.info(f"Stop event detected for {self.agent.name}")
                        break
                    except asyncio.TimeoutError:
                        pass

                except Exception as e:
                    logger.error(f"Error in agent action for {self.agent.name}: {e}")
                    try:
                        await asyncio.wait_for(self._stop_event.wait(), timeout=5)
                        logger.info(f"Stop event detected during error recovery for {self.agent.name}")
                        break
                    except asyncio.TimeoutError:
                        pass

        except Exception as e:
            logger.error(f"Error in agent loop for {self.agent.name}: {e}")
        finally:
            logger.info(f"Agent task for {self.agent.name} is about to shut down")
            async with self._running_lock:
                self._task = None
                logger.info(f"Agent loop stopped for {self.agent.name}")

    async def start_agent_loop(self):
        """Start the agent loop as an asyncio task"""
        async with self._running_lock:
            if await self.is_running():
                raise ValueError(f"Agent {self.agent.name} is already running")

            self._stop_event.clear()
            self._task = asyncio.create_task(self._run_agent_loop())

    async def stop_agent_loop(self, timeout: float = 5.0) -> bool:
        """Stop the agent loop"""
        logger.info(f"Initiating stop for agent {self.agent.name}")

        async with self._running_lock:
            if not await self.is_running():  # Changed to method call
                logger.info(f"Agent {self.agent.name} already stopped")
                return True
            current_task = self._task

        logger.info(f"Setting stop event for {self.agent.name}")
        self._stop_event.set()

        if current_task:
            logger.info(f"Waiting for task to complete for {self.agent.name}")
            try:
                await asyncio.wait_for(current_task, timeout=timeout)
                logger.info(f"Task completed for {self.agent.name}")
            except asyncio.TimeoutError:
                logger.error(f"Timeout waiting for {self.agent.name} to stop")
                return False

        async with self._running_lock:
            stopped = not await self.is_running()  # Changed to method call
            if not stopped:
                logger.error(f"Failed to stop agent {self.agent.name}'s loop")
            else:
                logger.info(f"Successfully stopped agent {self.agent.name}")
            return stopped
