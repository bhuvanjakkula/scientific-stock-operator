from risk_codex import (
    RiskBudget, Thesis, Side, LiquidityProfile,
    MarketDiagnosis, Regime, Expectancy, decide,
)

budget = RiskBudget(account_equity=100_000, risk_fraction_per_idea=0.01)
thesis = Thesis("ABC", Side.LONG, entry=50.0, invalidation=48.0)
liq = LiquidityProfile(
    average_daily_volume=5_000_000,
    bid_ask_spread=0.01,
    displayed_price=50.0,
    free_float_shares=200_000_000,
)
tape = MarketDiagnosis(
    regime=Regime.ADVANCE,
    price_structure_higher_highs=True,
    volume_confirms_direction=True,
    breadth_expanding=True,
    volatility_elevated=False,
    liquidity_adequate=True,
)
ev = Expectancy(p_gain=0.45, gain=6.0, p_loss=0.55, loss=2.0, costs=0.05)

d = decide(budget, thesis, liq, tape, stock_rs=0.08, group_rs=0.05, expectancy=ev)
print(f"d.accepted {d.accepted}, d.shares {d.shares}, d.planned_loss {d.planned_loss}")
