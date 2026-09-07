from __future__ import annotations

import asyncio
import logging
import re
import time
from dataclasses import dataclass, replace
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx

from .catalog import AssetSpec
from .config import Settings
from .errors import UserFacingError
from .parser import normalize_text

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class MarketQuote:
    symbol: str
    current: Decimal
    open: Decimal | None = None
    high: Decimal | None = None
    low: Decimal | None = None
    change: Decimal | None = None
    change_percent: Decimal | None = None
    updated_at: str | None = None


@dataclass(slots=True)
class CacheEntry:
    expires_at: float
    value: Any


class MarketAPI:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = httpx.AsyncClient(
            base_url=settings.oanor_base_url,
            headers={
                "x-oanor-key": settings.oanor_api_key,
                "accept": "application/json",
                "user-agent": "Iran-Gold-Currency-Bot/1.0",
            },
            timeout=httpx.Timeout(settings.http_timeout_seconds),
        )
        self._cache: dict[str, CacheEntry] = {}
        self._lock = asyncio.Lock()

    async def close(self) -> None:
        await self.client.aclose()

    async def get_quote(self, asset: AssetSpec) -> MarketQuote:
        endpoint = "/v1/currencies" if asset.category == "currency" else "/v1/gold"
        payload = await self._get_cached_json(
            endpoint,
            cache_key=endpoint,
            ttl=self.settings.cache_ttl_seconds,
        )

        quote = find_quote(payload, asset)
        if quote is None:
            # The aggregate endpoints are the first choice because one API call can serve many
            # user requests from the in-memory cache. If their shape changes or omits an asset,
            # resolve an official symbol and try the dedicated price endpoint.
            symbol = await self._resolve_symbol(asset)
            if symbol:
                quote = await self._get_price_quote(asset, symbol)

        if quote is None:
            raise UserFacingError(
                f"نرخ «{asset.fa_name}» در پاسخ فعلی سرویس پیدا نشد. "
                "ممکن است نام نماد یا ساختار API تغییر کرده باشد."
            )

        # If the group endpoint has current price but not daily OHLC, enrich it from /v1/price.
        if quote.high is None or quote.low is None:
            symbol = quote.symbol or await self._resolve_symbol(asset)
            if symbol:
                detailed = await self._get_price_quote(asset, symbol, raise_on_missing=False)
                if detailed:
                    quote = merge_quotes(quote, detailed)

        return quote

    async def _get_price_quote(
        self,
        asset: AssetSpec,
        symbol: str,
        *,
        raise_on_missing: bool = True,
    ) -> MarketQuote | None:
        key = f"/v1/price:{symbol}"
        try:
            payload = await self._get_cached_json(
                "/v1/price",
                cache_key=key,
                ttl=self.settings.cache_ttl_seconds,
                params={"symbol": symbol},
            )
        except UserFacingError:
            if raise_on_missing:
                raise
            logger.warning("Could not enrich quote from /v1/price | symbol=%s", symbol)
            return None

        quote = find_quote(payload, asset)
        if quote is None:
            # Dedicated price responses may omit symbol/name because the request already selects it.
            quote = first_quote(payload, symbol_hint=symbol)
        return quote

    async def _resolve_symbol(self, asset: AssetSpec) -> str | None:
        if asset.category == "currency":
            return asset.code

        payload = await self._get_cached_json(
            "/v1/symbols",
            cache_key="/v1/symbols",
            ttl=self.settings.symbols_cache_ttl_seconds,
        )
        return find_symbol(payload, asset)

    async def _get_cached_json(
        self,
        endpoint: str,
        *,
        cache_key: str,
        ttl: int,
        params: dict[str, str] | None = None,
    ) -> Any:
        now = time.monotonic()
        cached = self._cache.get(cache_key)
        if cached and cached.expires_at > now:
            return cached.value

        async with self._lock:
            now = time.monotonic()
            cached = self._cache.get(cache_key)
            if cached and cached.expires_at > now:
                return cached.value

            payload = await self._request_json(endpoint, params=params)
            self._cache[cache_key] = CacheEntry(expires_at=now + ttl, value=payload)
            return payload

    async def _request_json(
        self,
        endpoint: str,
        *,
        params: dict[str, str] | None = None,
    ) -> Any:
        try:
            response = await self.client.get(endpoint, params=params)
        except httpx.TimeoutException as exc:
            logger.warning("Market API timeout | endpoint=%s", endpoint)
            raise UserFacingError(
                "سرویس قیمت دیر پاسخ داد. چند لحظه دیگر دوباره امتحان کنید."
            ) from exc
        except httpx.HTTPError as exc:
            logger.warning("Market API network error | endpoint=%s | error=%s", endpoint, exc)
            raise UserFacingError(
                "در حال حاضر ارتباط با سرویس قیمت برقرار نشد. کمی بعد دوباره امتحان کنید."
            ) from exc

        if response.status_code in {401, 403}:
            logger.error("Oanor authentication failed | status=%s", response.status_code)
            raise UserFacingError(
                "کلید API سرویس قیمت معتبر نیست یا دسترسی آن فعال نشده است."
            )

        if response.status_code == 429:
            logger.warning("Oanor quota/rate limit reached")
            raise UserFacingError(
                "سهمیه یا محدودیت درخواست سرویس قیمت پر شده است. کمی بعد دوباره امتحان کنید."
            )

        if response.status_code >= 500:
            logger.warning("Oanor server error | status=%s", response.status_code)
            raise UserFacingError(
                "سرویس قیمت موقتاً در دسترس نیست. کمی بعد دوباره امتحان کنید."
            )

        try:
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPStatusError, ValueError) as exc:
            logger.warning(
                "Invalid market API response | status=%s | body=%s",
                response.status_code,
                response.text[:500],
            )
            raise UserFacingError(
                "پاسخ سرویس قیمت قابل پردازش نبود. لاگ برنامه را بررسی کنید."
            ) from exc


