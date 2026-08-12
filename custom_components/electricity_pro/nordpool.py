"""Nord Pool forecast normalization helpers."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from homeassistant.util import dt as dt_util

from .forecast import ForecastInterval

_MWH_TO_KWH = Decimal("0.001")


def normalize_nordpool_forecast_intervals(
    area: str,
    intervals: list[dict[str, str | int | float]],
    currency: str,
    published_at: datetime | None = None,
) -> list[ForecastInterval]:
    """Normalize Nord Pool action response intervals into forecast intervals."""
    if not area:
        raise ValueError("Nord Pool area is required")

    if not currency:
        raise ValueError("Nord Pool currency is required")

    normalized: list[ForecastInterval] = []

    for interval in intervals:
        start_raw = interval.get("start")
        end_raw = interval.get("end")
        price_raw = interval.get("price")

        if not isinstance(start_raw, str) or not isinstance(end_raw, str):
            raise ValueError("Nord Pool intervals must include string start and end")

        if not isinstance(price_raw, int | float):
            raise ValueError("Nord Pool intervals must include numeric price")

        start = dt_util.parse_datetime(start_raw)
        end = dt_util.parse_datetime(end_raw)

        if start is None or end is None:
            raise ValueError("Nord Pool intervals must include valid ISO datetimes")

        normalized.append(
            ForecastInterval(
                start=start,
                end=end,
                market_price=Decimal(str(price_raw)) * _MWH_TO_KWH,
                currency=currency,
                area=area,
                published_at=published_at,
            )
        )

    return normalized
