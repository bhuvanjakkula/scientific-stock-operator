#!/usr/bin/env python3
"""
Scientific Stock Operator — Risk Codex
I cannot promise the market will reward me.
I can promise I will never ask capital to obey an untested opinion.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from math import sqrt
from typing import Iterable, Optional
import json


class Side(str, Enum):
    LONG = "long"
    SHORT = "short"


class Alignment(str, Enum):
    STRONG = "strong"
    MIXED_GROUP = "mixed_group"
    ISOLATED_STRENGTH = "isolated_strength"
    WEAK = "weak"


class Regime(str, Enum):
    ADVANCE = "advance"
    DECLINE = "decline"
    RANGE = "range"
    UNSTABLE = "unstable"


class SourceRank(int, Enum):
    AUDITED_FILING = 1
    EXCHANGE_REGULATORY = 2
    VERIFIED_MANAGEMENT = 3
    INDEPENDENT_RESEARCH = 4
    RUMOR_OR_TIP = 5


def recovery_gain_required(loss_fraction: float) -> float:
    if loss_fraction >= 1.0:
        raise ValueError("A 100% loss cannot be recovered by a finite gain.")
    if loss_fraction < 0:
        raise ValueError("loss_fraction must be >= 0")
    return loss_fraction / (1.0 - loss_fraction)


def compounded_drawdown(returns: Iterable[float]) -> dict:
    equity = peak = 1.0
    max_dd = 0.0
    path = [1.0]
    for r in returns:
        equity *= 1.0 + r
        path.append(equity)
        peak = max(peak, equity)
        dd = (peak - equity) / peak if peak else 0.0
        max_dd = max(max_dd, dd)
    rec = recovery_gain_required(max_dd) if max_dd < 1 else float("inf")
    return {"ending_equity": equity, "max_drawdown": max_dd,
            "recovery_required": rec, "path": path}


@dataclass
class RiskBudget:
    """Book-wide: max position = permitted account risk / risk per share."""
    account_equity: float
    risk_fraction_per_idea: float = 0.01
    max_gross_exposure: float = 1.0
    max_correlated_cluster: float = 0.03
    max_leverage: float = 1.0

    def __post_init__(self) -> None:
        if self.account_equity <= 0:
            raise ValueError("account_equity must be positive")
        if not (0 < self.risk_fraction_per_idea < 0.25):
            raise ValueError("risk_fraction_per_idea should be a small positive fraction")

    @property
    def permitted_risk_dollars(self) -> float:
        return self.account_equity * self.risk_fraction_per_idea

    def shares_for_risk(self, entry: float, invalidation: float, side: Side = Side.LONG) -> int:
        risk_per_share = abs(entry - invalidation)
        if risk_per_share <= 0:
            raise ValueError("entry and invalidation must differ")
        raw = self.permitted_risk_dollars / risk_per_share
        notional_cap = (self.account_equity * self.max_gross_exposure * self.max_leverage) / entry
        return max(0, int(min(raw, notional_cap)))

    def dollars_at_risk(self, shares: int, entry: float, invalidation: float) -> float:
        return abs(entry - invalidation) * shares


def alignment_size_multiplier(alignment: Alignment) -> float:
    return {
        Alignment.STRONG: 1.00,
        Alignment.MIXED_GROUP: 0.50,
        Alignment.ISOLATED_STRENGTH: 0.25,
        Alignment.WEAK: 0.00,
    }[alignment]


@dataclass
class LiquidityProfile:
    average_daily_volume: float
    bid_ask_spread: float
    displayed_price: float
    free_float_shares: float
    ownership_top10_pct: float = 0.0
    depth_at_touch: float = 0.0
    stressed_volume_fraction: float = 0.35
    max_participation: float = 0.10

    def days_to_exit(self, shares: int, stressed: bool = False) -> float:
        vol = self.average_daily_volume * (self.stressed_volume_fraction if stressed else 1.0)
        usable = max(vol * self.max_participation, 1.0)
        return shares / usable

    def market_impact_estimate(self, shares: int, stressed: bool = False) -> float:
        vol = max(self.average_daily_volume * (self.stressed_volume_fraction if stressed else 1.0), 1.0)
        participation = shares / vol
        conc = 1.0 + self.ownership_top10_pct
        return self.displayed_price * 0.10 * sqrt(max(participation, 0.0)) * conc

    def realized_sell_price(self, shares: int, urgency: float = 0.0, stressed: bool = False) -> float:
        urgency = max(0.0, min(1.0, urgency))
        impact = self.market_impact_estimate(shares, stressed=stressed)
        urgency_cost = impact * urgency + self.bid_ask_spread * urgency
        return self.displayed_price - self.bid_ask_spread - impact - urgency_cost

    def paper_vs_realizable(self, shares: int, stressed: bool = True) -> dict:
        paper = self.displayed_price * shares
        real = self.realized_sell_price(shares, urgency=0.8, stressed=stressed) * shares
        return {
            "paper_value": paper,
            "realizable_value": real,
            "haircut": paper - real,
            "haircut_pct": (paper - real) / paper if paper else 0.0,
            "stressed_days_to_exit": self.days_to_exit(shares, stressed=True),
        }


@dataclass
class Expectancy:
    p_gain: float
    gain: float
    p_loss: float
    loss: float
    costs: float = 0.0

    def __post_init__(self) -> None:
        if self.p_gain + self.p_loss > 1.0 + 1e-9:
            raise ValueError("probabilities exceed 1")
        if min(self.p_gain, self.p_loss) < 0:
            raise ValueError("probabilities must be non-negative")

    @property
    def expected_value(self) -> float:
        return self.p_gain * self.gain - self.p_loss * self.loss - self.costs

    @property
    def payoff_ratio(self) -> float:
        return self.gain / self.loss if self.loss else float("inf")

    @property
    def favorable(self) -> bool:
        return self.expected_value > 0


@dataclass
class Thesis:
    symbol: str
    side: Side
    entry: float
    invalidation: float
    time_stop_sessions: Optional[int] = None
    fundamental_breaks: list[str] = field(default_factory=list)
    notes: str = ""

    def invalidated_by_price(self, last: float) -> bool:
        if self.side is Side.LONG:
            return last <= self.invalidation
        return last >= self.invalidation

    def risk_per_share(self) -> float:
        return abs(self.entry - self.invalidation)


@dataclass
class MarketDiagnosis:
    regime: Regime
    price_structure_higher_highs: bool
    volume_confirms_direction: bool
    breadth_expanding: bool
    volatility_elevated: bool
    liquidity_adequate: bool
    news_behavior_divergence: bool = False

    def deteriorating(self) -> bool:
        if self.regime in (Regime.DECLINE, Regime.UNSTABLE):
            return True
        weak = 0
        weak += not self.price_structure_higher_highs
        weak += not self.volume_confirms_direction
        weak += not self.breadth_expanding
        weak += self.volatility_elevated
        weak += 2 * (not self.liquidity_adequate)
        weak += self.news_behavior_divergence
        return weak >= 3

    def alignment_with_stock(self, stock_rs: float, group_rs: float) -> Alignment:
        stock_strong = stock_rs > 0
        group_strong = group_rs > 0
        market_ok = self.regime in (Regime.ADVANCE, Regime.RANGE) and not self.deteriorating()
        if market_ok and group_strong and stock_strong:
            return Alignment.STRONG
        if market_ok and not group_strong and stock_strong:
            return Alignment.ISOLATED_STRENGTH
        if market_ok and group_strong and not stock_strong:
            return Alignment.MIXED_GROUP
        if not market_ok and stock_strong:
            return Alignment.ISOLATED_STRENGTH
        return Alignment.WEAK


@dataclass
class InformationClaim:
    claim: str
    source_rank: SourceRank
    dated: str
    primary_source_url: str = ""
    already_in_price: bool = False
    changes_cash_flow: bool = False
    changes_risk: bool = False

    def actionable(self) -> bool:
        if self.source_rank is SourceRank.RUMOR_OR_TIP:
            return False
        if self.already_in_price and not self.changes_risk:
            return False
        return self.changes_cash_flow or self.changes_risk


@dataclass
class Position:
    thesis: Thesis
    shares: int
    liquidity: LiquidityProfile
    alignment: Alignment
    expectancy: Optional[Expectancy] = None
    source: Optional[InformationClaim] = None

    @property
    def notional(self) -> float:
        return self.shares * self.thesis.entry

    @property
    def planned_loss(self) -> float:
        return self.shares * self.thesis.risk_per_share()

    def forced_exit_loss(self, last: float, urgency: float = 1.0, stressed: bool = True) -> float:
        px = self.liquidity.realized_sell_price(self.shares, urgency=urgency, stressed=stressed)
        if self.thesis.side is Side.LONG:
            return (self.thesis.entry - px) * self.shares
        return (px - self.thesis.entry) * self.shares


@dataclass
class Portfolio:
    budget: RiskBudget
    positions: list[Position] = field(default_factory=list)
    clusters: dict[str, list[str]] = field(default_factory=dict)

    def gross_exposure(self) -> float:
        return sum(p.notional for p in self.positions)

    def net_exposure(self) -> float:
        net = 0.0
        for p in self.positions:
            sign = 1.0 if p.thesis.side is Side.LONG else -1.0
            net += sign * p.notional
        return net

    def planned_risk(self) -> float:
        return sum(p.planned_loss for p in self.positions)

    def cluster_risk(self, theme: str) -> float:
        symbols = set(self.clusters.get(theme, []))
        return sum(p.planned_loss for p in self.positions if p.thesis.symbol in symbols)

    def violations(self) -> list[str]:
        notes: list[str] = []
        eq = self.budget.account_equity
        if self.planned_risk() > eq * 0.06:
            notes.append(f"Aggregate planned risk {self.planned_risk():.0f} exceeds 6% of equity.")
        if self.gross_exposure() > eq * self.budget.max_gross_exposure * self.budget.max_leverage + 1e-6:
            notes.append("Gross exposure exceeds budget cap.")
        for theme in self.clusters:
            cap = eq * self.budget.max_correlated_cluster
            cr = self.cluster_risk(theme)
            if cr > cap + 1e-6:
                notes.append(f"Cluster '{theme}' risk {cr:.0f} exceeds cap {cap:.0f}.")
        for p in self.positions:
            if p.planned_loss > self.budget.permitted_risk_dollars + 1e-6:
                notes.append(f"{p.thesis.symbol} planned loss exceeds single-idea budget.")
            if p.alignment is Alignment.WEAK:
                notes.append(f"{p.thesis.symbol} is WEAK alignment — step aside.")
            days = p.liquidity.days_to_exit(p.shares, stressed=True)
            if days > 5:
                notes.append(f"{p.thesis.symbol} stressed exit is {days:.1f} days.")
            if p.source and p.source.source_rank is SourceRank.RUMOR_OR_TIP:
                notes.append(f"{p.thesis.symbol} is a tip without independent demand.")
            if p.expectancy and not p.expectancy.favorable:
                notes.append(f"{p.thesis.symbol} expectancy is not favorable after costs.")
        return notes

    def can_add(self, candidate: Position) -> tuple[bool, list[str]]:
        trial = Portfolio(self.budget, self.positions + [candidate], self.clusters)
        v = trial.violations()
        return (len(v) == 0, v)


@dataclass
class OperatorDecision:
    accepted: bool
    shares: int
    planned_loss: float
    alignment: Alignment
    reasons: list[str]
    warnings: list[str]
    realized_exit_preview: dict


def decide(
    budget: RiskBudget,
    thesis: Thesis,
    liquidity: LiquidityProfile,
    diagnosis: MarketDiagnosis,
    stock_rs: float,
    group_rs: float,
    expectancy: Optional[Expectancy] = None,
    source: Optional[InformationClaim] = None,
    portfolio: Optional[Portfolio] = None,
) -> OperatorDecision:
    reasons: list[str] = []
    warnings: list[str] = []

    if thesis.risk_per_share() <= 0:
        return OperatorDecision(False, 0, 0.0, Alignment.WEAK, ["No invalidation defined."], [], {})

    alignment = diagnosis.alignment_with_stock(stock_rs, group_rs)
    if alignment is Alignment.WEAK:
        reasons.append("Market, group, and stock are not aligned. Step aside.")
    if diagnosis.deteriorating() and thesis.side is Side.LONG:
        reasons.append("Vital signs deteriorating; long risk is not confirmed.")
    if source and not source.actionable():
        reasons.append("Information is a tip, already priced, or does not change cash flow/risk.")
    if expectancy and not expectancy.favorable:
        reasons.append("Expected value after costs is not positive.")

    preview_shares = budget.shares_for_risk(thesis.entry, thesis.invalidation, thesis.side)
    preview_shares = int(preview_shares * alignment_size_multiplier(alignment))

    liq = liquidity.paper_vs_realizable(max(preview_shares, 1), stressed=True)
    if liq["stressed_days_to_exit"] > 5 and preview_shares > 0:
        warnings.append(f"Stressed liquidation may take {liq['stressed_days_to_exit']:.1f} days.")
        while preview_shares > 0 and liquidity.days_to_exit(preview_shares, stressed=True) > 5:
            preview_shares = int(preview_shares * 0.8)

    if liq["haircut_pct"] > 0.08:
        warnings.append(f"Realizable haircut under stress is {liq['haircut_pct']:.1%} of paper value.")

    planned = preview_shares * thesis.risk_per_share()
    candidate = Position(thesis, preview_shares, liquidity, alignment, expectancy, source)

    if portfolio is not None and preview_shares > 0:
        ok, viol = portfolio.can_add(candidate)
        if not ok:
            reasons.extend(viol)

    accepted = preview_shares > 0 and not reasons
    if not accepted:
        preview_shares, planned = 0, 0.0

    return OperatorDecision(
        accepted=accepted,
        shares=preview_shares,
        planned_loss=planned,
        alignment=alignment,
        reasons=reasons,
        warnings=warnings,
        realized_exit_preview=liquidity.paper_vs_realizable(max(candidate.shares, 1), stressed=True),
    )


def kelly_fraction(p_gain: float, payoff_ratio: float) -> float:
    if payoff_ratio <= 0:
        return 0.0
    return max(0.0, p_gain - (1.0 - p_gain) / payoff_ratio)


def operator_fraction(p_gain: float, payoff_ratio: float, haircut: float = 0.25) -> float:
    """Quarter-Kelly: survival over maximization."""
    return kelly_fraction(p_gain, payoff_ratio) * haircut


@dataclass
class DecisionRecord:
    symbol: str
    known_at_the_time: dict
    action: str
    outcome: Optional[dict] = None
    process_error: Optional[str] = None

    def to_json(self) -> str:
        return json.dumps(asdict(self), default=str, indent=2)
