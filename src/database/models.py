from typing import List, Optional, Dict, Any, TYPE_CHECKING
from sqlmodel import Field, SQLModel, Relationship, Column, JSON
import json
from datetime import datetime


class AgentBase(SQLModel):
    """Base model for Agent"""
    name: str = Field(index=True)
    description: Optional[str] = None
    bio: str = Field(sa_column=Column(JSON))
    traits: str = Field(sa_column=Column(JSON))
    examples: str = Field(sa_column=Column(JSON))
    example_accounts: str = Field(sa_column=Column(JSON))
    loop_delay: int = 900
    use_time_based_weights: bool = False
    time_based_multipliers: str = Field(sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert the agent to a dictionary"""
        return {
            "id": self.id if hasattr(self, "id") else None,
            "name": self.name,
            "description": self.description,
            "bio": json.loads(self.bio),
            "traits": json.loads(self.traits),
            "examples": json.loads(self.examples),
            "example_accounts": json.loads(self.example_accounts),
            "loop_delay": self.loop_delay,
            "use_time_based_weights": self.use_time_based_weights,
            "time_based_multipliers": json.loads(self.time_based_multipliers),
            "config": [config.to_config_dict() for config in self.configs] if hasattr(self, "configs") else [],
            "tasks": [task.to_dict() for task in self.tasks] if hasattr(self, "tasks") else [],
            "created_at": self.created_at.isoformat() if hasattr(self, "created_at") else None,
            "updated_at": self.updated_at.isoformat() if hasattr(self, "updated_at") else None
        }


class Agent(AgentBase, table=True):
    """Agent model for database storage"""
    id: Optional[int] = Field(default=None, primary_key=True)

    # Explicitly define relationships with back_populates to avoid circular references
    configs: List["ConfigBase"] = Relationship(back_populates="agent",
                                               sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    tasks: List["Task"] = Relationship(back_populates="agent",
                                       sa_relationship_kwargs={"cascade": "all, delete-orphan"})

    class Config:
        arbitrary_types_allowed = True

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Agent":
        """Create an agent from a dictionary"""
        # Make a copy of the data to avoid modifying the original
        agent_data = data.copy()

        # Extract configs and tasks to create separately
        configs_data = agent_data.pop("config", [])
        tasks_data = agent_data.pop("tasks", [])

        # Convert lists to JSON strings
        for field in ["bio", "traits", "examples", "example_accounts", "time_based_multipliers"]:
            if field in agent_data and not isinstance(agent_data[field], str):
                agent_data[field] = json.dumps(agent_data[field])

        # Create the agent
        agent = Agent(**agent_data)

        # We'll handle configs and tasks after agent is saved to DB
        return agent


class Task(SQLModel, table=True):
    """Task model for database storage"""
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    weight: float = 1.0
    agent_id: Optional[int] = Field(default=None, foreign_key="agent.id")
    agent: Optional["Agent"] = Relationship(back_populates="tasks")

    def to_dict(self) -> Dict[str, Any]:
        """Convert the task to a dictionary"""
        return {
            "name": self.name,
            "weight": self.weight
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Task":
        """Create a task from a dictionary"""
        return cls(**data)

    class Config:
        arbitrary_types_allowed = True


class ConfigBase(SQLModel, table=True):
    """Base model for all configurations"""
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    agent_id: int = Field(foreign_key="agent.id")
    agent: Optional["Agent"] = Relationship(back_populates="configs")

    # JSON field to store all subclass-specific attributes
    attributes: str = Field(default="{}", sa_column=Column(JSON))

    # Discriminator column for polymorphic inheritance
    config_type: str = Field(default="base")

    def to_config_dict(self) -> Dict[str, Any]:
        """Convert the config to a dictionary"""
        # Base dictionary with common fields
        result = {
            "name": self.name,
            "config_type": self.config_type
        }

        # Add attributes from the JSON field
        if hasattr(self, "attributes") and self.attributes:
            try:
                attributes = json.loads(self.attributes)
                result.update(attributes)
            except (json.JSONDecodeError, TypeError):
                pass

        return result

    @staticmethod
    def from_dict(data: Dict[str, Any], agent_id: Optional[int] = None) -> "ConfigBase":
        """Create a config from a dictionary"""
        config_data = data.copy()

        # Set the agent_id if provided
        if agent_id is not None:
            config_data["agent_id"] = agent_id

        # Extract name and config_type
        name = config_data.pop("name", "base")
        config_type = name  # Use name as config_type

        # Create a new instance of the appropriate config class
        if name == "twitter":
            return TwitterConfig.create_from_dict(config_data, agent_id)
        elif name == "openai":
            return OpenAIConfig.create_from_dict(config_data, agent_id)
        elif name == "anthropic":
            return AnthropicConfig.create_from_dict(config_data, agent_id)
        elif name == "discord":
            return DiscordConfig.create_from_dict(config_data, agent_id)
        elif name == "farcaster":
            return FarcasterConfig.create_from_dict(config_data, agent_id)
        elif name in ["solana", "ethereum", "sonic"]:
            return NetworkConfig.create_from_dict(config_data, agent_id)
        else:
            # For base config, just set attributes as JSON
            config = ConfigBase(
                name=name,
                config_type=config_type,
                agent_id=agent_id,
                attributes=json.dumps(config_data)
            )
            return config

    class Config:
        arbitrary_types_allowed = True


# Define specific configuration classes
class TwitterConfig:
    """Twitter configuration"""

    @staticmethod
    def create_from_dict(data: Dict[str, Any], agent_id: Optional[int] = None) -> ConfigBase:
        """Create a TwitterConfig from a dictionary and convert to ConfigBase"""
        attributes = {
            "timeline_read_count": data.get("timeline_read_count", 10),
            "own_tweet_replies_count": data.get("own_tweet_replies_count", 2),
            "tweet_interval": data.get("tweet_interval", 5400)
        }

        return ConfigBase(
            name="twitter",
            config_type="twitter",
            agent_id=agent_id,
            attributes=json.dumps(attributes)
        )

    def to_config_dict(self) -> Dict[str, Any]:
        """Convert the config to a dictionary"""
        attributes = json.loads(self.attributes)
        return {
            "name": "twitter",
            "timeline_read_count": attributes.get("timeline_read_count", 10),
            "own_tweet_replies_count": attributes.get("own_tweet_replies_count", 2),
            "tweet_interval": attributes.get("tweet_interval", 5400)
        }


class FarcasterConfig:
    """Farcaster configuration"""

    @staticmethod
    def create_from_dict(data: Dict[str, Any], agent_id: Optional[int] = None) -> ConfigBase:
        """Create a FarcasterConfig from a dictionary and convert to ConfigBase"""
        attributes = {
            "timeline_read_count": data.get("timeline_read_count", 10),
            "cast_interval": data.get("cast_interval", 60)
        }

        return ConfigBase(
            name="farcaster",
            config_type="farcaster",
            agent_id=agent_id,
            attributes=json.dumps(attributes)
        )

    def to_config_dict(self) -> Dict[str, Any]:
        """Convert the config to a dictionary"""
        attributes = json.loads(self.attributes)
        return {
            "name": "farcaster",
            "timeline_read_count": attributes.get("timeline_read_count", 10),
            "cast_interval": attributes.get("cast_interval", 60)
        }


class OpenAIConfig:
    """OpenAI configuration"""

    @staticmethod
    def create_from_dict(data: Dict[str, Any], agent_id: Optional[int] = None) -> ConfigBase:
        """Create an OpenAIConfig from a dictionary and convert to ConfigBase"""
        attributes = {
            "model": data.get("model", "gpt-4o")
        }

        return ConfigBase(
            name="openai",
            config_type="openai",
            agent_id=agent_id,
            attributes=json.dumps(attributes)
        )

    def to_config_dict(self) -> Dict[str, Any]:
        """Convert the config to a dictionary"""
        attributes = json.loads(self.attributes)
        return {
            "name": "openai",
            "model": attributes.get("model", "gpt-4o")
        }


class AnthropicConfig:
    """Anthropic configuration"""

    @staticmethod
    def create_from_dict(data: Dict[str, Any], agent_id: Optional[int] = None) -> ConfigBase:
        """Create an AnthropicConfig from a dictionary and convert to ConfigBase"""
        attributes = {
            "model": data.get("model", "claude-3-5-sonnet-20241022")
        }

        return ConfigBase(
            name="anthropic",
            config_type="anthropic",
            agent_id=agent_id,
            attributes=json.dumps(attributes)
        )

    def to_config_dict(self) -> Dict[str, Any]:
        """Convert the config to a dictionary"""
        attributes = json.loads(self.attributes)
        return {
            "name": "anthropic",
            "model": attributes.get("model", "claude-3-5-sonnet-20241022")
        }


class DiscordConfig:
    """Discord configuration"""

    @staticmethod
    def create_from_dict(data: Dict[str, Any], agent_id: Optional[int] = None) -> ConfigBase:
        """Create a DiscordConfig from a dictionary and convert to ConfigBase"""
        attributes = {
            "message_read_count": data.get("message_read_count", 10),
            "message_emoji_name": data.get("message_emoji_name", "❤️"),
            "server_id": data.get("server_id", "")
        }

        return ConfigBase(
            name="discord",
            config_type="discord",
            agent_id=agent_id,
            attributes=json.dumps(attributes)
        )

    def to_config_dict(self) -> Dict[str, Any]:
        """Convert the config to a dictionary"""
        attributes = json.loads(self.attributes)
        return {
            "name": "discord",
            "message_read_count": attributes.get("message_read_count", 10),
            "message_emoji_name": attributes.get("message_emoji_name", "❤️"),
            "server_id": attributes.get("server_id", "")
        }


class NetworkConfig:
    """Network configuration for blockchain connections"""

    @staticmethod
    def create_from_dict(data: Dict[str, Any], agent_id: Optional[int] = None) -> ConfigBase:
        """Create a NetworkConfig from a dictionary and convert to ConfigBase"""
        attributes = {
            "network": data.get("network"),
            "rpc": data.get("rpc"),
            "private_key": data.get("private_key")
        }

        return ConfigBase(
            name=data.get("network", "network"),
            config_type="network",
            agent_id=agent_id,
            attributes=json.dumps(attributes)
        )

    def to_config_dict(self) -> Dict[str, Any]:
        """Convert the config to a dictionary"""
        attributes = json.loads(self.attributes)
        result = {"name": self.name}
        if attributes.get("network"):
            result["network"] = attributes["network"]
        if attributes.get("rpc"):
            result["rpc"] = attributes["rpc"]
        if attributes.get("private_key"):
            result["private_key"] = attributes["private_key"]
        return result