from fastapi import FastAPI

from agentrooms.api.routers import health, messages, rooms

app = FastAPI(title="Agent Rooms", version="0.1.0")

app.include_router(health.router)
app.include_router(rooms.router)
app.include_router(messages.router)
