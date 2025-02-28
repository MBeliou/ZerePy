from fastapi import APIRouter, Depends, HTTPException, status
import logging
from typing import Dict, List, Any, Optional

from src.matriarch.dependencies.dependencies import get_server_state
from src.matriarch.models.updated_server_state import ServerState
from src.matriarch.schemas import AgentResponse, AgentCreate, AgentUpdate, ActionRequest, StatusResponse, \
    RunningStatusResponse, ActionResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("matriarch/agents")

router = APIRouter()


@router.get("/", response_model=List[AgentResponse])
async def get_agents(server_state: ServerState = Depends(get_server_state)):
    """Get all agents"""
    return server_state.get_all_agents()


@router.get("/{agent_name}", response_model=AgentResponse)
async def get_agent(
        agent_name: str,
        server_state: ServerState = Depends(get_server_state)
):
    """Get agent by name"""
    agent = server_state.get_agent(agent_name)
    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_name} not found"
        )
    return agent


@router.post("/", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
        agent_data: AgentCreate,
        server_state: ServerState = Depends(get_server_state)
):
    """Create a new agent"""
    # Check if agent already exists
    existing_agent = server_state.get_agent(agent_data.name)
    if existing_agent:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Agent {agent_data.name} already exists"
        )

    try:
        new_agent = server_state.add_agent(agent_data.dict())
        return new_agent
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create agent: {str(e)}"
        )


@router.put("/{agent_name}", response_model=AgentResponse)
async def update_agent(
        agent_name: str,
        agent_data: AgentUpdate,
        server_state: ServerState = Depends(get_server_state)
):
    """Update an existing agent"""
    # Check if agent exists
    if not server_state.get_agent(agent_name):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_name} not found"
        )

    try:
        updated_agent = server_state.update_agent(agent_name, agent_data.dict(exclude_unset=True))
        if updated_agent:
            return updated_agent
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update agent {agent_name}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update agent: {str(e)}"
        )


@router.delete("/{agent_name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(
        agent_name: str,
        server_state: ServerState = Depends(get_server_state)
):
    """Delete an agent"""
    # First try to stop the agent if it's running
    try:
        await server_state.stop_agent(agent_name)
    except Exception as e:
        logger.error(f"Failed to stop agent {agent_name}: {e}")

    # Then delete it from the database
    if not server_state.delete_agent(agent_name):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_name} not found"
        )

    return


# Lifecycle endpoints

@router.post("/{agent_name}/start", response_model=StatusResponse)
async def start_agent(
        agent_name: str,
        server_state: ServerState = Depends(get_server_state)
):
    """Start an agent"""
    logger.info(f"Received start request for agent: {agent_name}")

    # Check if agent exists
    if not server_state.get_agent(agent_name):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_name} not found"
        )

    success = await server_state.start_agent(agent_name)
    if success:
        logger.info(f"Successfully started agent {agent_name}")
        return {"status": "success"}
    else:
        logger.error(f"Failed to start agent {agent_name}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start agent"
        )


@router.post("/{agent_name}/stop", response_model=StatusResponse)
async def stop_agent(
        agent_name: str,
        server_state: ServerState = Depends(get_server_state)
):
    """Stop a running agent"""
    if not server_state.get_agent(agent_name):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_name} not found"
        )

    success = await server_state.stop_agent(agent_name)
    if success:
        return {"status": "success"}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop agent {agent_name}"
        )


@router.get("/{agent_name}/actions")
async def get_actions(
        agent_name: str,
        server_state: ServerState = Depends(get_server_state)
):
    if not server_state.get_agent(agent_name):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_name} not found"
        )
    if not server_state.is_agent_running(agent_name):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Agent {agent_name} is not running"
        )
    response = server_state.get_agent_actions(agent_name)
    return {
        "status": "success",
        "response": response
    }


@router.post("/{agent_name}/action", response_model=ActionResponse)
async def request_action(
        agent_name: str,
        action_request: ActionRequest,
        server_state: ServerState = Depends(get_server_state)
):
    """Request an action from an agent"""
    if not server_state.get_agent(agent_name):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_name} not found"
        )

    try:
        response = await server_state.request_action(agent_name, action_request)
        return {
            "status": "success",
            "response": response
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute action: {str(e)}"
        )


@router.get("/{agent_name}/status", response_model=RunningStatusResponse)
async def get_agent_status(
        agent_name: str,
        server_state: ServerState = Depends(get_server_state)
):
    """Get agent running status"""
    if not server_state.get_agent(agent_name):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_name} not found"
        )

    # safe_name = server_state._make_safe_agent_name(agent_name)
    agent_loop = server_state.agent_loops.get(agent_name)

    if agent_loop:
        is_running = await agent_loop.is_running()
        return {"running": is_running}

    return {"running": False}
