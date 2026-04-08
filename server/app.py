
"""FastAPI application for the Devops Env Environment."""

try:
    from openenv.core.env_server.http_server import create_app
except Exception as e:
    raise ImportError("openenv is required for the web interface.") from e

try:
    from ..models import DevOpsAction, DevOpsObservation
    from .devops_env_environment import DevOpsEnvironment
except ImportError:
    from models import DevOpsAction, DevOpsObservation
    from server.devops_env_environment import DevOpsEnvironment

app = create_app(
    DevOpsEnvironment,
    DevOpsAction,
    DevOpsObservation,
    env_name="devops_env",
    max_concurrent_envs=1,
)

def main(host: str = "0.0.0.0", port: int = 8000):
    """Entry point for direct execution."""
    import uvicorn
    uvicorn.run(app, host=host, port=port)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    main(port=args.port)