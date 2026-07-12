from datetime import datetime, timezone
from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", summary="Health check")
async def health_check():
    """Returns service health status. Used for load-balancer / uptime checks."""
    return {
        "status": "ok",
        "service": "qshield-backend",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "0.1.0",
    }
