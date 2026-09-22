from fastapi import FastAPI
from pydantic import BaseModel


app = FastAPI(
    title="SmartBancs AI Service",
    description="Mock financial recommendation service",
    version="1.0.0",
)


class RecommendationRequest(BaseModel):
    transaction_id: str
    source_account: str
    destination_account: str
    amount: float
    currency: str


class RecommendationResponse(BaseModel):
    transaction_id: str
    recommendation: str
    model_version: str


@app.get("/health")
def health():
    return {
        "status": "UP",
        "service": "ai-service",
    }


@app.post(
    "/recommendations",
    response_model=RecommendationResponse,
)
def generate_recommendation(
    request: RecommendationRequest,
):
    amount = request.amount

    if amount >= 500:
        recommendation = (
            "Consider reviewing your monthly budget "
            "before making additional large transactions."
        )

    elif amount >= 100:
        recommendation = (
            "Consider allocating part of your available "
            "funds to a savings goal."
        )

    else:
        recommendation = (
            "Your transaction is within a low-value range. "
            "Continue monitoring your regular spending."
        )

    return {
        "transaction_id": request.transaction_id,
        "recommendation": recommendation,
        "model_version": "mock-v1",
    }