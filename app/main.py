from fastapi import FastAPI

app = FastAPI(
    title="SmartBancs API",
    description="MVP API para Smartbancs",
    version="1.0.0",
)


@app.get("/")
def root():
    return {
        "application": "SmartBancs API",
        "status": "running"
    }


@app.get("/health")
def health_check():
    return {
        "status": "UP"
    }