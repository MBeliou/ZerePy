from fastapi import FastAPI
import logging

from src.matriarch.models.server_state import ServerState
from src.matriarch.routers import agents

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("server/server")

app = FastAPI(title="Matriarch")
app.state.server_state = ServerState()

app.include_router(agents.router, prefix="/agents", tags=["agents"])
