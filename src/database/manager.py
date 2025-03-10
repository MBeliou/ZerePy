import os
import logging
from sqlmodel import SQLModel, Session, create_engine, select
from typing import List, Optional, Dict, Any, Type, TypeVar, Generic
from .models import Agent, ConfigBase, Task
from pathlib import Path

logger = logging.getLogger("database.manager")

T = TypeVar('T', bound=SQLModel)


class DatabaseManager:
    """Manager for database operations"""

    def __init__(self, db_url: str = None):
        """Initialize the database manager

        Args:
            db_url: SQLite database URL (default: sqlite:///agents.db)
        """
        if db_url is None:
            # Ensure the data directory exists
            data_dir = Path("data")
            data_dir.mkdir(exist_ok=True)
            db_url = f"sqlite:///{data_dir}/agents.db"

        logger.info(f"Initializing database with URL: {db_url}")
        self.engine = create_engine(db_url, echo=False)
        self.create_tables()

    def create_tables(self):
        """Create all tables in the database"""
        logger.info("Creating database tables...")
        SQLModel.metadata.create_all(self.engine)

    def get_session(self) -> Session:
        """Get a new database session"""
        return Session(self.engine)

    def add_agent(self, agent_dict: Dict[str, Any]) -> Agent:
        """Add a new agent to the database

        Args:
            agent_dict: Dictionary containing agent data

        Returns:
            The created Agent instance
        """
        agent = Agent.from_dict(agent_dict)

        with self.get_session() as session:
            try:
                # Add the agent first to get an ID
                session.add(agent)
                session.commit()
                session.refresh(agent)

                agent_id = agent.id

                # Now add configs
                configs_data = agent_dict.get("configs", agent_dict.get("config", []))
                for config_data in configs_data:
                    config = ConfigBase.from_dict(config_data, agent_id)
                    session.add(config)

                # Add tasks
                tasks_data = agent_dict.get("tasks", [])
                for task_data in tasks_data:
                    task = Task(**task_data)
                    task.agent_id = agent_id
                    session.add(task)

                session.commit()
                session.refresh(agent)
                logger.info(f"Added agent {agent.name} (ID: {agent.id}) to database")

                if agent:
                    # Load relationships
                    _ = agent.configs
                    _ = agent.tasks
                return agent


            except Exception as e:
                logger.error(f"Error adding agent: {e}")
                session.rollback()
                raise


    def update_agent(self, agent_id: int, agent_dict: Dict[str, Any]) -> Optional[Agent]:
        """Update an existing agent in the database

        Args:
            agent_id: ID of the agent to update
            agent_dict: Dictionary containing updated agent data

        Returns:
            The updated Agent instance or None if not found
        """
        with self.get_session() as session:
            agent = session.get(Agent, agent_id)
            if not agent:
                logger.warning(f"Agent with ID {agent_id} not found")
                return None

            # Update scalar fields
            for key, value in agent_dict.items():
                if key not in ["id", "configs", "config", "tasks", "created_at"]:
                    if key in ["bio", "traits", "examples", "example_accounts", "time_based_multipliers"]:
                        import json
                        if not isinstance(value, str):
                            value = json.dumps(value)
                    setattr(agent, key, value)

            # Update configs if provided
            if "configs" in agent_dict or "config" in agent_dict:
                configs_data = agent_dict.get("configs", agent_dict.get("config", []))

                # Delete existing configs
                existing_configs = session.exec(
                    select(ConfigBase).where(ConfigBase.agent_id == agent_id)
                ).all()
                for config in existing_configs:
                    session.delete(config)

                # Add new configs
                for config_data in configs_data:
                    config = ConfigBase.from_dict(config_data, agent_id)
                    session.add(config)

            # Update tasks if provided
            if "tasks" in agent_dict:
                tasks_data = agent_dict["tasks"]

                # Delete existing tasks
                existing_tasks = session.exec(
                    select(Task).where(Task.agent_id == agent_id)
                ).all()
                for task in existing_tasks:
                    session.delete(task)

                # Add new tasks
                for task_data in tasks_data:
                    task = Task(**task_data)
                    task.agent_id = agent_id
                    session.add(task)

            session.commit()
            session.refresh(agent)
            logger.info(f"Updated agent {agent.name} (ID: {agent.id})")

            return agent

    def get_agent_by_id(self, agent_id: int) -> Optional[Agent]:
        """Get an agent by ID

        Args:
            agent_id: ID of the agent to retrieve

        Returns:
            The Agent instance or None if not found
        """
        with self.get_session() as session:
            agent = session.get(Agent, agent_id)
            if agent:
                # Load relationships
                _ = agent.configs
                _ = agent.tasks
            return agent

    def get_agent_by_name(self, agent_name: str) -> Optional[Agent]:
        """Get an agent by name

        Args:
            agent_name: Name of the agent to retrieve

        Returns:
            The Agent instance or None if not found
        """
        with self.get_session() as session:
            statement = select(Agent).where(Agent.name == agent_name)
            agent = session.exec(statement).first()
            if agent:
                # Load relationships
                _ = agent.configs
                _ = agent.tasks
            return agent

    def get_all_agents(self) -> List[Agent]:
        """Get all agents from the database

        Returns:
            List of all Agent instances
        """
        with self.get_session() as session:
            statement = select(Agent)
            agents = session.exec(statement).all()
            # Ensure relationships are loaded
            for agent in agents:
                _ = agent.configs
                _ = agent.tasks
            return agents

    def delete_agent(self, agent_id: int) -> bool:
        """Delete an agent from the database

        Args:
            agent_id: ID of the agent to delete

        Returns:
            True if the agent was deleted, False otherwise
        """
        with self.get_session() as session:
            agent = session.get(Agent, agent_id)
            if not agent:
                logger.warning(f"Agent with ID {agent_id} not found")
                return False

            session.delete(agent)
            session.commit()
            logger.info(f"Deleted agent {agent.name} (ID: {agent.id})")
            return True

    def import_from_json(self, agent_path: Path) -> Optional[Agent]:
        """Import an agent from a JSON file

        Args:
            agent_path: Path to the JSON file

        Returns:
            The imported Agent instance or None if import failed
        """
        try:
            import json
            with open(agent_path, "r") as f:
                agent_dict = json.load(f)

            # Check if agent already exists
            existing_agent = self.get_agent_by_name(agent_dict["name"])
            if existing_agent:
                logger.warning(f"Agent {agent_dict['name']} already exists, updating...")
                return self.update_agent(existing_agent.id, agent_dict)

            # Create new agent
            agent = self.add_agent(agent_dict)
            logger.info(f"Imported agent {agent.name} from {agent_path}")
            return agent

        except Exception as e:
            logger.error(f"Failed to import agent from {agent_path}: {e}")
        return None

    def export_to_json(self, agent_id: int, export_path: Path) -> bool:
        """Export an agent to a JSON file

        Args:
            agent_id: ID of the agent to export
            export_path: Path to save the JSON file

        Returns:
            True if export was successful, False otherwise
        """
        try:
            import json
            agent = self.get_agent_by_id(agent_id)
            if not agent:
                logger.warning(f"Agent with ID {agent_id} not found")
                return False

            agent_dict = agent.to_dict()
            with open(export_path, "w") as f:
                json.dump(agent_dict, f, indent=2)

            logger.info(f"Exported agent {agent.name} to {export_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to export agent {agent_id} to {export_path}: {e}")
            return False

    def import_legacy_agents(self, agents_dir: Path) -> List[Agent]:
        """Import legacy agents from the agents directory

        Args:
            agents_dir: Path to the agents directory

        Returns:
            List of imported Agent instances
        """
        imported_agents = []
        for agent_file in agents_dir.glob("*.json"):
            if agent_file.stem == "general":
                continue

            agent = self.import_from_json(agent_file)
            if agent:
                imported_agents.append(agent)

        return imported_agents


db_manager = DatabaseManager()