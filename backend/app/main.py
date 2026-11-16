from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.api import threads
from app.auth.dependencies import CurrentUser, get_current_user
from app.config import settings

app = FastAPI(title="Document Copilot")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins.split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(threads.router)

COMPANIES = [
    {"ticker": "AAPL", "name": "Apple Inc.", "cik": "0000320193"},
    {"ticker": "MSFT", "name": "Microsoft Corp.", "cik": "0000789019"},
    {"ticker": "GOOGL", "name": "Alphabet Inc.", "cik": "0001652044"},
    {"ticker": "AMZN", "name": "Amazon.com Inc.", "cik": "0001018724"},
    {"ticker": "NVDA", "name": "NVIDIA Corp.", "cik": "0001045810"},
]


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/companies")
async def get_companies():
    return COMPANIES


@app.get("/companies/{ticker}")
async def get_company(ticker: str):
    for company in COMPANIES:
        if company["ticker"].lower() == ticker.lower():
            return company
    raise HTTPException(status_code=404, detail="Company not found")


@app.get("/me")
async def me(user: CurrentUser = Depends(get_current_user)):
    return {"id": user.id, "email": user.email}
