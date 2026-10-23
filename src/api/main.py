
from fastapi import FastAPI

app = FastAPI(
    title="Nexora API",
    description="API for the Nexora online technology store",
    version="1.0.0",
)


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
