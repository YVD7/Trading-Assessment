# Trading Bot — Binance Futures Testnet (USDT-M)

A small, structured Python CLI application for placing MARKET, LIMIT, and
STOP_LIMIT orders on Binance's USDT-M Futures Testnet, with input
validation, structured logging, and clean error handling.

## Project structure

```
trading_bot/
  bot/
    __init__.py
    client.py         # Binance Futures Testnet API wrapper (network boundary)
    orders.py         # Order construction, placement, response formatting
    validators.py      # CLI input validation
    logging_config.py  # Logging setup (file + console handlers)
  cli.py                # CLI entry point (argparse)
  logs/
    trading_bot.log     # created at runtime
    examples/           # sample logs (see logs/examples/README.md)
  requirements.txt
  README.md
```

The code is layered on purpose:
- **`cli.py`** only parses arguments and wires things together.
- **`bot/validators.py`** owns trading-semantics validation (valid sides,
  positive quantity, price required for LIMIT, etc.) — independent of both
  argparse and the network layer.
- **`bot/client.py`** is the *only* module that talks to Binance. All
  request/response/error logging happens here in one place.
- **`bot/orders.py`** turns a validated `OrderRequest` into the right client
  call and formats the response for the user.

This separation means the client layer could be swapped for raw
`requests`/`httpx` calls later without touching validation, CLI parsing, or
order-formatting logic.

## Setup

### 1. Create a Binance Futures Testnet account
1. Go to https://testnet.binancefuture.com and register/log in (GitHub login
   is supported).
2. Once logged in, generate an **API Key** and **API Secret** from the
   testnet dashboard (top right → API Key).
3. The testnet account is pre-funded with mock USDT — no real funds are
   involved.

### 2. Install dependencies
```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Set credentials
Preferred (environment variables):
```bash
export BINANCE_TESTNET_API_KEY="your-testnet-api-key"
export BINANCE_TESTNET_API_SECRET="your-testnet-api-secret"
```
Or pass them per-command with `--api-key` / `--api-secret`.

> The client is hard-pointed at `https://testnet.binancefuture.com` — it
> will never touch the live Binance API, regardless of credentials used.

## Usage

### Market order
```bash
python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01
```

### Limit order
```bash
python cli.py --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.01 --price 65000
```

### Stop-limit order (bonus order type)
```bash
python cli.py --symbol BTCUSDT --side SELL --type STOP_LIMIT \
  --quantity 0.01 --price 64000 --stop-price 64500
```

### Verbose mode (prints DEBUG logs, i.e. raw request/response payloads, to console too)
```bash
python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01 --verbose
```

### Example output
```
>> Order request: symbol=BTCUSDT, side=BUY, type=MARKET, quantity=0.01
>> Order response:
   orderId      : 123456789
   status       : FILLED
   symbol       : BTCUSDT
   side         : BUY
   type         : MARKET
   origQty      : 0.01
   executedQty  : 0.01
   avgPrice     : 65123.40
>> SUCCESS: order accepted by Binance Futures Testnet.
```

On failure (invalid input, rejected order, or network issue), the bot prints
a clear `Invalid input: ...` / `>> FAILED: ...` / `Error: ...` message and
exits with a non-zero status code (see **Exit codes** below), instead of
raising a raw traceback.

## Logging

Every run appends to `logs/trading_bot.log` (auto-rotated at 2MB, 5 backups
kept):
- `DEBUG` — outgoing request parameters and full raw API responses
- `INFO` — order placement start/success (concise, one line each)
- `ERROR` — validation failures, API errors, and network errors, with enough
  context to debug without re-running

The console only shows `INFO`+ by default (use `--verbose` for `DEBUG`), so
normal usage stays readable while the log file keeps the full audit trail.

Sample logs from real MARKET and LIMIT runs are in `logs/examples/` — see
`logs/examples/README.md` for how they were produced.

## Error handling

- **Invalid CLI input** (bad symbol format, invalid side/type, non-numeric
  or non-positive quantity/price, missing price on a LIMIT order) is caught
  by `bot/validators.py` before any network call is made, and reported as
  `Invalid input: ...` (exit code `2`).
- **Binance API errors** (e.g. bad symbol, insufficient testnet balance,
  quantity below the symbol's minimum) are caught, logged with the
  Binance error code/message, and reported as `>> FAILED: ...` (exit code `4`).
- **Network/timeout errors** are caught separately and reported as
  `Error: Network error while calling Binance: ...` (exit code `3`).
- Any other unexpected exception is logged with a full traceback
  (`logger.exception`) and reported as `Unexpected error: ...` (exit code `1`)
  rather than crashing with a raw stack trace on screen.

### Exit codes
| Code | Meaning |
|------|---------|
| 0 | Order placed successfully |
| 1 | Unexpected/unhandled error |
| 2 | Invalid CLI input |
| 3 | API client init / network error |
| 4 | Order rejected by Binance (API error) |

## Assumptions

- Only **USDT-M Futures Testnet** is in scope (not COIN-M, not spot).
- Symbol validation assumes standard `<BASE>USDT` perpetual futures symbols
  (e.g. `BTCUSDT`, `ETHUSDT`); exotic/expiring contract symbols aren't
  covered.
- LIMIT and STOP_LIMIT orders default to `timeInForce=GTC` (Good-Till-Cancel);
  this isn't currently exposed as a CLI flag, to keep the interface small.
- Quantity precision/step-size and price tick-size rules are enforced by
  Binance itself (the API will reject an order with the appropriate error
  message, which the bot surfaces); the bot doesn't pre-fetch and validate
  exchange filters client-side.
- The bonus order type implemented is **STOP_LIMIT** (via Binance's `STOP`
  order type, which is a stop-triggered limit order on Futures).
- API credentials are read from environment variables by default and never
  logged, per the log-hygiene guard in `bot/client.py`.

## Bonus implemented

- ✅ Third order type: **STOP_LIMIT**
- CLI validates all input up front with clear, specific error messages
  before any network call.
