from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/healthz")
def healthz() -> dict[str, str]:
    """Liveness probe used by the load balancer and the deploy pipeline."""
    return {"status": "ok"}
