from fastapi import APIRouter, Depends, HTTPException

from src.matriarch.dependencies.dependencies import get_server_state
from src.matriarch.models.server_state import ServerState, AgentConfig

router = APIRouter()


@router.get("/")
async def get_agents(server_state: ServerState = Depends(get_server_state)):
    return server_state.get_all_agents()


@router.get("/{agent_id}")
async def get_agent(
        agent_id: str,
        server_state: ServerState = Depends(get_server_state)
):
    agent = server_state.get_agent(agent_id)
    if agent is None:
        return {"error": "Agent not found"}
    return agent


@router.post("/")
async def create_agent(
        agent: AgentConfig,
        server_state: ServerState = Depends(get_server_state)
):
    server_state.add_agent(agent)
    return agent

@router.post("/{agent_id}/configure")
async def configure_agent():
    raise HTTPException(status_code=501, detail="Can't configure agents yet")


# Actions

@router.post("/{agent_id}/start")
async def start_agent():
    raise HTTPException(status_code=501, detail="Can't start agents yet")



@router.post("/{agent_id}/stop")
async def start_agent():
    raise HTTPException(status_code=501, detail="Can't stop agents yet")