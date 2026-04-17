---
name: arb-agent-system
description: >
  Use this skill when working on arb-agent-system — a multi-agent financial
  arbitrage detection system built with FastAPI microservices, real-time
  market data via ccxt, PostgreSQL audit logging, and Docker Compose.
  Activate when the user mentions arb-agent-system, arbitrage, spread detection,
  order books, ccxt, execution service, risk service, or orchestrator pipeline.
---

# arb-agent-system

> "Architecture first. Always."

## Project Overview

arb-agent-system is a multi-agent arbitrage detection system demonstrating
microservices architecture, real-time market data ingestion, distributed
risk management, and event-driven orchestration.

This is a research and demonstration system. Paper trading mode is enabled
by default — no real orders are placed.

- Language: Python (FastAPI)
- License: MIT

## Architecture

Five independent FastAPI microservices connected through HTTP contracts,
orchestrated by a central coordinator:

```
orchestrator/
  app.py           ← Pipeline coordinator. Calls each service in sequence.

data-service/
  app.py           ← Live order book ingestion via ccxt (Coinbase, Kraken)

strategy-service/
  app.py           ← Spread calculation and trade signal generation

risk-service/
  app.py           ← Independent risk approval gate

execution-service/
  app.py           ← Order execution (paper trading mode)

db/
  init.sql         ← PostgreSQL schema

docker-compose.yml ← Full stack definition
.devcontainer/     ← VS Code Dev Container config
```

## Pipeline Flow

```
GET /run →
  1. data-service    → fetch live BTC/USD order books
  2. strategy-service → calculate spreads, generate signal
  3. risk-service    → approve or reject signal
  4. execution-service → execute (paper) or skip
  5. PostgreSQL      → log full trace regardless of outcome
```

## Service Endpoints

### Orchestrator (port 8080)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Full pipeline health check — cascades through all services |
| `/run` | GET | Execute one full detection cycle |

### Data Service (port 8081)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Liveness check |
| `/ready` | GET | Readiness — validates exchange connectivity |
| `/price` | GET | Fetch live best bid/ask from all exchanges |

### Strategy Service (port 8082)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Liveness check |
| `/signal` | POST | Evaluate price data, return trade signal |

### Risk Service (port 8083)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Liveness check |
| `/risk` | POST | Evaluate signal, return approval decision |

### Execution Service (port 8084)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Liveness check |
| `/execute` | POST | Execute or simulate approved signal |

## Arbitrage Math

```python
# Buy low (ask price), sell high (bid price)
spread_cb_to_kr = kraken_bid - coinbase_ask   # Buy Coinbase, Sell Kraken
spread_kr_to_cb = coinbase_bid - kraken_ask   # Buy Kraken, Sell Coinbase

# Signal generated if spread > SPREAD_THRESHOLD
if spread_cb_to_kr > SPREAD_THRESHOLD:
    signal = { "trade": True, "direction": "buy_coinbase_sell_kraken", ... }
```

## Market Data (data-service)

Uses ccxt library for real exchange connectivity:
- Coinbase (coinbaseexchange)
- Kraken (kraken)
- Fetches Level 2 order books (best bid/ask)
- No API keys required for public market data
- Graceful partial failure — one exchange can fail without crashing

```python
# Internally:
order_book = exchange.fetch_order_book("BTC/USD")
best_bid = order_book["bids"][0][0]
best_ask = order_book["asks"][0][0]
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `SPREAD_THRESHOLD` | `10` | Minimum spread in USD to generate signal |
| `PAPER_TRADING` | `true` | Paper trade only — no real orders placed |
| `LOG_LEVEL` | `INFO` | Logging verbosity |

## Trade Lifecycle States

Every pipeline cycle is logged to PostgreSQL with one of these statuses:

| Status | Meaning |
|--------|---------|
| `executed` | Signal detected, approved, executed |
| `rejected` | Risk service rejected the signal |
| `no_opportunity` | No spread threshold exceeded |
| `error_data` | Data service failed |
| `error_strategy` | Strategy service failed |
| `error_execution` | Execution service failed |
| `fatal_error` | Unexpected exception |

## Database Schema

```sql
CREATE TABLE trades (
    id               SERIAL PRIMARY KEY,
    timestamp        TIMESTAMP DEFAULT NOW(),
    status           TEXT,
    coinbase_bid     NUMERIC,
    coinbase_ask     NUMERIC,
    kraken_bid       NUMERIC,
    kraken_ask       NUMERIC,
    spread           NUMERIC,
    direction        TEXT,
    approved         BOOLEAN,
    execution_status TEXT,
    raw              JSONB    -- full pipeline trace
);
```

## Pipeline Trace Example

```json
{
  "status": "executed",
  "trace": {
    "data": {
      "coinbase": { "bid": 68250.00, "ask": 68251.50 },
      "kraken":   { "bid": 68275.00, "ask": 68276.00 }
    },
    "strategy": {
      "trade": true,
      "direction": "buy_coinbase_sell_kraken",
      "spread": 23.50
    },
    "risk": { "approved": true },
    "execution": { "status": "paper_executed" }
  }
}
```

## Common Tasks

```bash
# Start full stack
docker compose up --build

# Test pipeline
curl http://localhost:8080/run

# Check system health
curl http://localhost:8080/health

# Check live market data
curl http://localhost:8081/price

# Check readiness (validates exchange connectivity)
curl http://localhost:8081/ready
```

## Key Design Decisions

- **Risk as independent gate** — cannot be bypassed by strategy or execution
- **`safe_request` wrapper** — all inter-service calls have timeout + error handling
- **`trace` pattern** — every stage captured for full audit trail
- **Health vs Readiness separation** — `/health` is fast liveness, `/ready` checks dependencies
- **Graceful degradation** — partial exchange failures return partial data, not errors

## Known Limitations / Future Work

- Fee modeling not yet implemented (fees would reduce effective spread)
- `/run` as GET is semantically impure — POST would be more correct
- DB connection per request (no pooling yet — fine for demo volume)
- Health check currently exercises strategy/risk logic (should be lightweight pings)
- WebSocket streaming vs polling for order books
- Prometheus metrics endpoint
- Grafana observability dashboard
- Multi-symbol support (ETH, SOL, etc.)
