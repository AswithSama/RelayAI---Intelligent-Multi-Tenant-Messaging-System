from fastapi import APIRouter

from app.api.routes import (
    company,
    conversations,
    customers,
    messages,
)


api_router = APIRouter(
    prefix="/api/v1",
)

api_router.include_router(company.router)
api_router.include_router(customers.router)
api_router.include_router(conversations.router)
api_router.include_router(messages.router)