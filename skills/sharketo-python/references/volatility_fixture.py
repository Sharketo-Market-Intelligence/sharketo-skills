import asyncio

import httpx
from pydantic import ValidationError

from sharketo import (
    AsyncSharketoClient,
    SharketoClient,
    VolatilityAssetV2,
    VolatilityCatalogV2,
    VolatilityTermStructureV1,
)

_CURATED = [
    (
        "us-indices",
        "US Indices",
        [
            ("ES", "S&P 500 E-mini", "VIX"),
            ("NQ", "NASDAQ 100 E-mini", "VXN"),
            ("YM", "DJIA Mini", "VXD"),
            ("RTY", "Russell 2000 Mini", "RVX"),
        ],
    ),
    (
        "mag7",
        "Mag7",
        [
            ("AAPL", "Apple", "VXAPL"),
            ("MSFT", "Microsoft", None),
            ("AMZN", "Amazon", "VXAZN"),
            ("GOOGL", "Alphabet", "VXGOG"),
            ("META", "Meta Platforms", None),
            ("NVDA", "NVIDIA", None),
            ("TSLA", "Tesla", None),
        ],
    ),
    (
        "sectors",
        "S&P 500 Sectors",
        [
            ("XLE", "Energy", None),
            ("XLF", "Financials", None),
            ("XLU", "Utilities", None),
            ("XLI", "Industrials", None),
            ("XLP", "Consumer Staples", None),
            ("XLV", "Health Care", None),
            ("XLY", "Consumer Discretionary", None),
            ("XLK", "Technology", None),
            ("XLB", "Materials", None),
            ("XLC", "Communication Services", None),
            ("XLRE", "Real Estate", None),
        ],
    ),
    (
        "currencies",
        "Currencies",
        [
            ("EURUSD", "EUR/USD", None),
            ("USDJPY", "USD/JPY", None),
            ("GBPUSD", "GBP/USD", None),
            ("AUDUSD", "AUD/USD", None),
            ("USDCAD", "USD/CAD", None),
            ("USDCHF", "USD/CHF", None),
        ],
    ),
    (
        "rates",
        "Rates & Bonds",
        [
            ("ZT", "US 2-Year T-Note", None),
            ("ZF", "US 5-Year T-Note", None),
            ("ZN", "US 10-Year T-Note", None),
            ("TLT", "20y+ Treasury ETF", "VXTLT"),
        ],
    ),
    (
        "commodities",
        "Commodities",
        [
            ("CL", "Crude Oil", "OVX"),
            ("RB", "RBOB Gasoline", None),
            ("HO", "Heating Oil", None),
            ("NG", "Natural Gas", None),
            ("GC", "Gold", "GVZ"),
            ("SI", "Silver", None),
            ("HG", "Copper", None),
            ("HE", "Lean Hogs", None),
            ("LE", "Live Cattle", None),
            ("ZC", "Corn", None),
            ("ZW", "Wheat", None),
            ("CT", "Cotton #2", None),
            ("ZS", "Soybeans", None),
            ("ZL", "Soybean Oil", None),
            ("SB", "Sugar #11", None),
            ("KC", "Coffee", None),
            ("CC", "Cocoa", None),
        ],
    ),
    (
        "crypto",
        "Crypto",
        [
            ("BTCUSD", "Bitcoin", None),
            ("ETHUSD", "Ethereum", None),
            ("SOLUSD", "Solana", None),
        ],
    ),
]


