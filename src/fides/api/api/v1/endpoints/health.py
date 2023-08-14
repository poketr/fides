from typing import Dict, List, Literal, Optional

from fastapi import HTTPException, status
from loguru import logger
from pydantic import BaseModel
from redis.exceptions import ResponseError

import fides
from fides.api.common_exceptions import RedisConnectionError
from fides.api.db.database import DatabaseHealth, get_db_health
from fides.api.util.api_router import APIRouter
from fides.api.util.cache import get_cache
from fides.api.util.logger import Pii
from fides.config import CONFIG

CacheHealth = Literal["healthy", "unhealthy", "no cache configured"]
HEALTH_ROUTER = APIRouter(tags=["Health"])


class CoreHealthCheck(BaseModel):
    """Healthcheck schema"""

    webserver: str
    version: str
    database: DatabaseHealth
    cache: CacheHealth
    workers_enabled: bool
    workers: List[Optional[str]]


def get_cache_health() -> str:
    """Checks if the cache is reachable"""

    if not CONFIG.redis.enabled:
        return "no cache configured"
    try:
        get_cache()
        return "healthy"
    except (RedisConnectionError, ResponseError) as e:
        logger.error("Unable to reach cache: {}", Pii(str(e)))
        return "unhealthy"


@HEALTH_ROUTER.get(
    "/health",
    response_model=CoreHealthCheck,
    responses={
        status.HTTP_200_OK: {
            "content": {
                "application/json": {
                    "example": {
                        "webserver": "healthy",
                        "version": "1.0.0",
                        "database": "healthy",
                        "cache": "healthy",
                        "workers_enabled": "True",
                        "workers": ["celery@c606808353b5"],
                    }
                }
            }
        },
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "content": {
                "application/json": {
                    "example": {
                        "detail": {
                            "webserver": "healthy",
                            "version": "1.0.0",
                            "database": "unhealthy",
                            "cache": "healthy",
                            "workers_enabled": "True",
                            "workers": ["celery@c606808353b5"],
                        }
                    }
                }
            }
        },
    },
)
async def health() -> Dict:
    """Confirm that the API is running and healthy."""
    database_health = get_db_health(CONFIG.database.sync_database_uri)
    cache_health = get_cache_health()
    response = CoreHealthCheck(
        webserver="healthy",
        version=str(fides.__version__),
        database=database_health,
        cache=cache_health,
        workers_enabled=False,
        workers=[],
    ).dict()

    for _, value in response.items():
        if value == "unhealthy":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=response
            )

    return response
