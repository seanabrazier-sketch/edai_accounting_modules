"""
EDai Location Intelligence API — src/api package

The FastAPI app is only imported on-demand so that orchestrator / schemas
work in environments without FastAPI installed (e.g. integration tests).
"""


def get_app():
    """Return the FastAPI app instance (requires FastAPI + uvicorn)."""
    from .main import app  # noqa: PLC0415
    return app


__all__ = ["get_app"]
