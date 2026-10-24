# Daily inventory history, SDK 0.1.14b3

For client reuse and repeated reads, see [application integration](integration.md#http-reads).

## Supported HTTP boundary

- Both clients expose `client.index_inventory.get_daily_history(ticker, *, start_date: str, end_date: str)`. Await it on `AsyncSharketoClient`. The method makes one bounded HTTP read. It needs no `get_access()` preflight; access diagnostics are summary-specific.
- Use canonical `SPX` or `NDX` and explicit inclusive date bounds in canonical `YYYY-MM-DD` format. Dates must be in years 1900..2100, in ascending order and span at most 366 calendar days. There is no implicit latest range, pagination, truncation or ETF support. The SDK rejects invalid bounds before transport.
- The root-exported `IndexInventoryDailyHistoryV1` has `schema_version/ticker/start_date/end_date/sessions/metadata`. `sessions` is an immutable tuple, and nested leaf records are frozen. Use `sharketo.models.parse_daily_history(payload)` as the shared public validator. Read snake_case attributes and use `.model_dump(mode='json', by_alias=True)` to preserve camelCase wire aliases.
- Sessions have unique dates in ascending order. Each has `date` and a nullable `timestamp` for the replay valuation instant in UTC Unix milliseconds. It also has `spot` in index points, `atm_iv` as annualized decimal IV, `atm_iv_dte` in calendar days, stored `regime_id` in 0..16, and fixed `exposures` and `z` objects. Both metric objects preserve the complete supported set of nullable finite exposure measures, including `gex/vex/vax/vox/delta/theta/dex/tex/cex`. The fixture enumerates the installed public exposure model to include every measure.
- Preserve source zero versus null, including older absent metrics and warmup scores. Values are existing backend replay outputs, not normalized display units. Raw `delta/theta` are not dollarized `dex/tex`. Do not rescale, re-dollarize, reconstruct Greeks, IV or regimes, interpolate gaps or compute local z-scores.
- Backend z-scores describe standardized exposure context over the complete dataset before request filtering. Window and minimum-session metadata are supplied separately. A shorter request does not recalculate scores. Dataset revisions can change early values. Display returned scores, including null warmup values, without reconstructing the method.
- The data has reconstructed `coverage='short_dated_replay'`. It is not complete live inventory or a provider-history API. This API adds no intraday multi-session archive.

## Availability, dates and clocks

| Metadata | Interpretation |
| --- | --- |
| `source_availability='missing'` | The per-ticker source dataset is missing. The request succeeds with no rows, zero dataset and selected counts, and null dates, version and modification time. Do not display it as a populated series. |
| `source_availability='empty'` | The source dataset is valid but has no rows after dataset-wide edge trimming. Version and modification time may be known; version can be null. |
| `source_availability='available'` | Dataset is populated, even when the request selects zero rows. Empty selection is not missing source. |
| `dataset_first_date/last_date/session_count` | These describe the entire trimmed dataset, not just this request. |
| `selected_first_date/last_date/session_count` | These describe returned rows only. Dates are null for zero rows. Show them separately from requested `start_date/end_date`. |
| `generated_at_ms` | This is the artifact modification time, not market or source freshness, SDK receipt time or a TTL. |
| `dataset_version` | This is an opaque identifier, not a content revision or replay cursor. Do not use it to order or deduplicate content. |
| `dataset_omitted_sessions_lower_bound` | This is a dataset-wide lower bound, not a selected-range gap count or exact total. |
| `dataset_trimmed_leading_sessions/trailing_sessions` | These describe existing dataset-wide edge trimming, not selection omissions. |

History requires effective Apex access through `developer_api` and an existing verified server-side API key with `ApiKeys` + `InventoryIndex`. It shares the account's inventory summary and access quota of 60 requests per minute. Existing API-key budgets also apply: 8 requests per second, 200 per minute and one distinct IP per minute. Browser sessions are not accepted.

Successful responses are `no-store` and contain at most 366 rows and 1,048,576 uncompressed encoded JSON bytes. Missing and valid-empty sources return their corresponding 200 states. Unreadable, corrupt, invalid or oversized artifacts return sanitized `503 HISTORY_UNAVAILABLE`, never an empty or partial fallback. Existing 400/401/403/404/429 boundaries remain. Honor bounded retry metadata rather than retrying without limits.

## Offline validation fixture, installed-package synthetic HTTP

```python
import httpx
from sharketo import IndexInventoryDailyHistoryV1, InventoryExposureTotals, SharketoClient

metrics = dict.fromkeys(InventoryExposureTotals.model_fields)
payload = {
    "schemaVersion": "index-inventory-daily-history.v1",
    "ticker": "SPX",
    "startDate": "2026-01-02",
    "endDate": "2026-01-05",
    "sessions": [
        {
            "date": "2026-01-02",
            "timestamp": 1767387600000,
            "spot": 6000.0,
            "exposures": {**metrics, "gex": 0.0, "delta": 5.0, "dex": 7.0},
            "atmIv": None,
            "atmIvDte": None,
            "regimeId": 1,
            "z": metrics.copy(),
        }
    ],
    "metadata": {
        "sourceAvailability": "available",
        "datasetFirstDate": "2026-01-02",
        "datasetLastDate": "2026-01-06",
        "datasetSessionCount": 2,
        "selectedFirstDate": "2026-01-02",
        "selectedLastDate": "2026-01-02",
        "selectedSessionCount": 1,
        "generatedAtMs": 1767740000000,
        "datasetVersion": "012345abcdef",
        "coverage": "short_dated_replay",
        "datasetOmittedSessionsLowerBound": 1,
        "datasetTrimmedLeadingSessions": 2,
        "datasetTrimmedTrailingSessions": 1,
        "zScoreWindowSessions": 63,
        "zScoreMinSessions": 20,
    },
}
calls = []


def respond(request):
    calls.append(request)
    assert request.url.path == "/v1/developer/inventory/index/SPX/history/daily"
    assert dict(request.url.params) == {"startDate": "2026-01-02", "endDate": "2026-01-05"}
    return httpx.Response(200, json=payload)


def number(value):
    return "—" if value is None else str(value)


with SharketoClient(
    "sk-shark-synthetic-only",
    "http://localhost",
    transport=httpx.MockTransport(respond),
    max_retries=0,
) as client:
    history = client.index_inventory.get_daily_history(
        "SPX", start_date="2026-01-02", end_date="2026-01-05"
    )
assert isinstance(history, IndexInventoryDailyHistoryV1)
assert isinstance(history.sessions, tuple) and len(calls) == 1  # No access preflight.
row = history.sessions[0]
assert row.exposures.gex == 0.0 and row.exposures.vex is None and row.z.gex is None
meta = history.metadata
print("SYNTHETIC:", history.ticker, meta.coverage, meta.source_availability)
print("requested:", history.start_date, history.end_date)
print("selected:", meta.selected_first_date, meta.selected_last_date, meta.selected_session_count)
print("dataset:", meta.dataset_first_date, meta.dataset_last_date, meta.dataset_session_count)
print("artifact mtime, NOT source freshness:", meta.generated_at_ms)
print("opaque identifier, NOT content revision:", meta.dataset_version)
print(
    "dataset-wide omitted lower bound, NOT selected gaps:",
    meta.dataset_omitted_sessions_lower_bound,
)
print(
    "dataset-wide trimmed leading/trailing:",
    meta.dataset_trimmed_leading_sessions,
    meta.dataset_trimmed_trailing_sessions,
)
print("date | spot | GEX | raw delta | DEX | ATM IV | z(GEX)")
for row in history.sessions:
    print(
        row.date,
        number(row.spot),
        number(row.exposures.gex),
        number(row.exposures.delta),
        number(row.exposures.dex),
        number(row.atm_iv),
        number(row.z.gex),
        sep=" | ",
    )
```

For separately approved agent-run live validation, follow the [validation workflow](workflow.md). Remove the fixture's synthetic transport and replace its key and URL with `SHARKETO_API_KEY` and `SHARKETO_API_URL` from the server process environment. Set an explicit ticker, start date and end date. For the async client, await the call within an async context. Never preflight summary access.
