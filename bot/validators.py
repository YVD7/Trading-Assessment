"""
Input validation for the trading bot CLI.

Each validator raises ValidationError with a human-readable message on
failure, and returns a normalized value on success. Keeping validation
separate from both the CLI parsing layer and the API client layer means:
  - the CLI only has to worry about *shape* (argparse types)
  - this module owns trading *semantics* (valid sides, positive quantity...)
  - the client layer can assume it always receives clean, valid data
"""

import re

VALID_SIDES = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT", "STOP_LIMIT"}

# Basic sanity check for USDT-M perpetual futures symbols, e.g. BTCUSDT, ETHUSDT.
_SYMBOL_RE = re.compile(r"^[A-Z0-9]{2,20}USDT$")


class ValidationError(Exception):
    """Raised when user-supplied CLI input fails validation."""


def validate_symbol(symbol: str) -> str:
    if not symbol:
        raise ValidationError("Symbol is required (e.g. BTCUSDT).")
    symbol = symbol.strip().upper()
    if not _SYMBOL_RE.match(symbol):
        raise ValidationError(
            f"Invalid symbol '{symbol}'. Expected a USDT-M futures symbol "
            f"like BTCUSDT or ETHUSDT."
        )
    return symbol


def validate_side(side: str) -> str:
    if not side:
        raise ValidationError("Side is required (BUY or SELL).")
    side = side.strip().upper()
    if side not in VALID_SIDES:
        raise ValidationError(f"Invalid side '{side}'. Must be one of {sorted(VALID_SIDES)}.")
    return side


def validate_order_type(order_type: str) -> str:
    if not order_type:
        raise ValidationError("Order type is required (MARKET, LIMIT, or STOP_LIMIT).")
    order_type = order_type.strip().upper()
    if order_type not in VALID_ORDER_TYPES:
        raise ValidationError(
            f"Invalid order type '{order_type}'. Must be one of {sorted(VALID_ORDER_TYPES)}."
        )
    return order_type


def validate_quantity(quantity) -> float:
    try:
        quantity = float(quantity)
    except (TypeError, ValueError):
        raise ValidationError(f"Quantity must be a number, got '{quantity}'.")
    if quantity <= 0:
        raise ValidationError("Quantity must be greater than 0.")
    return quantity


def validate_price(price, order_type: str) -> float | None:
    """
    Price is required for LIMIT and STOP_LIMIT orders, and must be absent
    (or ignored) for MARKET orders.
    """
    if order_type == "MARKET":
        return None

    if price is None:
        raise ValidationError(f"Price is required for {order_type} orders.")
    try:
        price = float(price)
    except (TypeError, ValueError):
        raise ValidationError(f"Price must be a number, got '{price}'.")
    if price <= 0:
        raise ValidationError("Price must be greater than 0.")
    return price


def validate_stop_price(stop_price, order_type: str) -> float | None:
    """Stop price is required only for STOP_LIMIT orders."""
    if order_type != "STOP_LIMIT":
        return None

    if stop_price is None:
        raise ValidationError("Stop price is required for STOP_LIMIT orders.")
    try:
        stop_price = float(stop_price)
    except (TypeError, ValueError):
        raise ValidationError(f"Stop price must be a number, got '{stop_price}'.")
    if stop_price <= 0:
        raise ValidationError("Stop price must be greater than 0.")
    return stop_price
