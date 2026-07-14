"""
Thin wrapper around python-binance's Client, scoped to USDT-M Futures
Testnet order placement.

This is the only module that talks to the network. Keeping it isolated
means:
  - orders.py / cli.py never import python-binance directly
  - all requests/responses/errors are logged in exactly one place
  - swapping python-binance for raw `requests` calls later only touches
    this file
"""

import logging
import time

from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceRequestException
from requests.exceptions import ConnectionError as RequestsConnectionError
from requests.exceptions import RequestException, Timeout

logger = logging.getLogger("trading_bot.client")

FUTURES_TESTNET_BASE_URL = "https://testnet.binancefuture.com"


class APIClientError(Exception):
    """Raised for any failure talking to the Binance Futures Testnet API."""


class BinanceFuturesTestnetClient:
    """
    Wraps python-binance's Client for USDT-M Futures Testnet order placement,
    with request/response logging and translated exceptions.
    """

    def __init__(self, api_key: str, api_secret: str, timeout: int = 10):
        if not api_key or not api_secret:
            raise APIClientError(
                "Missing API credentials. Set BINANCE_TESTNET_API_KEY and "
                "BINANCE_TESTNET_API_SECRET (env vars or --api-key/--api-secret)."
            )

        # python-binance's `testnet=True` flag points spot endpoints at the
        # spot testnet; for futures we additionally repoint FUTURES_URL
        # explicitly so this always targets the Futures Testnet regardless
        # of library version defaults.
        self._client = Client(api_key, api_secret, testnet=True, requests_params={"timeout": timeout})
        self._client.FUTURES_URL = FUTURES_TESTNET_BASE_URL + "/fapi"

        logger.debug("Initialized Binance Futures Testnet client (base_url=%s)", FUTURES_TESTNET_BASE_URL)

    def _call(self, description: str, func, **kwargs):
        """
        Execute a python-binance futures call with unified logging and
        error translation.
        """
        # Never log the api key/secret even though they aren't passed as
        # kwargs here; this is a defensive log-hygiene guard for future edits.
        safe_kwargs = {k: v for k, v in kwargs.items() if k not in ("api_key", "api_secret")}
        logger.debug("REQUEST  | %s | params=%s", description, safe_kwargs)

        start = time.monotonic()
        try:
            response = func(**kwargs)
        except BinanceAPIException as exc:
            # Raised when Binance returns a well-formed error response
            # (e.g. bad symbol, insufficient balance, invalid quantity step).
            logger.error(
                "API ERROR | %s | status=%s code=%s message=%s",
                description, exc.status_code, exc.code, exc.message,
            )
            raise APIClientError(f"Binance API error ({exc.code}): {exc.message}") from exc
        except BinanceRequestException as exc:
            # Raised when the response isn't valid JSON / malformed request.
            logger.error("REQUEST ERROR | %s | %s", description, exc)
            raise APIClientError(f"Malformed request/response: {exc}") from exc
        except (Timeout, RequestsConnectionError) as exc:
            logger.error("NETWORK ERROR | %s | %s", description, exc)
            raise APIClientError(f"Network error while calling Binance: {exc}") from exc
        except RequestException as exc:
            logger.error("HTTP ERROR | %s | %s", description, exc)
            raise APIClientError(f"HTTP error while calling Binance: {exc}") from exc

        elapsed_ms = (time.monotonic() - start) * 1000
        logger.debug("RESPONSE | %s | elapsed=%.1fms | data=%s", description, elapsed_ms, response)
        return response

    # ------------------------------------------------------------------
    # Public API surface used by orders.py
    # ------------------------------------------------------------------

    def create_market_order(self, symbol: str, side: str, quantity: float) -> dict:
        return self._call(
            f"POST /fapi/v1/order (MARKET {side} {symbol})",
            self._client.futures_create_order,
            symbol=symbol,
            side=side,
            type="MARKET",
            quantity=quantity,
        )

    def create_limit_order(
        self, symbol: str, side: str, quantity: float, price: float, time_in_force: str = "GTC"
    ) -> dict:
        return self._call(
            f"POST /fapi/v1/order (LIMIT {side} {symbol})",
            self._client.futures_create_order,
            symbol=symbol,
            side=side,
            type="LIMIT",
            quantity=quantity,
            price=price,
            timeInForce=time_in_force,
        )

    def create_stop_limit_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        stop_price: float,
        time_in_force: str = "GTC",
    ) -> dict:
        """Bonus order type: STOP as a stop-limit (triggers a LIMIT order at `price`)."""
        return self._call(
            f"POST /fapi/v1/order (STOP {side} {symbol})",
            self._client.futures_create_order,
            symbol=symbol,
            side=side,
            type="STOP",
            quantity=quantity,
            price=price,
            stopPrice=stop_price,
            timeInForce=time_in_force,
        )

    def get_order_status(self, symbol: str, order_id: int) -> dict:
        return self._call(
            f"GET /fapi/v1/order (symbol={symbol}, orderId={order_id})",
            self._client.futures_get_order,
            symbol=symbol,
            orderId=order_id,
        )
