import logging
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

from src.matriarch.models.server_state import ServerState
from src.matriarch.routers import agents as agents

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("server/server")


def get_server_state():
    """Dependency to get server state"""
    return app.state.server_state


def create_app() -> FastAPI:
    """Create and configure the FastAPI application"""
    app = FastAPI(
        title="ZerePy Server",
        description="API for managing AI agents",
        version="0.2.0"
    )

    @app.get("/robots.txt", response_class=PlainTextResponse)
    async def get_robots_txt():
        return """User-agent: *
Allow: /"""

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"]
    )

    # Initialize database
    logger.info("Setting up database...")
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)

    # Create server state
    logger.info("Initializing server state...")
    app.state.server_state = ServerState()

    # Register dependencies
    app.dependency_overrides[agents.get_server_state] = get_server_state

    # Include routers
    app.include_router(agents.router, prefix="/agents", tags=["agents"])

    return app


# Create the application
app = create_app()


@app.get("/", tags=["status"])
async def root():
    """Get server status"""
    return {
        "status": "running",
        "version": app.version,
        "title": app.title
    }


@app.get("/health", tags=["status"])
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.matriarch.server:app", host="0.0.0.0", port=8000, reload=True)