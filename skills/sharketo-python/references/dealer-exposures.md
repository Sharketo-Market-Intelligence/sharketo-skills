# Dealer Exposures, SDK 0.1.14b4

For client reuse and repeated reads, see [application integration](integration.md#http-reads).

## Public boundary

Both clients expose `client.dealer_exposures.get_snapshot("SPX")`. Await the call on
`AsyncSharketoClient`. It returns the root-exported, deeply frozen
`DealerExposuresSnapshotV2`. The `by_strike`, `by_expiration`,
`quality.available_expirations` and `quality.warnings` collections are tuples.
Python attributes are snake_case. `model_dump(mode="json", by_alias=True)` preserves
wire names and values.

Before I/O, the SDK trims the ticker and uppercases its ASCII characters. It accepts SPX,
NDX, SPY and QQQ and checks that the response identity matches. The request is one GET
to `/v1/developer/dealer-exposures/{ticker}/snapshot`, with no query, catalog preflight
or inventory `get_access()` preflight.

Only snapshots with model ID `dealer_exposures.standard_v1`, version `v4`, mode
`standard`, window `ALL` and source schema `dealer_exposures.v1` are supported.
Preserve the explicit `model.iv_routing_mode` value, `standard` or `contractAware`. It is a model assumption,
not an inference about current configuration. `standard` assumes European exercise even
for contracts that permit early exercise. This limitation matters for ETF options.
`contractAware` uses the inferred contract exercise style. Neither mode rates quality
or freshness.

Reads return existing snapshots without triggering a refresh.

## Interpretation that must survive rendering

- `totals.{call,put,net}.{gamma,delta}.{by_open_interest,by_volume}`, strike breakdowns
  and expiration breakdowns are independent authoritative server values. Do not force net
  to a sum, reconstruct totals or equate the two bases.
- Gamma and delta are already-scaled server exposure measures with units
  `usdGammaSpotSquared` and `usdDeltaSpot`, respectively. They already incorporate model
  signs, contract size, and OI or volume. Preserve the raw units. Do not multiply by positions
  or rescale the financial values. These measures are not interchangeable with inventory-family
  exposures. Prices and key levels use underlying quote units, index points or ETF USD per share.
- Preserve finite signed metrics and valid zero. Null spot, reference and any of the five
  key levels mean unknown. Never fill them with zero. Missing original OI or volume may
  already have been normalized to zero. Counts and zeros do not establish completeness.
- Keep `generated_at`, chain-fetch `data_timestamp`, quote `spot.as_of`, cache deadlines,
  cached session and local receipt time distinct. Chain and spot clocks can follow generation.
  Preserve `source_freshness="unknown"` even when cache state is `fresh`. Do not reclassify
  it using the local wall clock or session. Preserve `stale` and `closed`, including elapsed deadlines
  and nullable next-refresh values. The cache etag is opaque. It is not a digest to recalculate
  or a conditional-GET contract.
- `by_expiration[].settlement` can be AM, PM or null. It is a grouping and display label,
  not authoritative exercise style or settlement time. ETF roots can be AM, and NDXP can
  be null. Preserve same-date rows separately and never derive clocks from labels.
  `quality.available_expirations[].settles_at` is the last recorded settlement on a date,
  not proof that every individual series remains unsettled.
- Preserve quality counts, categories, `has0_dte`, warnings, spot fallback and source,
  and all cached session metadata. Warnings are data, not a freshness classifier.
- Do not substitute an unavailable=false, null or empty snapshot for an unavailable artifact.
  Sanitized 503 responses distinguish
  `DEALER_EXPOSURES_MISSING/CORRUPT/INCOMPATIBLE/EXPIRED/SESSION_INVALID/STALE/OVERSIZED`.
  Each code has the full `DEALER_EXPOSURES_` prefix. Dependency failures use
  `DEPENDENCY_UNAVAILABLE`. There is no data-availability Retry-After promise.
  Fail closed on protocol violations or exceeded bounds. Never sort, merge, deduplicate
  or crop an invalid snapshot to repair it. Display ordering does not alter validated data.
  The limits are 1 to 1,000 strikes, 1 to 256 expiration and settlement rows, 1 to 128
  available dates and at most 32 warnings. The complete HTTP body is limited to 1 MiB
  by default.

Access requires effective Apex access through `developer_api`, an existing server-side
developer key, verified email, `api_keys` and `dealer_exposures.full`. A shared-account budget of 60 requests per minute applies.
Every response is no-store. Use
[client configuration](integration.md#endpoints-and-environment-configuration) for documented
production defaults and custom endpoints.

## Offline validation fixture, standalone installed synthetic data

```python
import asyncio
import httpx
from sharketo import AsyncSharketoClient, DealerExposuresSnapshotV2, SharketoClient

metrics = {
    "gamma": {"byOpenInterest": -25.0, "byVolume": 0.0},
    "delta": {"byOpenInterest": 0.0, "byVolume": 12.0},
}
totals = {"call": metrics, "put": metrics, "net": metrics}
levels = {
    "gammaFlip": None,
    "callWall": 0.0,
    "putWall": 4900.0,
    "positiveGammaPeak": None,
    "negativeGammaTrough": 4950.0,
}
payload = {
    "schemaVersion": "dealer-exposures-snapshot.v2",
    "sourceSchemaVersion": "dealer_exposures.v1",
    "ticker": "SPX",
    "model": {
        "id": "dealer_exposures.standard_v1",
        "version": "v4",
        "mode": "standard",
        "ivRoutingMode": "contractAware",
    },
    "window": "ALL",
    "units": {
        "gamma": "usdGammaSpotSquared",
        "delta": "usdDeltaSpot",
        "prices": "underlyingPrice",
    },
    "generatedAt": "2026-05-01T14:00:00Z",
    "dataTimestamp": "2026-05-01T14:01:00Z",
    "sourceFreshness": "unknown",
    "cache": {
        "etag": "synthetic-only",
        "freshUntil": "2026-05-01T14:05:00Z",
        "staleUntil": "2026-05-01T14:29:00Z",
        "nextRefreshAt": "2026-05-01T14:05:00Z",
        "state": "fresh",
    },
    "spot": {
        "price": None,
        "asOf": "2026-05-01T14:02:00Z",
        "source": "option_chain",
        "fallbackUsed": True,
        "referencePrice": 0.0,
    },
    "marketSession": {
        "market": "open",
        "sessionDate": "2026-05-01",
        "nextMarketDate": "2026-05-04",
        "isOpenDay": True,
        "isRefreshWindow": True,
        "nextOpen": "2026-05-01T13:30:00Z",
        "nextClose": "2026-05-01T20:00:00Z",
    },
    "quality": {
        "contractsTotal": 12,
        "contractsUsed": 10,
        "contractsSkipped": 2,
        "expirationsTotal": 1,
        "has0Dte": False,
        "warnings": ["Synthetic coverage unknown"],
        "availableExpirations": [
            {
                "expiration": "2026-05-08",
                "expirationCategory": "WEEKLY",
                "contractsCount": 12,
                "settlesAt": "2026-05-08T20:00:00Z",
            }
        ],
    },
    "totals": totals,
    "byStrike": [{"strike": 5000.0, **totals}],
    "byExpiration": [
        {
            "expiration": "2026-05-08",
            "settlement": None,
            "expirationCategory": "WEEKLY",
            "contractsCount": 10,
            "totals": totals,
        }
    ],
    "keyLevels": {"byOpenInterest": levels, "byVolume": levels},
}
calls = []


def respond(request):
    assert request.method == "GET" and not request.url.query
    assert request.url.path == "/v1/developer/dealer-exposures/SPX/snapshot"
    calls.append(request.url.path)
    return httpx.Response(200, json=payload)


def inspect(snapshot):
    assert isinstance(snapshot, DealerExposuresSnapshotV2)
    assert snapshot.model_dump(mode="json", by_alias=True) == payload
    assert isinstance(snapshot.by_strike, tuple)
    assert snapshot.totals.net.gamma.by_open_interest == -25.0
    assert snapshot.totals.call.gamma.by_volume == 0.0
    assert snapshot.spot.price is None and snapshot.spot.reference_price == 0.0
    assert snapshot.by_expiration[0].settlement is None
    assert snapshot.quality.warnings == ("Synthetic coverage unknown",)
    print("SPX: gamma OI=-25, volume=0; spot unknown; source freshness unknown")


with SharketoClient(
    "sk-shark-synthetic-only",
    "http://localhost",
    transport=httpx.MockTransport(respond),
    max_retries=0,
) as client:
    inspect(client.dealer_exposures.get_snapshot(" spx "))


async def run():
    async with AsyncSharketoClient(
        "sk-shark-synthetic-only",
        "http://localhost",
        transport=httpx.MockTransport(respond),
        max_retries=0,
    ) as client:
        inspect(await client.dealer_exposures.get_snapshot("SPX"))


asyncio.run(run())
assert calls == ["/v1/developer/dealer-exposures/SPX/snapshot"] * 2
```

For separately approved agent-run live validation, follow the
[validation workflow](workflow.md).
