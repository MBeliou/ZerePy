"""API schemas for FastAPI"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


# Task schemas
class TaskCreate(BaseModel):
    name: str
    weight: float = 1.0


class TaskResponse(TaskCreate):
    id: Optional[int] = None

    class Config:
        from_attributes = True


# Config schemas
class ConfigBase(BaseModel):
    name: str

    class Config:
        from_attributes = True


class TwitterConfigCreate(ConfigBase):
    timeline_read_count: int = 10
    own_tweet_replies_count: int = 2
    tweet_interval: int = 5400


class TwitterConfigResponse(TwitterConfigCreate):
    id: Optional[int] = None


class FarcasterConfigCreate(ConfigBase):
    timeline_read_count: int = 10
    cast_interval: int = 60


class FarcasterConfigResponse(FarcasterConfigCreate):
    id: Optional[int] = None


class OpenAIConfigCreate(ConfigBase):
    model: str = "gpt-4o"


class OpenAIConfigResponse(OpenAIConfigCreate):
    id: Optional[int] = None


class AnthropicConfigCreate(ConfigBase):
    model: str = "claude-3-5-sonnet-20241022"


class AnthropicConfigResponse(AnthropicConfigCreate):
    id: Optional[int] = None


class DiscordConfigCreate(ConfigBase):
    message_read_count: int = 10
    message_emoji_name: str = "❤️"
    server_id: str = ""


class DiscordConfigResponse(DiscordConfigCreate):
    id: Optional[int] = None


class NetworkConfigCreate(ConfigBase):
    network: Optional[str] = None
    rpc: Optional[str] = None


class NetworkConfigResponse(NetworkConfigCreate):
    id: Optional[int] = None


# Unified config type for responses
ConfigResponse = Dict[str, Any]


# Agent schemas
class TimeBasedMultipliers(BaseModel):
    tweet_night_multiplier: float = 0.4
    engagement_day_multiplier: float = 1.5


class AgentCreate(BaseModel):
    name: str
    description: Optional[str] = None
    bio: List[str]
    traits: List[str]
    examples: List[str] = []
    example_accounts: List[str] = []
    loop_delay: int = 900
    use_time_based_weights: bool = False
    time_based_multipliers: TimeBasedMultipliers = Field(default_factory=TimeBasedMultipliers)
    config: List[Dict[str, Any]] = []
    tasks: List[TaskCreate] = []


class AgentResponse(BaseModel):
    id: Optional[int] = None
    name: str
    description: Optional[str] = None
    bio: List[str]
    traits: List[str]
    examples: List[str]
    example_accounts: List[str]
    loop_delay: int
    use_time_based_weights: bool
    time_based_multipliers: Dict[str, float]
    config: List[ConfigResponse]
    tasks: List[Dict[str, Any]]
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class AgentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    bio: Optional[List[str]] = None
    traits: Optional[List[str]] = None
    examples: Optional[List[str]] = None
    example_accounts: Optional[List[str]] = None
    loop_delay: Optional[int] = None
    use_time_based_weights: Optional[bool] = None
    time_based_multipliers: Optional[Dict[str, float]] = None
    config: Optional[List[Dict[str, Any]]] = None
    tasks: Optional[List[Dict[str, Any]]] = None


# Action request schema
class ActionRequest(BaseModel):
    connection: str
    action: str
    params: List[Any] = []


class ActionParameter(BaseModel):
    name: str
    required: bool
    type: str
    description: str


class Action(BaseModel):
    name: str
    parameters: List[ActionParameter]
    description: str


class AgentActionsResponse(BaseModel):
    status: str
    response: Dict[str, Dict[str,  Action]]


# Status responses
class StatusResponse(BaseModel):
    status: str


class RunningStatusResponse(BaseModel):
    running: bool


class ActionResponse(BaseModel):
    status: str
    response: Any = None
