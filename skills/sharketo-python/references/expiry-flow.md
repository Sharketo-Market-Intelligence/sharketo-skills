# Expiry flow, SDK 0.1.14b2

For client reuse and repeated reads, see [application integration](integration.md#http-reads).

## Public boundary

- Both clients expose `index_inventory.get_expiry_flow_latest(ticker)`, which returns the root-exported `IndexInventoryExpiryFlowLatestV1`, and `index_inventory.get_expiry_flow_series(ticker, *, root, expiration, start_date, end_date)`, which returns `IndexInventoryExpiryFlowSeriesV1`. Await either on `AsyncSharketoClient`. Canonical SPX permits SPX and SPXW roots; NDX permits NDX and NDXP. These methods read explicit HTTP snapshots. Do not preflight with catalog, summary or `get_access()` reads.
- Latest GET `/v1/developer/inventory/index/{ticker}/expiry-flow/latest` has no query. Series GET `/v1/developer/inventory/index/{ticker}/expiry-flow/series` requires exactly `root`, `expiration`, `startDate` and `endDate`. SDK date arguments are canonical YYYY-MM-DD strings in 1900..2100. The inclusive range may span at most 31 UTC calendar days. Buckets must be at or after UTC midnight on the start date and before UTC midnight after the end date. Do not reinterpret dates using local time or DST. Invalid selectors fail before I/O. Returned ticker, root, expiration and range must agree with the request.
- Models are deeply frozen, `rows` is a tuple, and fields use snake_case. `.model_dump(mode="json", by_alias=True)` preserves wire values. Latest returns at most 200 rows in strict order by expiration and root. Series returns at most 744 unique chronological whole-hour rows. There is no pagination, cropping or implicit history truncation. Backend encoded success responses are at most 262,144 bytes. Normal SDK HTTP bounds still apply.
- Latest selects expirations on or after `selection_date` in `time_zone="America/New_York"`, then the greatest persisted hour for each root and expiration. This is calendar eligibility, not proof that expirations are currently unsettled. A same-day cutoff may have passed. Latest `cutoff_timestamp_ms` is persisted metadata, not another selection filter. `settlement_style` is `am_cash` for SPX and NDX, and `pm_cash` for SPXW and NDXP.
- `hour_timestamp_ms` is Unix milliseconds exactly divisible by 3,600,000. It identifies a mutable last-write-wins bucket, not exact observation time, publication time or freshness. Latest rows can have different hours. Neither those rows nor independent endpoint reads form an atomic market snapshot. Sparse hours, single points and gaps are valid. Never fill gaps or infer a complete hourly record. Series `time_zone="UTC"` governs selection and is not a freshness clock.
- `gross_contracts` is standing gross positions, the sum of absolute call and put positions, not hourly traded volume. `institutional_contracts` is a cumulative expiration-life classifier count. It is nonnegative and within the signed-i64 range. `institutional_net_premium_usd` is finite signed cumulative expiration-life premium in USD. Positive values mean customer premium paid; negative values mean premium collected. Do not sum hourly snapshots as increments or infer causal changes or trades. Roll attribution applies per leg to the closed or opened expiration. Nearest-expiration package counts are not exposed.
- All three metrics are nonnullable and finite. Gross positions and classifier counts are nonnegative. Preserve valid zero and signed premium rather than inventing nulls or zero fallbacks. The SDK supplies no local classifiers or financial analytics. Do not present application comparisons or alerts as backend outputs.
- `availability="available"` means selected rows exist. `"empty"` means only that zero rows were selected. The reason for an empty result is unknown. You cannot distinguish never-recorded data, pruned data, data outside the selection or other absence. Neither empty nor available establishes source readiness, freshness or provider health. Source retention may prune old expirations.
- Access requires an API key, verified email and existing `ApiKeys`/`InventoryIndex` capabilities. The shared-account inventory budget of 60 requests per minute and existing key budgets apply. All outward responses are no-store. Service dependency or read failures, and corrupt identity, metrics, order or bounds return sanitized 503 `EXPIRY_FLOW_UNAVAILABLE`. A busy service may return `EXPIRY_FLOW_BUSY`. Existing typed errors for authentication, validation, entitlement, features and rate limits apply. Do not fabricate empty success responses. `get_access()` remains summary-only.

## Offline validation fixture, installed-only synthetic data

This fixture preserves zero, signed premium, sparse buckets and empty selections through both public clients.

```python
import asyncio
import httpx
from sharketo import (
    AsyncSharketoClient,
    IndexInventoryExpiryFlowLatestV1,
    IndexInventoryExpiryFlowSeriesV1,
    SharketoClient,
)

latest = {
    "schemaVersion": "index-inventory-expiry-flow-latest.v1",
    "ticker": "NDX",
    "selectionDate": "2026-09-18",
    "timeZone": "America/New_York",
    "availability": "empty",
    "rows": [],
}
series = {
    "schemaVersion": "index-inventory-expiry-flow-series.v1",
    "ticker": "NDX",
    "root": "NDXP",
    "expiration": "2026-09-18",
    "startDate": "2026-09-18",
    "endDate": "2026-09-18",
    "timeZone": "UTC",
    "availability": "available",
    "rows": [
        {
            "hourTimestampMs": 1789732800000,
            "grossContracts": 0.0,
            "institutionalContracts": 0,
            "institutionalNetPremiumUsd": 0.0,
        },
        {
            "hourTimestampMs": 1789747200000,
            "grossContracts": 12.5,
            "institutionalContracts": 2,
            "institutionalNetPremiumUsd": -30.0,
        },
    ],
}
calls = []


def respond(request):
    assert request.method == "GET"
    calls.append(request.url.path)
    if request.url.path.endswith("/latest"):
        assert not request.url.query
        return httpx.Response(200, json=latest)
    assert request.url.path == "/v1/developer/inventory/index/NDX/expiry-flow/series"
    assert sorted(request.url.params.multi_items()) == sorted(
        [
            ("root", "NDXP"),
            ("expiration", "2026-09-18"),
            ("startDate", "2026-09-18"),
            ("endDate", "2026-09-18"),
        ]
    )
    return httpx.Response(200, json=series)


def inspect(a, b):
    assert isinstance(a, IndexInventoryExpiryFlowLatestV1)
    assert isinstance(b, IndexInventoryExpiryFlowSeriesV1)
    assert a.model_dump(mode="json", by_alias=True) == latest
    assert b.model_dump(mode="json", by_alias=True) == series
    assert a.availability == "empty" and a.rows == ()
    assert isinstance(b.rows, tuple)
    assert b.rows[0].gross_contracts == 0.0
    assert b.rows[-1].institutional_net_premium_usd == -30.0
    print("Empty latest: reason unknown; history premium -30 USD collected; zero retained")


selection = dict(
    root="NDXP",
    expiration="2026-09-18",
    start_date="2026-09-18",
    end_date="2026-09-18",
)
with SharketoClient(
    "sk-shark-synthetic-only",
    "http://localhost",
    transport=httpx.MockTransport(respond),
    max_retries=0,
) as client:
    inspect(
        client.index_inventory.get_expiry_flow_latest("NDX"),
        client.index_inventory.get_expiry_flow_series("NDX", **selection),
    )


async def run():
    async with AsyncSharketoClient(
        "sk-shark-synthetic-only",
        "http://localhost",
        transport=httpx.MockTransport(respond),
        max_retries=0,
    ) as client:
        inspect(
            await client.index_inventory.get_expiry_flow_latest("NDX"),
            await client.index_inventory.get_expiry_flow_series("NDX", **selection),
        )


asyncio.run(run())
assert (
    calls
    == [
        "/v1/developer/inventory/index/NDX/expiry-flow/latest",
        "/v1/developer/inventory/index/NDX/expiry-flow/series",
    ]
    * 2
)
```

For separately approved agent-run live validation, follow the [validation workflow](workflow.md).
