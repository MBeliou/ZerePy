from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any, Union, Tuple


class NetworkConfig(BaseModel):
    name: str
    network: Optional[str] = None
    rpc: Optional[str] = None
    private_key: str

    class Config:
        frozen = True


class DiscordConfig(BaseModel):
    name: str = "discord"
    message_read_count: int
    message_emoji_name: str
    server_id: str

    class Config:
        frozen = True


class TwitterConfig(BaseModel):
    name: str
    timeline_read_count: int
    own_tweet_replies_count: int
    tweet_interval: int

    class Config:
        frozen = True


ConfigItem = DiscordConfig | TwitterConfig | NetworkConfig


class TaskConfig(BaseModel):
    name: str
    weight: float

    class Config:
        frozen = True


class TimeBasedMultipliers(BaseModel):
    tweet_night_multiplier: float
    engagement_day_multiplier: float

    class Config:
        frozen = True



class AgentConfig(BaseModel):
    name: str
    bio: Optional[Tuple[str,...]] = None
    traits: Optional[Tuple[str,...]] = None
    examples: Optional[Tuple[str,...]] = None
    example_accounts: Optional[Tuple[str,...]] = None
    loop_delay: Optional[int] = None
    config: Optional[Tuple["ConfigItem",...]] = None
    tasks: Optional[Tuple["TaskConfig",...]] = None
    use_time_based_weights: Optional[bool] = None

    time_based_multipliers: Optional["TimeBasedMultipliers"] = None

    class Config:
        frozen = True


class ListAgentConfig(BaseModel):
    name: str
    bio: Optional[List[str]] = None
    traits: Optional[List[str]] = None
    examples: Optional[List[str]] = None
    example_accounts: Optional[List[str]] = None
    loop_delay: Optional[int] = None
    config: Optional[List["ConfigItem"]] = None
    tasks: Optional[List["TaskConfig"]] = None
    use_time_based_weights: Optional[bool] = None

    time_based_multipliers: Optional["TimeBasedMultipliers"] = None

    class Config:
        frozen = True


class SafeAgentConfig(BaseModel):
    """Returns an Agent Config that is safe for outside consumption and removes mentions of private keys"""
    name: str
    bio: List[str]
    traits: List[str]
    examples: List[str]
    example_accounts: List[str]
    loop_delay: int
    config: List[Dict]  # Will contain NetworkConfigResponse or DiscordConfig
    tasks: List["TaskConfig"]
    use_time_based_weights: bool
    time_based_multipliers: TimeBasedMultipliers

    class Config:
        frozen = True

    @classmethod
    def from_internal(cls, internal: AgentConfig) -> 'SafeAgentConfig':
        # Deep copy the internal config
        data = internal.model_dump()

        # FIXME: We'll most likely want to have a more general approach to private fields. Either allow marking every config value as private or prefix with _ keys we shouldn't be passing out
        sanitized_config = []

        # Surely only config will contain sensitive info, right?
        for cfg in data['config']:
            if cfg.get('name') in ['sonic', 'ethereum']:  # blockchain configs
                sanitized_cfg = {
                    'name': cfg['name'],
                    'network': cfg.get('network'),
                    'rpc': cfg.get('rpc')
                }
                sanitized_config.append(sanitized_cfg)
            else:
                sanitized_config.append(
                    cfg)  # NOTE: We're not doing anything special with non-blockchain configs for now

        data['config'] = sanitized_config
        return cls(**data)


class AgentUpdate(BaseModel):
    bio: Optional[List[str]] = None
    traits: Optional[List[str]] = None
    examples: Optional[List[str]] = None
    example_accounts: Optional[List[str]] = None
    loop_delay: Optional[int] = None
    config: Optional[List[Dict]] = None
    tasks: Optional[List[TaskConfig]] = None
    use_time_based_weights: Optional[bool] = None
    time_based_multipliers: Optional[TimeBasedMultipliers] = None

    class Config:
        frozen = True
