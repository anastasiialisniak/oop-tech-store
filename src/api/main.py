
from fastapi import FastAPI

from src.api.auth import router as auth_router


app = FastAPI(
    title="Nexora API",
    description="API for the Nexora online technology store",
    version="1.0.0",
)

# Authentication routes
app.include_router(auth_router)


@app.get("/")
def home():
    return {
        "message": "Welcome to Nexora API!"
    }


@app.get("/health")
def health_check():
    return {
        "status": "ok"
    }
