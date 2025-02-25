"""Utility functions for database operations"""
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from .models import Agent, ConfigBase, TwitterConfig, OpenAIConfig, AnthropicConfig, DiscordConfig, NetworkConfig, Task, FarcasterConfig
from src.agent import ZerePyAgent

logger = logging.getLogger("database.utils")

def convert_db_agent_to_json(agent: Agent) -> Dict[str, Any]:
    """Convert a database agent to a JSON-compatible dictionary

    Args:
        agent: Agent model instance

    Returns:
        Dictionary representation of the agent
    """
    # Convert JSON fields from strings to Python objects
    agent_dict = agent.to_dict()

    return agent_dict

def convert_json_to_db_agent(data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a JSON-compatible dictionary to a database agent

    Args:
        data: Dictionary containing agent data

    Returns:
        Dictionary with properly formatted fields for database storage
    """
    agent_dict = data.copy()

    # Convert list fields to JSON strings
    for field in ["bio", "traits", "examples", "example_accounts", "time_based_multipliers"]:
        if field in agent_dict and not isinstance(agent_dict[field], str):
            agent_dict[field] = json.dumps(agent_dict[field])

    return agent_dict

def create_zerepy_agent_from_db(agent: Agent) -> ZerePyAgent:
    """Create a ZerePyAgent instance from a database agent

    Args:
        agent: Agent model instance

    Returns:
        ZerePyAgent instance
    """
    # First, export the agent to a temporary JSON file
    import tempfile
    import os

    temp_dir = Path(tempfile.gettempdir()) / "zerepy"
    temp_dir.mkdir(exist_ok=True)

    agent_file = temp_dir / f"{agent.name.lower().replace(' ', '_')}.json"

    with open(agent_file, "w") as f:
        json.dump(agent.to_dict(), f, indent=2)

    # Create the ZerePyAgent from the temporary file
    try:
        zerepy_agent = ZerePyAgent(agent_file.stem)
        return zerepy_agent
    except Exception as e:
        logger.error(f"Failed to create ZerePyAgent from database agent: {e}")
        raise

def get_config_by_type(configs: List[ConfigBase], config_type: str) -> Optional[ConfigBase]:
    """Get a config by type

    Args:
        configs: List of ConfigBase instances
        config_type: Type of config to find

    Returns:
        ConfigBase instance or None if not found
    """
    for config in configs:
        if config.name == config_type:
            return config
    return None

def create_config(config_data: Dict[str, Any]) -> ConfigBase:
    """Create a config instance based on the config type

    Args:
        config_data: Dictionary containing config data

    Returns:
        ConfigBase instance
    """
    config_type = config_data.get("name")
    if config_type == "twitter":
        return TwitterConfig(**config_data)
    elif config_type == "openai":
        return OpenAIConfig(**config_data)
    elif config_type == "anthropic":
        return AnthropicConfig(**config_data)
    elif config_type == "discord":
        return DiscordConfig(**config_data)
    elif config_type == "farcaster":
        return FarcasterConfig(**config_data)
    elif config_type in ["solana", "ethereum", "sonic"]:
        return NetworkConfig(**config_data)
    else:
        return ConfigBase(**config_data)

def load_default_agent() -> Optional[str]:
    """Load the default agent name from general.json

    Returns:
        Name of the default agent or None if not found
    """
    general_path = Path("agents") / "general.json"
    if not general_path.exists():
        return None

    try:
        with open(general_path, "r") as f:
            data = json.load(f)
        return data.get("default_agent")
    except Exception as e:
        logger.error(f"Failed to load default agent: {e}")
        return None

def save_default_agent(agent_name: str) -> bool:
    """Save the default agent name to general.json

    Args:
        agent_name: Name of the default agent

    Returns:
        True if successful, False otherwise
    """
    general_path = Path("agents") / "general.json"

    try:
        data = {"default_agent": agent_name}

        # Create the directory if it doesn't exist
        general_path.parent.mkdir(exist_ok=True)

        with open(general_path, "w") as f:
            json.dump(data, f, indent=2)

        return True
    except Exception as e:
        logger.error(f"Failed to save default agent: {e}")
        return False