# Seasonality, SDK 0.1.14b2

For client reuse and repeated reads, see [application integration](integration.md#http-reads).

## Verified boundary

- The sync client exposes `client.seasonality.get_asset(asset_id)`, `get_catalog()`, `get_monitor(*, ids=None)` and `get_momentum(*, ids=None)`. Await the same methods on `AsyncSharketoClient`. These calls need no `get_access()` preflight. Access discovery describes inventory summaries, not this independent feature.
- `ids=None` requests all identities. Otherwise, supply a sequence of 1 to 50 distinct canonical lowercase ASCII `[a-z0-9_-]` IDs, each at most 64 characters. Do not pass a string, set or generator. Get identities from the catalog rather than normalizing inventory tickers. Output follows artifact order, not selection order. Rows and `unavailable_ids` together account for exactly the selected identities. Unknown IDs are errors, not unavailable rows.
- The public exports are `SeasonalityAssetDetailV2`, `SeasonalityCatalogV2`, `SeasonalityMonitorV1` and `SeasonalityMomentumV1`. They have snake_case attributes. Use `.model_dump(mode='json', by_alias=True)` for camelCase JSON. Nested collections are tuples, and records are immutable. Preserve the distinction between `None` and zero, including when the whole `current` or `next` statistics record is null.
- The catalog uses `seasonality-catalog.v2`, and asset detail uses `seasonality-asset.v2`. Monitor and momentum remain v1. Use catalog IDs and public tickers exactly as the backend returns them, for example `vix` and `VIX`. Do not reconstruct identifiers or mappings in Python.
- The catalog nests assets under `groups`. Each asset supplies `id/ticker/name/available`. `available` means analysis succeeded, not that the data is fresh. Monitor rows supply `mean_percent/hit_rate_percent/t_statistic/sample_size/horizon_trading_days/years.first/years.last`. Momentum rows supply `current/next`, each nullable with `mean_percent/hit_rate_percent/t_statistic/sample_size`. `month/next_month` describes the generator's context, not the request date or `as_of` month.
- `horizon_trading_days` is the configured trading-step horizon for the asset's calendar, not NYSE weekdays or an application-derived date range. It includes weekends for weekend-trading assets. The generator clips historical windows at year end, so the configured horizon does not promise equal sample lengths. Do not reconstruct window dates in Python.
- Percent fields already use percentage units. Display `1.25` as `1.25%`; never multiply by 100. These are historical backend statistics, not supplied forecasts or investment recommendations.
- For the compact catalog, monitor and momentum endpoints, `as_of` is the maximum analyzed source date or unknown. It is not publication time or every asset's date. The responses specify `as_of_semantics='maximumAnalyzedSourceDate'` and `per_asset_freshness='unknown'`. Never infer a TTL or per-row freshness. Separate fetches are nontransactional, even when their dates match. Retain each response's source date, fetch date and unavailable list rather than joining them into a synchronized record.
- Access requires an API key, verified email, `ApiKeys` and `Models`. Inventory access diagnostics do not establish Seasonality availability. Sanitized `APIError` codes include `FEATURE_NOT_AVAILABLE`, `SUBSCRIPTION_REQUIRED`, `RATE_LIMITED`, `SEASONALITY_UNAVAILABLE` and `DEPENDENCY_UNAVAILABLE`. Unavailable artifacts produce errors, not empty successes.

## Offline validation fixture, synthetic seasonal comparison

Fetch labels in this fixture are synthetic receipt metadata, not SDK response fields.

```python
import httpx
from sharketo import SharketoClient

common = {"asOfSemantics": "maximumAnalyzedSourceDate", "perAssetFreshness": "unknown"}
ids = ("alpha", "beta", "missing")
assets = [
    {
        "id": identity,
        "ticker": identity.upper(),
        "name": identity,
        "available": identity != "missing",
    }
    for identity in ids
]
stats = {"meanPercent": 1.25, "hitRatePercent": 60.0, "tStatistic": None, "sampleSize": 8}
payloads = {
    "catalog": {
        **common,
        "schemaVersion": "seasonality-catalog.v2",
        "asOf": "2025-01-30",
        "groups": [{"label": "Synthetic", "assets": assets}],
    },
    "monitor": {
        **common,
        "schemaVersion": "seasonality-monitor.v1",
        "asOf": "2025-01-30",
        "rows": [
            {
                "id": identity,
                "name": identity,
                "group": "Synthetic",
                **stats,
                "meanPercent": value,
                "horizonTradingDays": 7,
                "years": {"first": 2010, "last": 2025},
            }
            for identity, value in (("alpha", 0.0), ("beta", None))
        ],
        "unavailableIds": ["missing"],
    },
    "momentum": {
        **common,
        "schemaVersion": "seasonality-momentum.v1",
        "asOf": "2025-01-29",
        "month": 12,
        "nextMonth": 1,
        "rows": [
            {
                "id": "alpha",
                "name": "alpha",
                "group": "Synthetic",
                "current": stats,
                "next": {**stats, "meanPercent": 0.0},
            },
            {
                "id": "beta",
                "name": "beta",
                "group": "Synthetic",
                "current": None,
                "next": {**stats, "meanPercent": None},
            },
        ],
        "unavailableIds": ["missing"],
    },
}


def respond(request):
    endpoint = request.url.path.rsplit("/", 1)[-1]
    assert request.url.path == f"/v1/developer/seasonality/{endpoint}"
    assert endpoint in payloads  # No independent summary-access preflight.
    if endpoint != "catalog":
        assert set(request.url.params["ids"].split(",")) == set(ids)
    return httpx.Response(200, json=payloads[endpoint])


def percent(value):
    return "—" if value is None else f"{value:.2f}%"


with SharketoClient(
    "sk-shark-synthetic-only",
    "http://localhost",
    transport=httpx.MockTransport(respond),
    max_retries=0,
) as client:
    catalog = client.seasonality.get_catalog()
    monitor = client.seasonality.get_monitor(ids=ids)
    momentum = client.seasonality.get_momentum(ids=ids)

print(
    "CATALOG analysis success, not freshness:",
    [(a.id, a.available) for g in catalog.groups for a in g.assets],
)
print("MONITOR", monitor.as_of, "synthetic fetch-A: id | mean | hit rate | t | n | days | years")
for row in sorted(monitor.rows, key=lambda r: (r.group, r.id)):
    print(
        row.id,
        percent(row.mean_percent),
        percent(row.hit_rate_percent),
        "—" if row.t_statistic is None else row.t_statistic,
        row.sample_size,
        row.horizon_trading_days,
        row.years.first,
        row.years.last,
        sep=" | ",
    )
print("Unavailable:", monitor.unavailable_ids)
print(
    "MOMENTUM",
    momentum.as_of,
    "synthetic fetch-B: generator months",
    momentum.month,
    momentum.next_month,
)
for row in momentum.rows:
    for label, value in (("current", row.current), ("next", row.next)):
        print(
            row.id,
            label,
            "missing statistics"
            if value is None
            else (
                percent(value.mean_percent),
                percent(value.hit_rate_percent),
                value.t_statistic,
                value.sample_size,
            ),
        )
print("Unavailable:", momentum.unavailable_ids, "; separate snapshots, no synchronized join")
assert monitor.rows[0].horizon_trading_days == 7
assert percent(monitor.rows[0].mean_percent) == "0.00%"
assert percent(monitor.rows[1].mean_percent) == "—"
assert percent(momentum.rows[0].current.mean_percent) == "1.25%"
assert momentum.rows[1].current is None
assert set(r.id for r in monitor.rows) | set(monitor.unavailable_ids) == set(ids)
assert monitor.unavailable_ids == momentum.unavailable_ids == ("missing",)
assert monitor.as_of != momentum.as_of and momentum.month == 12
assert monitor.model_dump(mode="json", by_alias=True) == payloads["monitor"]
```

## Full per-asset analysis

- Call `client.seasonality.get_asset(asset_id)` for one direct HTTP read with a canonical lowercase `[a-z0-9_-]{1,64}` ID. Await the call on the async client. The call has no query, catalog or access preflight, cache or financial recomputation. Use the catalog only for optional identity discovery, not to establish authorization or readiness.
- Asset `as_of_semantics='analyzedSourceDate'` identifies this asset's exact analyzed source date. It is not the compact endpoint maximum, generation time or publication time. `per_asset_freshness='unknown'` remains unknown. Separate fetches are nontransactional.
- A known analysis failure returns a successful response with `available=False`, `analysis=None`, `as_of=None` and `unavailable_reason='analysisFailed'`. Unknown IDs are validation errors. Malformed or missing artifacts produce sanitized 503 errors, never empty successes.
- `analysis` preserves annual and current curves, conformity, monthly returns and statistics, turn-of-month, options-expiration and pre-holiday comparisons, Halloween, optional FOMC and four election-cycle curves. All nested arrays, matrix rows and history pairs are immutable tuples, and leaf records are frozen. Use `.model_dump(mode='json', by_alias=True)` to serialize.
- Percent fields are already scaled. Preserve signed values, zero and null. `curve.envelope_low/high/mean` are dimensionless values in [0,1], not percentages, prices or confidence bands in return units. FOMC cumulative returns are backend sums and may be below -100. Do not compound or clip them.
- `years.sample_size <= 25` counts historical samples, not calendar rows. Monthly and Halloween series span `years.first..current.year` inclusive, including the current year and skipped sample years. Thus 25 complete historical years produce 26 calendar rows, and gaps can produce more. Never truncate to 25 rows or infer missing observations.
- `significant_days_percent` uses the full curve's denominator before truncation, while the returned mask omits five tail days. Preserve the scalar; never recompute it from `curve.significant`.
- Annual labels describe the generator's alignment to the current year, not authoritative future trading dates. Current values may be empty. Conformity and FOMC may be absent as explicit null. The SDK supplies no forecast and does not recompute curves or statistics. Preserve backend curves, t-tests, p-values and correlation rather than substituting local calculations. Per-asset freshness remains unknown.

Run the bundled [asset fixture](seasonality_asset_fixture.py):

```python
from importlib import resources
from runpy import run_path

fixture = resources.files("sharketo").joinpath(
    "_skills/sharketo-python/references/seasonality_asset_fixture.py"
)
with resources.as_file(fixture) as path:
    run_path(str(path), run_name="__main__")
```

For separately approved agent-run live validation, follow [workflow](workflow.md).
