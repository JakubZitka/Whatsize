from typing import Annotated

from fastapi import Depends, HTTPException, Request

from app.engine.store import ChartStore


def get_store(request: Request) -> ChartStore:
    store = getattr(request.app.state, "store", None)
    if store is None:
        raise HTTPException(status_code=503,
                            detail="Data o velikostech nejsou dostupná. Zkus to za chvíli.")
    return store


Store = Annotated[ChartStore, Depends(get_store)]
