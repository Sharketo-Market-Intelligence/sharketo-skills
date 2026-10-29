# Curated RRG, SDK 0.1.14b4

For client reuse and repeated reads, see [application integration](integration.md#http-reads).

## Boundary and interpretation

- Both clients expose `rrg.get_catalog()`, which returns root-exported `RrgCatalogV1`; `rrg.get_group(group_id)`, which returns `RrgGroupV2`; and `rrg.get_screener()`, which returns `RrgScreenerV2`. Await these calls on `AsyncSharketoClient`. They make fixed GETs without query parameters at `/v1/developer/rrg/catalog`, `/v1/developer/rrg/groups/{id}` and `/v1/developer/rrg/screener`. The only canonical group IDs are `spx-sectors`, `factors`, `industries`, `global-markets` and `asset-classes`. Direct group reads validate the ID before I/O and check the returned identity. They do not require a catalog or inventory `get_access()` preflight.
- Curated group members use public tickers supplied by the backend. In `asset-classes`, Bitcoin is `BTCUSD` and Ethereum is `ETHUSD`. Its benchmark remains `AOR`, Global 60/40. Preserve supplied tickers without client-side translation.
- Each call fetches one snapshot. The API has no WebSocket or replay API. The backend supplies ratios, momentum, states, hooks, scores, regimes and statistics. The SDK does not recompute indicators, transitions, forecasts or quadrants. Keep application decisions distinct from backend analytics.
- Records are frozen, arrays and nested coordinate pairs are tuples, and attributes use snake_case. `.model_dump(mode="json", by_alias=True)` emits camelCase JSON. Required nulls remain `None`. Zero is valid, including zero bars, counts and returns. A failed analysis for a known group, screener or member returns a successful HTTP response with `available=False`, `analysis=None` and `unavailable_reason="analysisFailed"`. Failed roots have `as_of=None`. Never substitute zero, carry forward an earlier nonnull coordinate, or invent a benchmark or provenance for failed screener analysis.
- Catalog `as_of_semantics="maximumAnalyzedSourceDate"` identifies the maximum analyzed source date among available groups. The date is nullable when none succeeded. Detail `as_of_semantics="analyzedSourceDate"` identifies that artifact's analyzed source date. `freshness="unknown"` remains unknown. Availability means analysis succeeded; it does not establish source freshness, publication time, artifact modification time, current provider health or local fetch completion. Endpoint reads are nontransactional and may have different dates. Keep each root's date rather than joining them under the catalog maximum.
- Group `analysis.daily_dates/weekly_dates` align with each available member's `daily/weekly.ratio/momentum` tuples. The latest value is the final aligned entry, even if null. `state.daily/weekly` contains separately supplied state and normalized coordinates. Axes are normalized around 100; they are not prices or percent returns. `heading_degrees` permits 360 because of source rounding. For a stationary step, it can be null with zero velocity. Do not fill that null. `velocity/distance` use normalized units, and `bars_in_quadrant` counts bars in the relevant timeframe. Preserve nullable `state.hook`.
- `scores.momentum12_minus1_month_percent`, `momentum1_month_percent`, `return12_month_percent`, `volatility6_month_percent`, `distance_from52_week_high_percent` and `volatility_adjusted_momentum_percent` are backend percent values. `relative_strength_t_statistic` is a t-statistic. Do not rescale these values or replace unknown scores.
- `analysis.parameters.fast_window_bars`, `slow_window_bars`, `momentum_window_bars` and `normalization_window_bars` retain the backend's numerical bar settings. `analysis.regime.below_long_term_average` is the supplied boolean comparison against the long-term average of 200 daily bars. Its wire key is `belowLongTermAverage`. The parameter wire keys are `fastWindowBars/slowWindowBars/momentumWindowBars/normalizationWindowBars`.
- Screener `analysis` retains the supplied `universe`, `membership` and verbatim `note`. These describe curated current membership or membership with an embedded date. They do not guarantee point-in-time historical constituents. Applying current membership to history carries survivorship bias. Preserve `benchmark`, parameters, regime, member `sector/cap_tier` with values `large|small`, state, scores and `weekly_spark`. The spark contains at most nine normalized [ratio, momentum] pairs. Do not invent timestamps.
- `statistics.quadrants` fixes the order as leading, weakening, lagging, improving. Transition counts form a 4 by 4 matrix with its supplied sample size. `median_holding_weeks` has four nullable values. The forward-return horizon is `forward_returns.horizon_trading_days=21`. `all/northeast` each contain four buckets with `mean_relative_return_percentage_points`, `hit_rate_percent` and `sample_size`. Preserve sample counts, units and null values in zero-sample buckets. These descriptive source statistics are not guaranteed forward returns or recommendations. Do not reinterpret northeast conditioning.
- Access requires effective Apex access through `developer_api`, an API key, verified email, `ApiKeys` and `Models`. Existing key restrictions and the shared-account RRG budget of 60 requests per minute apply. All responses use no-store. Typed `APIError` retains authentication, validation, feature, entitlement and rate metadata, including Retry-After for 429 responses. Missing, corrupt, oversized or incoherent artifacts produce sanitized 503 `RRG_UNAVAILABLE` errors. A budget dependency failure produces `DEPENDENCY_UNAVAILABLE`, not a fabricated empty success.
- Public data limits include at most 32 catalog groups, 128 group members, 3000 screener members, 500 daily dates and 156 weekly dates, plus bounded strings and counts. The SDK has a separate HTTP JSON response default of `max_response_bytes=1_048_576`, or 1 MiB. Valid larger RRG snapshots can exceed that default. For bounded larger reads, explicitly construct `SharketoClient(..., max_response_bytes=8_388_608)` or `AsyncSharketoClient(..., max_response_bytes=8_388_608)`, as in the fixture below. This sets an 8 MiB client-wide response bound, not a per-RRG override, and leaves global defaults unchanged. The explicit response bound can still reject a larger response with `ProtocolError`. Do not crop or repair invalid financial data or remove bounds to force success.

## Chart labels and colors

Carry `state.daily` or `state.weekly` ratio, momentum and quadrant together into the chart.
Use the supplied `quadrant` for labels and colors. Published coordinates are rounded, so
comparisons against 100 can disagree with the supplied classification. For example, ratio
99.50 and momentum 100.00 with quadrant `lagging` must retain a lagging label and style.
Keep a null quadrant unknown rather than deriving one from coordinates.

## Offline validation fixture, installed-only synthetic data

The bundled [synthetic fixture](rrg_fixture.py) exercises all three methods on both clients.
Its `rotation_point` adapter preserves supplied quadrants at rounded 100 boundaries. It also
preserves zero, null coordinates, a failed member and a failed screener.

```python
from importlib import resources
from runpy import run_path

fixture = resources.files("sharketo").joinpath("_skills/sharketo-python/references/rrg_fixture.py")
with resources.as_file(fixture) as path:
    run_path(str(path), run_name="__main__")
```

For separately approved agent-run live validation, follow [workflow](workflow.md). See [SDK compatibility](sdk.md) and [installation](install.md).
