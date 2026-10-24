import asyncio

import httpx

from sharketo import (
    AsyncSharketoClient,
    RrgCatalogV1,
    RrgGroupV2,
    RrgScreenerV2,
    SharketoClient,
)

benchmark = {"ticker": "SPY", "name": "S&P 500"}
frame = {
    "quadrant": None,
    "ratio": None,
    "momentum": None,
    "headingDegrees": None,
    "velocity": None,
    "distance": None,
    "barsInQuadrant": 0,
}
scores = dict.fromkeys(
    [
        "momentum12Minus1MonthPercent",
        "momentum1MonthPercent",
        "relativeStrengthTStatistic",
        "volatilityAdjustedMomentumPercent",
        "return12MonthPercent",
        "volatility6MonthPercent",
        "distanceFrom52WeekHighPercent",
    ]
)
scores["momentum1MonthPercent"] = 0.0
bucket = {"meanRelativeReturnPercentagePoints": None, "hitRatePercent": None, "sampleSize": 0}
statistics = {
    "quadrants": ["leading", "weakening", "lagging", "improving"],
    "transition": {"counts": [[0, 0, 0, 0] for _ in range(4)], "sampleSize": 0},
    "medianHoldingWeeks": [None] * 4,
    "forwardReturns": {
        "horizonTradingDays": 21,
        "all": [bucket.copy() for _ in range(4)],
        "northeast": [bucket.copy() for _ in range(4)],
    },
}
members = [
    {
        "ticker": ticker,
        "name": name,
        "available": False,
        "unavailableReason": "analysisFailed",
        "analysis": None,
    }
    for ticker, name in [
        ("VLUE", "Value"),
        ("MTUM", "Momentum"),
        ("QUAL", "Quality"),
        ("USMV", "Min Volatility"),
        ("VB", "Size (Small)"),
        ("VUG", "Growth"),
    ]
]
members[0].update(
    available=True,
    unavailableReason=None,
    analysis={
        "daily": {"ratio": [None], "momentum": [None]},
        "weekly": {"ratio": [None], "momentum": [None]},
        "state": {"daily": frame.copy(), "weekly": frame.copy(), "hook": None},
        "scores": scores,
    },
)
for member, (quadrant, ratio, momentum, distance) in zip(
    members[2:5],
    [
        ("lagging", 99.5, 100.0, 0.5),
        ("weakening", 100.5, 100.0, 0.5),
        ("improving", 100.0, 100.5, 0.5),
    ],
    strict=True,
):
    rounded_frame = frame | {
        "quadrant": quadrant,
        "ratio": ratio,
        "momentum": momentum,
        "distance": distance,
        "barsInQuadrant": 1,
    }
    member.update(
        available=True,
        unavailableReason=None,
        analysis={
            "daily": {"ratio": [ratio], "momentum": [momentum]},
            "weekly": {"ratio": [ratio], "momentum": [momentum]},
            "state": {"daily": rounded_frame.copy(), "weekly": rounded_frame.copy(), "hook": None},
            "scores": scores,
        },
    )
catalog = {
    "schemaVersion": "rrg-catalog.v1",
    "asOf": "2026-01-30",
    "asOfSemantics": "maximumAnalyzedSourceDate",
    "freshness": "unknown",
    "groups": [
        {
            "id": "factors",
            "name": "Equity Factors",
            "benchmark": benchmark,
            "memberCount": 6,
            "available": True,
        },
    ],
}
group = {
    "schemaVersion": "rrg-group.v2",
    "id": "factors",
    "name": "Equity Factors",
    "benchmark": benchmark,
    "asOf": "2026-01-30",
    "asOfSemantics": "analyzedSourceDate",
    "freshness": "unknown",
    "available": True,
    "unavailableReason": None,
    "analysis": {
        "parameters": {
            "fastWindowBars": 12,
            "slowWindowBars": 26,
            "momentumWindowBars": 4,
            "normalizationWindowBars": 104,
        },
        "regime": {"level": "none", "belowLongTermAverage": False, "volatilityPercentile": None},
        "dailyDates": ["2026-01-30"],
        "weeklyDates": ["2026-01-30"],
        "members": members,
        "statistics": statistics,
    },
}
screener = {
    "schemaVersion": "rrg-screener.v2",
    "id": "screener",
    "asOf": None,
    "asOfSemantics": "analyzedSourceDate",
    "freshness": "unknown",
    "available": False,
    "unavailableReason": "analysisFailed",
    "analysis": None,
}
paths = [
    "/v1/developer/rrg/catalog",
    "/v1/developer/rrg/groups/factors",
    "/v1/developer/rrg/screener",
]
payloads = dict(zip(paths, [catalog, group, screener], strict=True))
calls = []


def respond(request):
    assert request.method == "GET" and not request.url.query
    calls.append(request.url.path)
    return httpx.Response(200, json=payloads[request.url.path])


def rotation_point(state):
    return {"x": state.ratio, "y": state.momentum, "quadrant": state.quadrant}


def inspect(results):
    for result, root, path in zip(
        results, (RrgCatalogV1, RrgGroupV2, RrgScreenerV2), paths, strict=True
    ):
        assert isinstance(result, root)
        assert result.model_dump(mode="json", by_alias=True) == payloads[path]
    catalog_result, group_result, screener_result = results
    member = group_result.analysis.members[0]
    assert member.analysis.scores.momentum1_month_percent == 0.0
    assert member.analysis.weekly.ratio[-1] is None  # no carry-forward or invented zero
    assert rotation_point(member.analysis.state.weekly) == {"x": None, "y": None, "quadrant": None}
    for timeframe in ("daily", "weekly"):
        points = [
            rotation_point(getattr(item.analysis.state, timeframe))
            for item in group_result.analysis.members[2:5]
        ]
        assert points == [
            {"x": 99.5, "y": 100.0, "quadrant": "lagging"},
            {"x": 100.5, "y": 100.0, "quadrant": "weakening"},
            {"x": 100.0, "y": 100.5, "quadrant": "improving"},
        ]
    assert group_result.analysis.members[1].unavailable_reason == "analysisFailed"
    assert screener_result.as_of is None and screener_result.analysis is None
    print("VLUE | 1m percent=0.0 | latest ratio=unknown | source=2026-01-30")
    print("MTUM | analysisFailed; screener | analysisFailed | source=unknown")


with SharketoClient(
    "sk-shark-synthetic-only",
    "http://localhost",
    transport=httpx.MockTransport(respond),
    max_retries=0,
    max_response_bytes=8_388_608,
) as client:
    inspect((client.rrg.get_catalog(), client.rrg.get_group("factors"), client.rrg.get_screener()))


async def run():
    async with AsyncSharketoClient(
        "sk-shark-synthetic-only",
        "http://localhost",
        transport=httpx.MockTransport(respond),
        max_retries=0,
        max_response_bytes=8_388_608,
    ) as client:
        inspect(
            (
                await client.rrg.get_catalog(),
                await client.rrg.get_group("factors"),
                await client.rrg.get_screener(),
            )
        )


asyncio.run(run())
assert calls == paths * 2
