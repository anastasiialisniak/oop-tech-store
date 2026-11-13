
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.auth import router as auth_router
from src.api.products import router as products_router
from src.api.orders import router as orders_router
from src.services.database import verify_and_log_database_config


@asynccontextmanager
async def lifespan(_app: FastAPI):
    verify_and_log_database_config()
    yield


verify_and_log_database_config()

app = FastAPI(
    title="Nexora API",
    description="API for the Nexora online technology store",
    version="1.0.0",
    lifespan=lifespan,
)

# Дозволяємо frontend звертатися до backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://127.0.0.1:5501",
        "http://localhost:5501",
        "http://127.0.0.1:3000",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(products_router)
app.include_router(orders_router)


@app.get("/")
def home():
    return {"message": "Welcome to Nexora API!"}


@app.get("/health")
def health_check():
    return {"status": "ok"}
