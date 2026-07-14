"""
Order-level logic: turns validated CLI input into an API call, and turns
the raw API response into a clean summary for both logs and console output.
"""

import logging
from dataclasses import dataclass

from bot.client import APIClientError, BinanceFuturesTestnetClient

logger = logging.getLogger("trading_bot.orders")


@dataclass
class OrderRequest:
    symbol: str
    side: str
    order_type: str
    quantity: float
    price: float | None = None
    stop_price: float | None = None

    def summary(self) -> str:
        parts = [f"symbol={self.symbol}", f"side={self.side}", f"type={self.order_type}", f"quantity={self.quantity}"]
        if self.price is not None:
            parts.append(f"price={self.price}")
        if self.stop_price is not None:
            parts.append(f"stopPrice={self.stop_price}")
        return ", ".join(parts)


class OrderError(Exception):
    """Raised when an order cannot be placed (wraps validation/API errors)."""


class OrderManager:
    """Places orders via a BinanceFuturesTestnetClient and reports results."""

    def __init__(self, client: BinanceFuturesTestnetClient):
        self._client = client

    def place_order(self, request: OrderRequest) -> dict:
        logger.info("Placing order: %s", request.summary())
        print(f"\n>> Order request: {request.summary()}")

        try:
            if request.order_type == "MARKET":
                response = self._client.create_market_order(
                    symbol=request.symbol, side=request.side, quantity=request.quantity
                )
            elif request.order_type == "LIMIT":
                response = self._client.create_limit_order(
                    symbol=request.symbol,
                    side=request.side,
                    quantity=request.quantity,
                    price=request.price,
                )
            elif request.order_type == "STOP_LIMIT":
                response = self._client.create_stop_limit_order(
                    symbol=request.symbol,
                    side=request.side,
                    quantity=request.quantity,
                    price=request.price,
                    stop_price=request.stop_price,
                )
            else:
                # Shouldn't happen if validators.py did its job, but guard anyway.
                raise OrderError(f"Unsupported order type: {request.order_type}")
        except APIClientError as exc:
            logger.error("Order failed: %s | request=%s", exc, request.summary())
            print(f">> FAILED: {exc}\n")
            raise OrderError(str(exc)) from exc

        self._print_response(response)
        logger.info(
            "Order placed successfully: orderId=%s status=%s symbol=%s",
            response.get("orderId"), response.get("status"), response.get("symbol"),
        )
        return response

    @staticmethod
    def _print_response(response: dict) -> None:
        order_id = response.get("orderId")
        status = response.get("status")
        executed_qty = response.get("executedQty")
        avg_price = response.get("avgPrice")

        print(">> Order response:")
        print(f"   orderId      : {order_id}")
        print(f"   status       : {status}")
        print(f"   symbol       : {response.get('symbol')}")
        print(f"   side         : {response.get('side')}")
        print(f"   type         : {response.get('type')}")
        print(f"   origQty      : {response.get('origQty')}")
        print(f"   executedQty  : {executed_qty}")
        if avg_price not in (None, "0", "0.00000"):
            print(f"   avgPrice     : {avg_price}")
        print(">> SUCCESS: order accepted by Binance Futures Testnet.\n")
