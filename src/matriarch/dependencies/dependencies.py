from fastapi import Request
from src.matriarch.models.server_state import ServerState

def get_server_state(request: Request) -> ServerState:
    """Dependency to get the server state from the request"""
    return request.app.state.server_state