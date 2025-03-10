import uvicorn
import argparse
from pathlib import Path


def start_server(host: str = "0.0.0.0", port: int = 8000, reload: bool = False):
    """Start the ZerePy server

    Args:
        host: Host to bind to
        port: Port to listen on
        reload: Whether to enable auto-reload
    """
    # Ensure data directory exists
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)

    print(f"Starting ZerePy server on {host}:{port}")
    uvicorn.run(
        "src.matriarch.server:app",
        host=host,
        port=port,
        reload=reload
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ZerePy Server")
    parser.add_argument("--host", default="0.0.0.0", help="Server host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="Server port (default: 8000)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")

    args = parser.parse_args()
    start_server(args.host, args.port, args.reload)