from fastapi import Request
from src.matriarch.models.server_state import ServerState

def get_server_state(request: Request) -> ServerState:
    return request.app.state.server_state