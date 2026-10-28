from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database.session import Base, engine
import app.models  # noqa: F401
from app.routers import client_router, invoice_router, payment_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield
    engine.dispose()


app = FastAPI(
    title="Payment Gateway API",
    version="1.0.0",
    lifespan=lifespan,
)

@app.get("/")
async def root():
    return {"message": "Payment Gateway API is running"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

app.include_router(client_router.router)
app.include_router(invoice_router.router)
app.include_router(payment_router.router)

