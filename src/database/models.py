from typing import List, Optional, Dict, Any, TYPE_CHECKING
from sqlmodel import Field, SQLModel, Relationship, Column, JSON
import json
from datetime import datetime

if TYPE_CHECKING:
    from typing import ForwardRef

    Agent = ForwardRef("Agent")


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


class Task(SQLModel, table=True):
    """Task model for database storage"""
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    weight: float = 1.0
    agent_id: Optional[int] = Field(default=None, foreign_key="agent.id")

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
    agent_id: Optional[int] = Field(default=None, foreign_key="agent.id")

    # Discriminator column for polymorphic inheritance
    config_type: str = Field(default="base")

    __mapper_args__ = {"polymorphic_on": "config_type", "polymorphic_identity": "base"}

    def to_config_dict(self) -> Dict[str, Any]:
        """Convert the config to a dictionary"""
        return {
            "name": self.name
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConfigBase":
        """Create a config from a dictionary"""
        return cls(**data)

    class Config:
        arbitrary_types_allowed = True


class Agent(AgentBase, table=True):
    """Agent model for database storage"""
    id: Optional[int] = Field(default=None, primary_key=True)

    # Explicitly define relationships with back_populates to avoid circular references
    configs: List["ConfigBase"] = Relationship(sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    tasks: List["Task"] = Relationship(sa_relationship_kwargs={"cascade": "all, delete-orphan"})

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

        # Create configs
        for config_data in configs_data:
            config_type = config_data.get("name")
            config = None

            if config_type == "twitter":
                config = TwitterConfig(**config_data)
            elif config_type == "openai":
                config = OpenAIConfig(**config_data)
            elif config_type == "anthropic":
                config = AnthropicConfig(**config_data)
            elif config_type == "discord":
                config = DiscordConfig(**config_data)
            elif config_type == "farcaster":
                config = FarcasterConfig(**config_data)
            elif config_type in ["solana", "ethereum", "sonic"]:
                config = NetworkConfig(**config_data)
            else:
                config = ConfigBase(**config_data)

            if config:
                agent.configs.append(config)

        # Create tasks
        for task_data in tasks_data:
            task = Task(**task_data)
            agent.tasks.append(task)

        return agent


# Update ConfigBase to reference Agent for the relationship
ConfigBase.agent = Relationship(back_populates="configs")
Task.agent = Relationship(back_populates="tasks")


# Define subclass configurations
class TwitterConfig(SQLModel, table=False):
    """Twitter configuration"""
    timeline_read_count: int = 10
    own_tweet_replies_count: int = 2
    tweet_interval: int = 5400

    def to_config_dict(self) -> Dict[str, Any]:
        """Convert the config to a dictionary"""
        return {
            "name": "twitter",
            "timeline_read_count": self.timeline_read_count,
            "own_tweet_replies_count": self.own_tweet_replies_count,
            "tweet_interval": self.tweet_interval
        }


class FarcasterConfig(SQLModel, table=False):
    """Farcaster configuration"""
    timeline_read_count: int = 10
    cast_interval: int = 60

    def to_config_dict(self) -> Dict[str, Any]:
        """Convert the config to a dictionary"""
        return {
            "name": "farcaster",
            "timeline_read_count": self.timeline_read_count,
            "cast_interval": self.cast_interval
        }


class OpenAIConfig(SQLModel, table=False):
    """OpenAI configuration"""
    model: str = "gpt-4o"

    def to_config_dict(self) -> Dict[str, Any]:
        """Convert the config to a dictionary"""
        return {
            "name": "openai",
            "model": self.model
        }


class AnthropicConfig(SQLModel, table=False):
    """Anthropic configuration"""
    model: str = "claude-3-5-sonnet-20241022"

    def to_config_dict(self) -> Dict[str, Any]:
        """Convert the config to a dictionary"""
        return {
            "name": "anthropic",
            "model": self.model
        }


class DiscordConfig(SQLModel, table=False):
    """Discord configuration"""
    message_read_count: int = 10
    message_emoji_name: str = "❤️"
    server_id: str = ""

    def to_config_dict(self) -> Dict[str, Any]:
        """Convert the config to a dictionary"""
        return {
            "name": "discord",
            "message_read_count": self.message_read_count,
            "message_emoji_name": self.message_emoji_name,
            "server_id": self.server_id
        }


class NetworkConfig(SQLModel, table=False):
    """Network configuration for blockchain connections"""
    network: Optional[str] = None
    rpc: Optional[str] = None

    def to_config_dict(self) -> Dict[str, Any]:
        """Convert the config to a dictionary"""
        result = {"name": "network"}
        if self.network:
            result["network"] = self.network
        if self.rpc:
            result["rpc"] = self.rpc
        return result

    """Twitter configuration"""
    timeline_read_count: int = 10
    own_tweet_replies_count: int = 2
    tweet_interval: int = 5400

    __mapper_args__ = {"polymorphic_identity": "twitter"}

    def to_config_dict(self) -> Dict[str, Any]:
        """Convert the config to a dictionary"""
        base_dict = super().to_config_dict()
        base_dict.update({
            "timeline_read_count": self.timeline_read_count,
            "own_tweet_replies_count": self.own_tweet_replies_count,
            "tweet_interval": self.tweet_interval
        })
        return base_dict


class Config:
    arbitrary_types_allowed = True
    loop_delay: int = 900
    use_time_based_weights: bool = False
    time_based_multipliers: str = Field(sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:

        """Convert the agent to a dictionary"""
        return {
            "name": self.name,
            "description": self.description,
            "bio": json.loads(self.bio),
            "traits": json.loads(self.traits),
            "examples": json.loads(self.examples),
            "example_accounts": json.loads(self.example_accounts),
            "loop_delay": self.loop_delay,
            "use_time_based_weights": self.use_time_based_weights,
            "time_based_multipliers": json.loads(self.time_based_multipliers),
            "config": [config.to_config_dict() for config in self.configs],
            "tasks": [task.to_dict() for task in self.tasks]
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Agent":

        """Create an agent from a dictionary"""
        # Extract configs and tasks to create separately
        configs_data = data.pop("config", [])
        tasks_data = data.pop("tasks", [])

        # Convert lists to JSON strings
        for field in ["bio", "traits", "examples", "example_accounts", "time_based_multipliers"]:
            if field in data and not isinstance(data[field], str):
                data[field] = json.dumps(data[field])

        agent = Agent(**data)

        # Create and link configs
        for config_data in configs_data:
            config_type = config_data.get("name")
            if config_type == "twitter":
                config = TwitterConfig.from_dict(config_data)
            elif config_type == "openai":
                config = OpenAIConfig.from_dict(config_data)
            elif config_type == "anthropic":
                config = AnthropicConfig.from_dict(config_data)
            elif config_type == "discord":
                config = DiscordConfig.from_dict(config_data)
            elif config_type in ["solana", "ethereum", "sonic"]:
                config = NetworkConfig.from_dict(config_data)
            elif config_type == "farcaster":
                config = FarcasterConfig.from_dict(config_data)
            else:
                config = ConfigBase.from_dict(config_data)

        config.agent_id = agent.id
        agent.configs.append(config)

        # Create and link tasks
        for task_data in tasks_data:
            task = Task.from_dict(task_data)
            task.agent_id = agent.id
            agent.tasks.append(task)

        return agent

