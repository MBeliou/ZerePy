from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import logging

from src.matriarch.models.server_state import ServerState
from src.matriarch.routers import agents

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("server/server")

app = FastAPI(title="Matriarch")
app.add_middleware(CORSMiddleware,
                   allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.state.server_state = ServerState()

app.include_router(agents.router, prefix="/agents", tags=["agents"])
