from fastapi import APIRouter

from app.api import articles, auth, authors, health, me, tags

API_PREFIX = "/api/v1"

api_router = APIRouter(prefix=API_PREFIX)
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(me.router)
api_router.include_router(authors.router)
api_router.include_router(articles.router)
api_router.include_router(tags.router)
