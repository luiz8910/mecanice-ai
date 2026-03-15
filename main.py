"""Application entrypoint.

Imports the FastAPI app from the hexagonal architecture (src/bot).
Run with: uvicorn main:app --reload --port 9000
"""

from src.bot.adapters.driver.fastapi.app_factory import app  # noqa: F401
