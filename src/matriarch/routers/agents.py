from fastapi import APIRouter, Depends, HTTPException

from src.matriarch.dependencies.dependencies import get_server_state
from src.matriarch.models.server_state import ServerState, AgentConfig

router = APIRouter()


@router.get("/")
async def get_agents(server_state: ServerState = Depends(get_server_state)):
    return server_state.get_all_agents()


@router.get("/{agent_name}")
async def get_agent(
        agent_name: str,
        server_state: ServerState = Depends(get_server_state)
):
    print(agent_name)
    agent = server_state.get_agent(agent_name)
    if agent is None:
        return {"error": f"Agent {agent_name} not found"}
    return agent


@router.post("/")
async def create_agent(
        agent: AgentConfig,
        server_state: ServerState = Depends(get_server_state)
):
    if server_state.get_agent(agent.name):
        raise HTTPException(status_code=400, detail="Agent already exists")
    server_state.add_agent(agent)
    return agent


@router.post("/{agent_name}/configure")
async def configure_agent():
    raise HTTPException(status_code=501, detail="Can't configure agents yet")


# Actions

@router.post("/{agent_name}/start")
async def start_agent(agent_name: str, server_state: ServerState = Depends(get_server_state)):
    if server_state.get_agent(agent_id=agent_name):
        success = server_state.start_agent(agent_name)
        if success:
            return {"status": "success"}
        else:
            raise HTTPException(status_code=500, detail="Couldn't start agent")
    else:
        raise HTTPException(status_code=404, detail="Couldn't find agent")


@router.post("/{agent_name}/stop")
async def stop_agent(agent_name: str, server_state: ServerState = Depends(get_server_state)):
    raise HTTPException(status_code=501, detail="Can't start agents yet")