def merge_quotes(primary: MarketQuote, detail: MarketQuote) -> MarketQuote:
    return replace(
        primary,
        symbol=primary.symbol or detail.symbol,
        current=primary.current or detail.current,
        open=primary.open if primary.open is not None else detail.open,
        high=primary.high if primary.high is not None else detail.high,
        low=primary.low if primary.low is not None else detail.low,
        change=primary.change if primary.change is not None else detail.change,
        change_percent=(
            primary.change_percent
            if primary.change_percent is not None
            else detail.change_percent
        ),
        updated_at=primary.updated_at or detail.updated_at,
    )


def find_quote(payload: Any, asset: AssetSpec) -> MarketQuote | None:
    candidates: list[tuple[int, MarketQuote]] = []

    for path, record in iter_records(payload):
        quote = quote_from_record(record, symbol_hint=path.split(".")[-1] if path else "")
        if quote is None:
            continue

        identity = record_identity(record, path)
        score = match_score(identity, asset)
        if score > 0:
            candidates.append((score, quote))

    if not candidates:
        return None

    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1]


def find_symbol(payload: Any, asset: AssetSpec) -> str | None:
    candidates: list[tuple[int, str]] = []

    for path, record in iter_dicts(payload):
        identity = record_identity(record, path)
        score = match_score(identity, asset)
        if score <= 0:
            continue

        symbol = first_string(
            record,
            ("symbol", "code", "ticker", "slug", "id"),
        )
        if symbol:
            candidates.append((score, symbol))

    # Some APIs expose /symbols as a flat list of strings instead of objects.
    for value in iter_strings(payload):
        score = match_score(value, asset)
        if score > 0:
            candidates.append((score, value))

    if not candidates:
        return None

    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1]


def first_quote(payload: Any, *, symbol_hint: str = "") -> MarketQuote | None:
    direct = quote_from_record(payload, symbol_hint=symbol_hint)
    if direct is not None:
        return direct

    for _, record in iter_records(payload):
        quote = quote_from_record(record, symbol_hint=symbol_hint)
        if quote is not None:
            return quote
    return None


def iter_strings(payload: Any):
    if isinstance(payload, str):
        yield payload
    elif isinstance(payload, dict):
        for value in payload.values():
            yield from iter_strings(value)
    elif isinstance(payload, list):
        for value in payload:
            yield from iter_strings(value)


def iter_records(payload: Any, path: str = ""):
    if isinstance(payload, dict):
        yield path, payload
        for key, value in payload.items():
            child_path = f"{path}.{key}" if path else str(key)
            if isinstance(value, (int, float, Decimal, str)) and _to_decimal(value) is not None:
                synthetic = {"symbol": str(key), "price": value}
                yield child_path, synthetic
            elif isinstance(value, (dict, list)):
                yield from iter_records(value, child_path)

    elif isinstance(payload, list):
        for index, value in enumerate(payload):
            child_path = f"{path}.{index}" if path else str(index)
            yield from iter_records(value, child_path)


def iter_dicts(payload: Any, path: str = ""):
    if isinstance(payload, dict):
        yield path, payload
        for key, value in payload.items():
            if isinstance(value, (dict, list)):
                child_path = f"{path}.{key}" if path else str(key)
                yield from iter_dicts(value, child_path)
    elif isinstance(payload, list):
        for index, value in enumerate(payload):
            child_path = f"{path}.{index}" if path else str(index)
            yield from iter_dicts(value, child_path)


