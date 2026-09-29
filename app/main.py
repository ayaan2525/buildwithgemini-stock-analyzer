"""
FastAPI Server for Stock Market Analyzer.
Provides REST endpoints and serves the mobile-responsive web dashboard.
"""
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from pathlib import Path
import threading

from app.database import (
    init_db, get_latest_run_details, get_runs_list,
    get_run_details, get_chat_history, clear_chat_history,
    add_to_portfolio, remove_from_portfolio, get_user_portfolio, clear_user_portfolio
)
from app.services.analyzer_service import run_full_market_analysis
from app.services.qa_service import generate_answer, resolve_stock

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

app = FastAPI(title="Stock Market Analyzer (AI, Chips, Energy)", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Background analysis lock and status tracking
ANALYSIS_STATE = {
    "is_running": False,
    "progress": "Idle",
    "last_error": None
}
analysis_lock = threading.Lock()

def background_analysis_task():
    global ANALYSIS_STATE
    try:
        ANALYSIS_STATE["is_running"] = True
        ANALYSIS_STATE["progress"] = "Fetching 7-day Google News & quotes for AI, Chips, Energy..."
        ANALYSIS_STATE["last_error"] = None
        run_full_market_analysis()
        ANALYSIS_STATE["progress"] = "Complete"
    except Exception as e:
        print(f"Error during analysis run: {e}")
        ANALYSIS_STATE["last_error"] = str(e)
        ANALYSIS_STATE["progress"] = "Failed"
    finally:
        ANALYSIS_STATE["is_running"] = False

class AskRequest(BaseModel):
    question: str

@app.on_event("startup")
def on_startup():
    init_db()
    # If database is fresh and empty, initiate first run in background
    if not get_latest_run_details():
        threading.Thread(target=background_analysis_task, daemon=True).start()

# API Endpoints

@app.get("/api/status")
def get_status_alias():
    return get_status()

@app.get("/api/latest")
def get_latest_alias():
    return get_latest_analysis()

@app.get("/api/analysis/status")
def get_status():
    return ANALYSIS_STATE

@app.get("/api/analysis/latest")
def get_latest_analysis():
    data = get_latest_run_details()
    if not data:
        return {"status": "empty", "message": "No analysis completed yet. Please trigger an analysis."}
    return data

@app.get("/api/analysis/history")
def get_history(limit: int = 30):
    return get_runs_list(limit=limit)

@app.get("/api/analysis/run/{run_id}")
def get_run(run_id: int):
    data = get_run_details(run_id)
    if not data:
        raise HTTPException(status_code=404, detail="Run not found")
    return data

@app.post("/api/analysis/trigger")
def trigger_analysis(background_tasks: BackgroundTasks):
    global ANALYSIS_STATE
    if ANALYSIS_STATE["is_running"]:
        return {"status": "already_running", "message": "An analysis run is already in progress."}

    background_tasks.add_task(background_analysis_task)
    return {"status": "started", "message": "7-day market analysis started in background."}

@app.post("/api/ask")
def ask_analyzer(payload: AskRequest):
    if not payload.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    answer = generate_answer(payload.question.strip())
    return {"answer": answer}

@app.get("/api/chat/history")
def get_chat_messages(limit: int = 50):
    return get_chat_history(limit=limit)

@app.delete("/api/chat/history")
def clear_chat():
    clear_chat_history()
    return {"status": "cleared"}

# User Portfolio Memory Endpoints
class PortfolioAddRequest(BaseModel):
    ticker: str
    company_name: Optional[str] = None
    domain: Optional[str] = None
    shares: Optional[float] = 1.0
    notes: Optional[str] = ""

@app.get("/api/portfolio")
def list_portfolio():
    return {"portfolio": get_user_portfolio()}

@app.post("/api/portfolio")
def add_portfolio_item(payload: PortfolioAddRequest):
    info = resolve_stock(payload.ticker)
    ticker = info["ticker"] if info else payload.ticker.upper().strip()
    company_name = payload.company_name or (info["company_name"] if info else ticker)
    domain = payload.domain or (info["domain"] if info else "General")
    item = add_to_portfolio(
        ticker=ticker,
        company_name=company_name,
        domain=domain,
        shares=payload.shares or 1.0,
        notes=payload.notes or "Added via API"
    )
    return {"status": "success", "item": item}

@app.delete("/api/portfolio/{ticker}")
def delete_portfolio_item(ticker: str):
    removed = remove_from_portfolio(ticker)
    return {"status": "success" if removed else "not_found", "ticker": ticker.upper()}

@app.delete("/api/portfolio")
def clear_portfolio():
    clear_user_portfolio()
    return {"status": "cleared"}

# Static file mount for UI
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

@app.get("/")
def serve_index():
    return FileResponse(FRONTEND_DIR / "index.html")
