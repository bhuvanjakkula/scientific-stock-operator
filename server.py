from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from risk_codex import (
    RiskBudget, Thesis, Side, LiquidityProfile, MarketDiagnosis, Regime, decide
)
from fastapi.middleware.cors import CORSMiddleware
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

# Mount static files for the dashboard
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)