def synthetic_payloads() -> dict[str, dict]:
    header = {
        "generatedOn": "2025-01-03",
        "generationDateSemantics": "generationDate",
        "freshness": "unknown",
    }
    catalog = {
        **header,
        "schemaVersion": "volatility-catalog.v2",
        "classes": [
            {
                "id": class_id,
                "name": name,
                "memberCount": len(members),
                "availableMemberCount": 1 if class_id == "mag7" else 0,
                "assets": [
                    {"assetId": ticker, "ticker": ticker, "name": member_name, "ivSymbol": iv}
                    for ticker, member_name, iv in members
                ],
            }
            for class_id, name, members in _CURATED
        ],
    }
    asset = {
        **header,
        "schemaVersion": "volatility-asset.v2",
        "assetId": "AAPL",
        "ticker": "AAPL",
        "name": "Apple",
        "classId": "mag7",
        "className": "Mag7",
        "asOf": "2025-01-02",
        "asOfSemantics": "analyzedSourceDate",
        "available": True,
        "unavailableReason": None,
        "analysis": {
            "spot": 100.0,
            "cone": [
                {
                    "window": 5,
                    "min": 0.0,
                    "p05": 0.1,
                    "p25": 0.15,
                    "p50": 0.2,
                    "p75": 0.25,
                    "p95": 0.3,
                    "max": 0.4,
                    "current": 0.2,
                    "currentPct": 50.0,
                    "samples": 100,
                }
            ],
            "estimators": {
                "closeToClose": 0.19,
                "highLowRange": 0.18,
                "openHighLowClose": 0.17,
                "openCloseRange": 0.16,
                "overnightAdjusted": 0.2,
                "overnightShare": 0.2,
            },
            "rvSeries": {
                "dates": ["2025-01-01", "2025-01-02"],
                "rv21": [0.0, 0.2],
                "rv63": [None, None],
            },
            "signals": {
                "rv10": 0.0,
                "rv21": 0.2,
                "rv63": None,
                "rv252": None,
                "rv21Change1w": -0.02,
                "rvPct3y": 40.0,
                "rvPct1y": 50.0,
                "regime": "normal",
                "vratio": None,
                "volOfVol": 0.3,
                "leverageCorr": -0.4,
                "acf1Abs": 0.2,
                "persistence": 1.2,
                "expectedMoves": [],
                "straddle21dPct": 0.04,
                "volTargetExposure": 0.75,
                "vrp": {
                    "ivSymbol": "VXAPL",
                    "iv": 25.0,
                    "spread": 5.0,
                    "spreadVar": 225.0,
                    "pct1y": 70.0,
                    "pct5y": 60.0,
                },
            },
            "forecast": {"adaptive": 0.21, "forecast21d": None, "fitScore": None},
        },
    }
    failed_asset = {
        **asset,
        "assetId": "MSFT",
        "ticker": "MSFT",
        "name": "Microsoft",
        "available": False,
        "unavailableReason": "analysisFailed",
        "asOf": None,
        "analysis": None,
    }
    term = {
        **header,
        "schemaVersion": "volatility-term-structure.v1",
        "available": False,
        "analysis": {
            "curveToday": [{"label": "VIX", "days": 30.0, "value": 20.0}],
            "curve1w": [],
            "curve1m": [],
            "ratioSeries": [],
            "ratioToday": None,
            "ratioPctFull": None,
            "ratioPct1y": None,
            "slopeToday": None,
            "vxCurve": [{"expiry": "2025-01-20", "dte": 17.0, "price": 21.0, "basis": 1.0}],
            "frontBasisPctOfSpot": 0.05,
            "frontBasisPercentile": 60.0,
            "rollYieldAnn": 1.0735,
            "basisSeries": [["2025-01-02", 0.05]],
            "conditional": [{"label": "Q2", "n": 2, "meanFwdPp": 0.2, "hit": 0.5}],
            "basisPointsSeries": [["2025-01-02", 1.0]],
            "f2f1Series": [["2025-01-02", -0.2]],
            "curveState": "watch",
            "curveStates": [
                {"state": "normal", "daysPct": 80.0, "n": 2, "meanFwdPp": 1.0, "hit": 1.0},
                {"state": "watch", "daysPct": 20.0, "n": 0, "meanFwdPp": None, "hit": None},
                {"state": "stress", "daysPct": 0.0, "n": 0, "meanFwdPp": None, "hit": None},
            ],
        },
    }
    return {
        "/v1/developer/volatility/catalog": catalog,
        "/v1/developer/volatility/assets/AAPL": asset,
        "/v1/developer/volatility/assets/MSFT": failed_asset,
        "/v1/developer/volatility/term-structure": term,
    }


payloads = synthetic_payloads()
paths = list(payloads)
calls = []


def respond(request):
    assert request.method == "GET" and not request.url.query
    calls.append(request.url.path)
    return httpx.Response(200, json=payloads[request.url.path])


def inspect(results):
    for result, expected_type, path in zip(
        results,
        (VolatilityCatalogV2, VolatilityAssetV2, VolatilityAssetV2, VolatilityTermStructureV1),
        paths,
        strict=True,
    ):
        assert isinstance(result, expected_type)
        assert result.model_dump(mode="json", by_alias=True) == payloads[path]
    catalog, asset, failed, term = results
    assert isinstance(catalog.classes[0].assets, tuple)
    assert asset.as_of == "2025-01-02" != asset.generated_on
    assert asset.analysis.rv_series.rv21[0] == 0.0
    assert asset.analysis.rv_series.rv63[-1] is None
    assert asset.analysis.signals.vrp.iv == 25.0
    assert asset.analysis.forecast.forecast21d is None
    assert failed.analysis is None and failed.unavailable_reason == "analysisFailed"
    assert not term.available and term.analysis.ratio_today is None
    assert term.analysis.basis_series == (("2025-01-02", 0.05),)
    assert term.analysis.conditional[0].hit == 0.5
    try:
        asset.analysis.signals.vrp.iv = 0.0
    except ValidationError:
        pass
    else:
        raise AssertionError("Nested record must be frozen")
    print("AAPL RV=0.2 decimal; IV=25.0 vol points; underlying source=2025-01-02")
    print("MSFT analysisFailed; partial term basis=0.05 fraction; hit=0.5 fraction")


with SharketoClient(
    "sk-shark-synthetic-only",
    "http://localhost",
    transport=httpx.MockTransport(respond),
    max_retries=0,
    max_response_bytes=8_388_608,
) as client:
    inspect(
        (
            client.volatility.get_catalog(),
            client.volatility.get_asset("AAPL"),
            client.volatility.get_asset("MSFT"),
            client.volatility.get_term_structure(),
        )
    )


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
                await client.volatility.get_catalog(),
                await client.volatility.get_asset("AAPL"),
                await client.volatility.get_asset("MSFT"),
                await client.volatility.get_term_structure(),
            )
        )


asyncio.run(run())
assert calls == paths * 2
