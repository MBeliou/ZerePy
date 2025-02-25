import json
import threading
import time
import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

from src.agent import ZerePyAgent
from src.database.manager import db_manager
from src.database.utils import create_zerepy_agent_from_db
from src.server.app import ActionRequest

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("matriarch/server")


class AgentController:
    def __init__(self, agent: "ZerePyAgent"):
        if agent is None:
            raise ValueError("Agent cannot be None")
        self.agent: ZerePyAgent = agent

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
                        await asyncio.wait_for(self._stop_event.wait(), timeout=2.0)
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
            if not await self.is_running():
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
            stopped = not await self.is_running()
            if not stopped:
                logger.error(f"Failed to stop agent {self.agent.name}'s loop")
            else:
                logger.info(f"Successfully stopped agent {self.agent.name}")
            return stopped

    async def request_action(self, action_request: ActionRequest):
        try:
            ret = self.agent.perform_action(action_request.connection, action_request.action,
                                            params=action_request.params)
            return ret
        except Exception as e:
            logger.error(f"Couldn't run action {action_request.action} with agent {self.agent.name}: {e}")
            raise Exception(f"Couldn't run action {action_request.action} with agent {self.agent.name}: {e}")


class ServerState:
    def __init__(self, config_dir: str = "agents"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        logger.info(f"Config directory is located: {self.config_dir}")

        # Import legacy agents if they exist
        self._import_legacy_agents()

        # Track running agent controllers
        self.agent_loops: Dict[str, Optional[AgentController]] = {}

    def get_agent(self, agent_id: str) -> Optional[dict]:
        """Get an agent by name or ID

        Args:
            agent_id: Name or ID of the agent

        Returns:
            Agent as dictionary or None if not found
        """
        try:
            # Try to parse as integer ID
            agent_id_int = int(agent_id)
            agent = db_manager.get_agent_by_id(agent_id_int)
        except ValueError:
            # If not an integer, treat as name
            safe_name = self._make_safe_agent_name(agent_id)
            agent = db_manager.get_agent_by_name(safe_name)

        if agent:
            return agent.to_dict()
        return None

    def get_all_agents(self) -> List[dict]:
        """Get all agents

        Returns:
            List of all agents as dictionaries
        """
        return [agent.to_dict() for agent in db_manager.get_all_agents()]

    def add_agent(self, agent_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add a new agent

        Args:
            agent_data: Agent data as dictionary

        Returns:
            The created agent as dictionary
        """
        agent = db_manager.add_agent(agent_data)
        return agent.to_dict()

    def update_agent(self, agent_id: str, agent_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update an existing agent

        Args:
            agent_id: Name or ID of the agent
            agent_data: Updated agent data

        Returns:
            The updated agent as dictionary or None if not found
        """
        try:
            # Try to parse as integer ID
            agent_id_int = int(agent_id)
            agent = db_manager.update_agent(agent_id_int, agent_data)
        except ValueError:
            # If not an integer, treat as name
            safe_name = self._make_safe_agent_name(agent_id)
            db_agent = db_manager.get_agent_by_name(safe_name)
            if db_agent:
                agent = db_manager.update_agent(db_agent.id, agent_data)
            else:
                return None

        if agent:
            return agent.to_dict()
        return None

    def delete_agent(self, agent_id: str) -> bool:
        """Delete an agent

        Args:
            agent_id: Name or ID of the agent

        Returns:
            True if agent was deleted, False otherwise
        """
        try:
            # Try to parse as integer ID
            agent_id_int = int(agent_id)
            return db_manager.delete_agent(agent_id_int)
        except ValueError:
            # If not an integer, treat as name
            safe_name = self._make_safe_agent_name(agent_id)
            db_agent = db_manager.get_agent_by_name(safe_name)
            if db_agent:
                return db_manager.delete_agent(db_agent.id)
            return False

    def _import_legacy_agents(self):
        """Import legacy agents from the config directory"""
        if self.config_dir.exists():
            logger.info(f"Importing legacy agents from {self.config_dir}")
            imported = db_manager.import_legacy_agents(self.config_dir)
            logger.info(f"Imported {len(imported)} legacy agents")

    def _make_safe_agent_name(self, agent_name: str) -> str:
        """Create a safe agent name for file storage"""
        return agent_name.replace(' ', '_').lower()

    async def start_agent(self, agent_name: str) -> bool:
        """Start an agent loop"""
        logger.info(f"Attempting to start agent: {agent_name}")

        # Check if agent exists in database
        safe_name = self._make_safe_agent_name(agent_name)
        db_agent = db_manager.get_agent_by_name(safe_name)

        if not db_agent:
            logger.error(f"No agent found with name: {safe_name}")
            return False

        # Check if agent is already running
        agent_loop = self.agent_loops.get(safe_name)
        if agent_loop is not None:
            is_running = await agent_loop.is_running()
            if is_running:
                logger.info(f"Agent {safe_name} is already running")
                return False

        try:
            # Create ZerePyAgent from database agent
            zerepy_agent = create_zerepy_agent_from_db(db_agent)
            controller = AgentController(zerepy_agent)
            self.agent_loops[safe_name] = controller

            logger.info(f"Starting agent loop for {safe_name}")
            await controller.start_agent_loop()

            logger.info(f"Successfully started agent {safe_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to start agent {safe_name}: {e}")
            return False

    async def stop_agent(self, agent_name: str) -> bool:
        """Stop a running agent"""
        safe_name = self._make_safe_agent_name(agent_name)
        agent_loop = self.agent_loops.get(safe_name)

        if agent_loop is not None:
            await agent_loop.stop_agent_loop()
            return True

        return True

    async def request_action(self, agent_name: str, action_request: ActionRequest):
        """Request an action from an agent"""
        safe_name = self._make_safe_agent_name(agent_name)
        controller = self.agent_loops.get(safe_name)

        if controller is not None:
            return await controller.request_action(action_request)

        # If agent is not running, try to create it temporarily
        db_agent = db_manager.get_agent_by_name(safe_name)
        if not db_agent:
            logger.error(f"No agent found with name: {safe_name}")
            return None

        try:
            # Create ZerePyAgent from database agent
            zerepy_agent = create_zerepy_agent_from_db(db_agent)
            return zerepy_agent.perform_action(
                action_request.connection,
                action_request.action,
                params=action_request.params
            )
        except Exception as e:
            logger.error(f"Failed to perform action: {e}")
            return None
