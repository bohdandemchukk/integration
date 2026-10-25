import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import Literal

import httpx
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from . import crud, models, schemas        
from app.auth import get_current_user             
from app.database import Base, engine, get_db
from app.routers import auth as auth_router 

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

logger = logging.getLogger("orders-api")

FORECAST_URL = os.getenv(
    "FORECAST_URL",
    "http://forecast-api:8001",
)

# `or` handles both an unset and an empty variable (Compose passes "" if unset).
FORECAST_TIMEOUT = float(os.getenv("FORECAST_TIMEOUT") or "3.0")

PROPERTY_FIELDS = {
    "gr_liv_area", "total_bsmt_sf", "garage_area",
    "year_built", "overall_qual", "ms_zoning",
}
FORECAST_FIELDS = ["client_name", *sorted(PROPERTY_FIELDS)]

# Tables are created automatically for the initial version.
# In production, replace this with Alembic migrations.
Base.metadata.create_all(bind=engine)

client: httpx.AsyncClient | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create one shared HTTP client for the app lifetime."""
    global client
    client = httpx.AsyncClient(
        timeout=httpx.Timeout(FORECAST_TIMEOUT, connect=2.0),
    )
    yield
    await client.aclose()


app = FastAPI(
    title="Orders API",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(auth_router.router)        

auth_required = [Depends(get_current_user)]


async def get_prediction(
    payload: dict,
) -> tuple[float | None, Literal["ok", "failed"]]:
    """Request a price prediction. Never raises.

    The whole call (DNS, connect, response) is bounded by a hard overall
    deadline of FORECAST_TIMEOUT. No retries.
    """
    try:
        async with asyncio.timeout(FORECAST_TIMEOUT):
            resp = await client.post(
                f"{FORECAST_URL}/predict",
                json=payload,
            )
            resp.raise_for_status()
            return float(resp.json()["predicted_price"]), "ok"
    except (
        asyncio.TimeoutError,
        httpx.HTTPError,
        KeyError,
        ValueError,
        TypeError,
    ) as exc:
        logger.warning("Forecast failed: %r", exc)
        return None, "failed"


@app.get("/health")
def health() -> dict[str, str]:
    """Return the health status of the Orders API."""
    return {"status": "ok"}


@app.post(
    "/orders",
    response_model=schemas.OrderRead,
    status_code=201,
    dependencies=auth_required,
)

async def create_order(
    data: schemas.OrderCreate,
    db: Session = Depends(get_db),
):
    """Create an order and attempt to obtain a price prediction.

    The order is persisted regardless of the forecast outcome. The prediction
    happens before, and independently of, the INSERT transaction.
    """
    price, status = await get_prediction(data.model_dump())

    return await run_in_threadpool(
        crud.create_order,
        db,
        data,
        price,
        status,
    )


@app.get(
    "/orders",
    response_model=list[schemas.OrderRead],
    dependencies=auth_required
)

def list_orders(
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """Return a paginated list of orders."""
    if limit < 1 or limit > 100:
        raise HTTPException(
            status_code=400,
            detail="Limit must be between 1 and 100.",
        )

    if offset < 0:
        raise HTTPException(
            status_code=400,
            detail="Offset must be non-negative.",
        )

    return crud.list_orders(
        db,
        limit,
        offset,
    )


@app.get(
    "/orders/{oid}",
    response_model=schemas.OrderRead,
    dependencies=auth_required,
)
def get_order(
    oid: int,
    db: Session = Depends(get_db),
):
    """Return a single order by ID."""
    order = crud.get_order(db, oid)

    if order is None:
        raise HTTPException(
            status_code=404,
            detail="Order not found.",
        )

    return order


@app.patch("/orders/{oid}", response_model=schemas.OrderRead, dependencies=auth_required,)
async def update_order(
    oid: int,
    data: schemas.OrderUpdate,
    db: Session = Depends(get_db),
):
    order = await run_in_threadpool(crud.get_order, db, oid)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found.")

    changes = data.model_dump(exclude_unset=True)
    reprice = bool(PROPERTY_FIELDS & changes.keys())

    price = status = None
    if reprice:
        payload = {f: getattr(order, f) for f in FORECAST_FIELDS}
        payload.update(changes)
        price, status = await get_prediction(payload)

    return await run_in_threadpool(
        crud.update_order, db, order, data, reprice, price, status
    )


@app.delete(
    "/orders/{oid}",
    status_code=204,
    dependencies=auth_required,
)
def delete_order(
    oid: int,
    db: Session = Depends(get_db),
) -> None:
    """Delete an existing order."""
    order = crud.get_order(db, oid)

    if order is None:
        raise HTTPException(
            status_code=404,
            detail="Order not found.",
        )

    crud.delete_order(db, order)