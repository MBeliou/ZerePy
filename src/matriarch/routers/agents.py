from fastapi import APIRouter, Depends, HTTPException
import logging

from src.matriarch.dependencies.dependencies import get_server_state
from src.matriarch.models.server_state import ServerState, AgentConfig
from src.server.app import ActionRequest

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("matriarch/agents")

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


# Lifecycle

@router.post("/{agent_name}/start")
async def start_agent(agent_name: str, server_state: ServerState = Depends(get_server_state)):
    logger.info(f"Received start request for agent: {agent_name}")

    if server_state.get_agent(agent_id=agent_name):
        logger.info(f"Found agent configuration for {agent_name}")

        success = await server_state.start_agent(agent_name)
        if success:
            logger.info(f"Successfully started agent {agent_name}")
            return {"status": "success"}
        else:
            logger.error(f"Failed to start agent {agent_name}")
            raise HTTPException(status_code=500, detail="Couldn't start agent")
    else:
        logger.error(f"No agent found with name {agent_name}")
        raise HTTPException(status_code=404, detail="Couldn't find agent")


@router.post("/{agent_name}/stop")
async def stop_agent(agent_name: str, server_state: ServerState = Depends(get_server_state)):
    if server_state.get_agent(agent_name) is None:
        raise HTTPException(status_code=404, detail=f"Couldn't find agent {agent_name}")
    success = await server_state.stop_agent(agent_name)

    if success:
        return {
            "status": "success"
        }
    else:
        raise HTTPException(status_code=500, detail=f"Couldn't stop agent {agent_name}")


# Actions
@router.post("/{agent_name}/action")
async def request_action(agent_name: str, action_request: ActionRequest, server_state: ServerState = Depends(get_server_state)):
    if server_state.get_agent(agent_name) is None:
        raise HTTPException(status_code=404, detail=f"Couldn't find agent {agent_name}")

    response = await server_state.request_action(agent_name, action_request)
    return  {
        "status": "success",
        "response": response
    }