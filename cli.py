#!/usr/bin/env python3
"""
CLI entry point for the Simplified Trading Bot (Binance Futures Testnet).

Examples:
    # Market order
    python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01

    # Limit order
    python cli.py --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.01 --price 65000

    # Stop-limit order (bonus)
    python cli.py --symbol BTCUSDT --side SELL --type STOP_LIMIT --quantity 0.01 \\
        --price 64000 --stop-price 64500

Credentials can be supplied via environment variables (recommended) or CLI flags:
    export BINANCE_TESTNET_API_KEY=xxxx
    export BINANCE_TESTNET_API_SECRET=xxxx
"""

import argparse
import os
import sys

from bot.client import APIClientError, BinanceFuturesTestnetClient
from bot.logging_config import setup_logging
from bot.orders import OrderError, OrderManager, OrderRequest
from bot.validators import (
    ValidationError,
    validate_order_type,
    validate_price,
    validate_quantity,
    validate_side,
    validate_stop_price,
    validate_symbol,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trading_bot",
        description="Place MARKET / LIMIT / STOP_LIMIT orders on Binance Futures Testnet (USDT-M).",
    )
    parser.add_argument("--symbol", required=True, help="Trading pair, e.g. BTCUSDT")
    parser.add_argument("--side", required=True, choices=["BUY", "SELL", "buy", "sell"], help="Order side")
    parser.add_argument(
        "--type", dest="order_type", required=True,
        choices=["MARKET", "LIMIT", "STOP_LIMIT", "market", "limit", "stop_limit"],
        help="Order type",
    )
    parser.add_argument("--quantity", required=True, help="Order quantity (base asset units)")
    parser.add_argument("--price", required=False, default=None, help="Limit price (required for LIMIT/STOP_LIMIT)")
    parser.add_argument(
        "--stop-price", dest="stop_price", required=False, default=None,
        help="Stop trigger price (required for STOP_LIMIT)",
    )
    parser.add_argument(
        "--api-key", dest="api_key", default=os.environ.get("BINANCE_TESTNET_API_KEY"),
        help="Binance Futures Testnet API key (defaults to $BINANCE_TESTNET_API_KEY)",
    )
    parser.add_argument(
        "--api-secret", dest="api_secret", default=os.environ.get("BINANCE_TESTNET_API_SECRET"),
        help="Binance Futures Testnet API secret (defaults to $BINANCE_TESTNET_API_SECRET)",
    )
    parser.add_argument("--verbose", action="store_true", help="Print DEBUG-level logs to console too")
    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    logger = setup_logging(verbose_console=args.verbose)

    # --- Validate input -------------------------------------------------
    try:
        symbol = validate_symbol(args.symbol)
        side = validate_side(args.side)
        order_type = validate_order_type(args.order_type)
        quantity = validate_quantity(args.quantity)
        price = validate_price(args.price, order_type)
        stop_price = validate_stop_price(args.stop_price, order_type)
    except ValidationError as exc:
        logger.error("Input validation failed: %s", exc)
        print(f"Invalid input: {exc}")
        return 2

    request = OrderRequest(
        symbol=symbol, side=side, order_type=order_type,
        quantity=quantity, price=price, stop_price=stop_price,
    )

    # --- Build client + place order -------------------------------------
    try:
        client = BinanceFuturesTestnetClient(api_key=args.api_key, api_secret=args.api_secret)
        manager = OrderManager(client)
        manager.place_order(request)
    except APIClientError as exc:
        logger.error("Client initialization failed: %s", exc)
        print(f"Error: {exc}")
        return 3
    except OrderError:
        # Already logged/printed inside OrderManager.place_order
        return 4
    except Exception as exc:  # noqa: BLE001 - final safety net, still logged
        logger.exception("Unexpected error while placing order")
        print(f"Unexpected error: {exc}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