def quote_from_record(
    record: Any,
    *,
    symbol_hint: str = "",
) -> MarketQuote | None:
    if not isinstance(record, dict):
        return None

    current = read_toman_value(
        record,
        toman_keys=(
            "close_toman",
            "price_toman",
            "last_toman",
            "value_toman",
            "close.toman",
            "price.toman",
            "last.toman",
            "value.toman",
            "toman",
        ),
        rial_keys=(
            "close_rial",
            "price_rial",
            "last_rial",
            "value_rial",
            "close.rial",
            "price.rial",
            "last.rial",
            "value.rial",
            "rial",
        ),
        generic_keys=("close", "price", "last", "value"),
    )
    if current is None:
        return None

    high = read_toman_value(
        record,
        toman_keys=("high_toman", "day_high_toman", "high.toman", "day_high.toman"),
        rial_keys=("high_rial", "day_high_rial", "high.rial", "day_high.rial"),
        generic_keys=("high", "day_high", "max"),
    )
    low = read_toman_value(
        record,
        toman_keys=("low_toman", "day_low_toman", "low.toman", "day_low.toman"),
        rial_keys=("low_rial", "day_low_rial", "low.rial", "day_low.rial"),
        generic_keys=("low", "day_low", "min"),
    )
    opening = read_toman_value(
        record,
        toman_keys=("open_toman", "day_open_toman", "open.toman", "day_open.toman"),
        rial_keys=("open_rial", "day_open_rial", "open.rial", "day_open.rial"),
        generic_keys=("open", "day_open"),
    )
    change = read_toman_value(
        record,
        toman_keys=("change_toman", "day_change_toman", "change.toman"),
        rial_keys=("change_rial", "day_change_rial", "change.rial"),
        generic_keys=("change", "day_change"),
    )
    change_percent = first_decimal(
        record,
        (
            "change_percent",
            "change_pct",
            "percent_change",
            "change_percentage",
            "day_change_percent",
            "day_change_pct",
        ),
    )

    symbol = first_string(record, ("symbol", "code", "ticker", "slug")) or symbol_hint
    updated_at = first_string(
        record,
        (
            "updated_at",
            "last_update",
            "datetime",
            "date",
            "timestamp",
        ),
    )

    return MarketQuote(
        symbol=str(symbol or ""),
        current=current,
        open=opening,
        high=high,
        low=low,
        change=change,
        change_percent=change_percent,
        updated_at=updated_at,
    )


def read_toman_value(
    record: dict[str, Any],
    *,
    toman_keys: tuple[str, ...],
    rial_keys: tuple[str, ...],
    generic_keys: tuple[str, ...],
) -> Decimal | None:
    value = first_decimal(record, toman_keys)
    if value is not None:
        return value

    value = first_decimal(record, rial_keys)
    if value is not None:
        return value / Decimal("10")

    value = first_decimal(record, generic_keys)
    if value is None:
        return None

    unit = (
        first_string(record, ("unit", "currency", "quote_currency", "price_unit")) or ""
    ).lower()
    if "rial" in unit or unit == "irr" or "ریال" in unit:
        return value / Decimal("10")

    return value


def first_decimal(record: dict[str, Any], keys: tuple[str, ...]) -> Decimal | None:
    for key in keys:
        value = nested_get(record, key)
        converted = _to_decimal(value)
        if converted is not None:
            return converted
    return None


def first_string(record: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = nested_get(record, key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, (int, float)) and key in {"symbol", "code", "id"}:
            return str(value)
    return None


def nested_get(record: dict[str, Any], path: str) -> Any:
    value: Any = record
    for part in path.split("."):
        if not isinstance(value, dict):
            return None
        if part in value:
            value = value[part]
            continue

        lowered = {str(key).lower(): key for key in value}
        original_key = lowered.get(part.lower())
        if original_key is None:
            return None
        value = value[original_key]
    return value


def record_identity(record: dict[str, Any], path: str) -> str:
    parts = [path]
    for key in ("symbol", "code", "ticker", "slug", "name", "title", "name_fa", "name_en"):
        value = record.get(key)
        if isinstance(value, (str, int, float)):
            parts.append(str(value))
    return " ".join(parts)


def match_score(identity: str, asset: AssetSpec) -> int:
    normalized = _identity_normalize(identity)
    if not normalized:
        return 0

    score = 0
    code = _identity_normalize(asset.code)
    if re.search(rf"(?:^|\s){re.escape(code)}(?:$|\s)", normalized):
        score += 100

    for term in asset.lookup_terms:
        normalized_term = _identity_normalize(term)
        if not normalized_term:
            continue
        if normalized_term == normalized:
            score += 80
        elif re.search(
            rf"(?:^|\s){re.escape(normalized_term)}(?:$|\s)",
            normalized,
        ):
            score += 50
        elif normalized_term in normalized:
            score += 20

    return score


def _identity_normalize(value: str) -> str:
    value = normalize_text(value)
    value = re.sub(r"[_/\-.]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _to_decimal(value: Any) -> Decimal | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    if isinstance(value, str):
        cleaned = value.translate(
            str.maketrans(
                "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩",
                "01234567890123456789",
            )
        )
        cleaned = cleaned.replace(",", "").replace("٬", "").replace("٫", ".")
        cleaned = re.sub(r"[^\d.\-+]", "", cleaned)
        if not cleaned or cleaned in {"-", "+", ".", "-.", "+."}:
            return None
        try:
            return Decimal(cleaned)
        except InvalidOperation:
            return None
    return None
