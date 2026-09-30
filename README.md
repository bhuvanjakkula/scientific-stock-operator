# The Scientific Operator

*Never ask capital to obey an untested opinion.*

The Scientific Operator is an institutional-grade decision engine built for serious traders. It mathematically calculates exact position sizes, aligns trades with current market regimes, and acts as a strict risk-management gateway before capital is deployed.

## Features
- **Strict Risk Management**: Prevent emotional mistakes by mathematically limiting downside risk.
- **Dynamic Sizing**: Position sizing is dynamically adjusted based on market regimes and volatility.
- **Market Alignment**: Enforces alignment with broader market trends (Advance, Decline, Range, Unstable).

## Setup
```bash
pip install -r requirements.txt
uvicorn server:app --host 127.0.0.1 --port 8000
```
