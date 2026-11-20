from fastapi import APIRouter, Request

router = APIRouter(tags=["health"])


@router.get("/healthz")
def healthz() -> dict[str, str]:
    """Liveness probe used by the load balancer and the deploy pipeline."""
    return {"status": "ok"}


@router.get("/readyz")
def readyz(request: Request) -> dict:
    """Readiness: is the size graph loaded, and from where."""
    state = request.app.state
    store = getattr(state, "store", None)
    return {
        "status": "ready" if store is not None else "not_ready",
        "store_source": getattr(state, "store_source", None),
        "data_version": store.version if store else None,
        "brands": len(store.brands) if store else 0,
        "chart_rows": store.row_count if store else 0,
        "db_error": getattr(state, "db_error", None),
    }
