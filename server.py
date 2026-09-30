from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from risk_codex import (
    RiskBudget, Thesis, Side, LiquidityProfile, MarketDiagnosis, Regime, decide
)
from fastapi.middleware.cors import CORSMiddleware
import os

app = FastAPI(title="Scientific Stock Operator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

@app.get("/")
def get_index():
    return FileResponse(os.path.join(BASE_DIR, "index.html"))

@app.get("/style.css")
def get_style():
    return FileResponse(os.path.join(BASE_DIR, "style.css"))

@app.get("/app.js")
def get_js():
    return FileResponse(os.path.join(BASE_DIR, "app.js"))

class DecideRequest(BaseModel):
    equity: float
    risk_fraction: float = 0.01
    entry: float
    invalidation: float
    side: str = "long"
    adv: float
    spread: float
    free_float: float = 100_000_000
    regime: str = "advance"
    stock_rs: float = 0.0
    group_rs: float = 0.0

@app.post("/api/decide")
def api_decide(req: DecideRequest):
    budget = RiskBudget(req.equity, req.risk_fraction)
    thesis = Thesis("APP", Side.LONG if req.side.lower() == "long" else Side.SHORT, req.entry, req.invalidation)
    liq = LiquidityProfile(req.adv, req.spread, req.entry, req.free_float)
    
    try:
        reg = Regime(req.regime.lower())
    except ValueError:
        reg = Regime.UNSTABLE
        
    md = MarketDiagnosis(
        regime=reg,
        price_structure_higher_highs=reg == Regime.ADVANCE,
        volume_confirms_direction=reg == Regime.ADVANCE,
        breadth_expanding=reg == Regime.ADVANCE,
        volatility_elevated=reg == Regime.UNSTABLE,
        liquidity_adequate=reg != Regime.UNSTABLE
    )
    
    d = decide(budget, thesis, liq, md, req.stock_rs, req.group_rs)
    
    return {
        "accepted": d.accepted,
        "shares": d.shares,
        "planned_loss": d.planned_loss,
        "alignment": d.alignment.value,
        "reasons": d.reasons,
        "warnings": d.warnings
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("server:app", host="0.0.0.0", port=port)
