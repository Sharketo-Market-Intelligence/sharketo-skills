"""Synthetic full-asset fixture; public SDK only, no credentials or network."""

from __future__ import annotations

import httpx

from sharketo import SharketoClient


def synthetic_asset(*, available: bool = True) -> dict:
    stats = {"meanPercent": 0, "hitRatePercent": 50, "tStatistic": None, "sampleSize": 2}
    comparison = {
        "target": dict(stats),
        "rest": dict(stats),
        "differenceTStatistic": None,
        "differencePValue": None,
    }
    labels = [
        "Jan 02",
        "Jan 03",
        "Jan 06",
        "Jan 07",
        "Jan 08",
        "Jan 09",
        "Jan 10",
        "Jan 13",
        "Jan 14",
        "Jan 15",
        "Jan 16",
        "Jan 17",
        "Jan 20",
        "Jan 21",
        "Jan 22",
        "Jan 23",
        "Jan 24",
        "Jan 27",
        "Jan 28",
        "Jan 29",
    ]
    nullable = [0, None] + [None] * 18
    analysis = {
        "years": {"first": 2023, "last": 2024, "sampleSize": 2},
        "sharpeRatio": None,
        "significantDaysPercent": 0,
        "tradesWeekends": False,
        "curve": {
            "labels": labels,
            "meanPercent": nullable.copy(),
            "geometricMeanPercent": nullable.copy(),
            "confidenceLowPercent": [-1] + [None] * 19,
            "confidenceHighPercent": [1] + [None] * 19,
            "envelopeLow": nullable.copy(),
            "envelopeHigh": [1] + [None] * 19,
            "envelopeMean": [0.5] + [None] * 19,
            "significant": [False] * 20,
        },
        "current": {"year": 2025, "valuesPercent": [0] * 20, "tradingDayCount": 20},
        "conformity": {
            "correlation": 0,
            "percentile": 0,
            "windowTradingDays": 20,
            "history": [[2023, None], [2024, 0]],
        },
        "monthly": {
            "years": [2023, 2024, 2025],
            "returnsPercent": [[0, None] + [None] * 10 for _ in range(3)],
            "stats": [
                {
                    **stats,
                    "adjustedPValue": None,
                    "firstHalfMeanPercent": 0,
                    "secondHalfMeanPercent": None,
                }
                for _ in range(12)
            ],
        },
        "turnOfMonth": {
            "days": [-5, -4, -3, -2, -1, 1, 2, 3, 4],
            "meanPercent": [0] * 9,
            "hitRatePercent": [50] * 9,
            "tStatistic": [None] * 9,
            "window": dict(stats),
            "rest": dict(stats),
            "differenceTStatistic": None,
            "differencePValue": None,
        },
        "optionsExpiration": comparison,
        "preHoliday": {
            **comparison,
            "target": dict(stats),
            "rest": dict(stats),
        },
        "halloween": {
            "years": [[2023, 0, None], [2024, None, 0], [2025, 0, None]],
            "winter": dict(stats),
            "summer": dict(stats),
            "differenceTStatistic": None,
            "differencePValue": None,
            "winterOutperformanceRatePercent": 0,
        },
        "fomc": {
            "days": list(range(-6, 34)),
            "averagePercent": [0] * 40,
            "cumulativePercent": [-200] + [0] * 39,
            "evenWeeks": dict(stats),
            "oddWeeks": dict(stats),
            "differenceTStatistic": None,
            "differencePValue": None,
            "dayBefore": dict(stats),
            "dayOf": dict(stats),
            "dayAfter": dict(stats),
            "allDaysMeanPercent": 0,
            "meetingCount": 2,
        },
        "election": {
            "sampleSizes": [1, 0, 1, 0],
            "curvesPercent": [nullable.copy() for _ in range(4)],
        },
    }
    return {
        "schemaVersion": "seasonality-asset.v2",
        "id": "synthetic",
        "ticker": "SYNTH",
        "name": "Synthetic asset",
        "group": "Synthetic",
        "available": available,
        "asOf": "2025-01-30" if available else None,
        "asOfSemantics": "analyzedSourceDate",
        "perAssetFreshness": "unknown",
        "unavailableReason": None if available else "analysisFailed",
        "analysis": analysis if available else None,
    }


def run_fixture() -> None:
    calls = []
    payload = synthetic_asset()

    def respond(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        assert request.url.path == "/v1/developer/seasonality/assets/synthetic"
        assert not request.url.query
        return httpx.Response(200, json=payload)

    with SharketoClient(
        "sk-shark-synthetic-not-a-secret",
        "http://localhost",
        max_retries=0,
        transport=httpx.MockTransport(respond),
    ) as client:
        result = client.seasonality.get_asset("synthetic")
    assert len(calls) == 1
    assert result.as_of == "2025-01-30" and result.per_asset_freshness == "unknown"
    a = result.analysis
    assert a is not None
    assert a.curve.mean_percent[:2] == (0, None)
    assert a.curve.envelope_mean[:2] == (0.5, None)
    assert a.monthly.returns_percent[0][:2] == (0, None)
    assert a.halloween.years[0] == (2023, 0, None)
    assert a.fomc.cumulative_percent[0] == -200
    assert result.model_dump(mode="json", by_alias=True) == payload


if __name__ == "__main__":
    run_fixture()
