import uvicorn
from src.matriarch.server import app

def start_server(host: str = "0.0.0.0", port: int = 8000):
    """Start the ZerePy server"""
    uvicorn.run(app, host=host, port=port)

if __name__ == "__main__":
    start_server()