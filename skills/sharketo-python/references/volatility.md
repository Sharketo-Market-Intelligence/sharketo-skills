# Curated Volatility, SDK 0.1.14b4

For client reuse and repeated reads, see [application integration](integration.md#http-reads).

## Boundaries and identity

- Both clients expose `volatility.get_catalog()`, which returns root `VolatilityCatalogV2`; `get_asset(asset_id)`, which returns `VolatilityAssetV2`; and `get_term_structure()`, which returns `VolatilityTermStructureV1`. Await calls on `AsyncSharketoClient`. Each call makes one GET without query parameters under `/v1/developer/volatility/`, at `catalog`, `assets/{asset_id}` or `term-structure`. It does not require an inventory `get_access()` or catalog preflight. Use canonical public asset IDs such as `AAPL`, `ES`, `EURUSD`, `BTCUSD` and the other catalog IDs. Do not normalize IDs or substitute arbitrary or custom tickers, filenames or aliases. Validate IDs before I/O and check the returned asset identity.
- The backend supplies financial analysis, cones, estimators, signals, forecasts and term statistics. The SDK validates, transports and deeply freezes them without local financial computation. Keep application decisions distinct from backend analytics. The API has no refresh, historical query or WebSocket service.
- Root and nested records are frozen. Arrays, price-band pairs and history pairs are tuples. Attributes use snake_case, and `.model_dump(mode="json", by_alias=True)` emits wire JSON. Preserve required nulls, zero, signed values, supplied order and independent histories. Never crop, fill, sort or recompute metrics to repair invalid snapshots.

Public estimator wire keys are `closeToClose`, `highLowRange`, `openHighLowClose`,
`openCloseRange` and `overnightAdjusted`. Python attributes use snake_case. These are
distinct supplied realized-volatility estimates with the same annualized decimal units.
They are not interchangeable fields or client-selectable calculation modes. Preserve each value.

Forecast wire keys are `adaptive`, `forecast21d` and `fitScore`.

## Dates and availability

- Every root has `generated_on`, `generation_date_semantics="generationDate"` and `freshness="unknown"`. The generation date is the generator's ET calendar date. It is not a publication timestamp, generation ID, source age, provider health signal, TTL or current-session guarantee. Local fetch completion is a separate clock. Endpoints do not form a transactional snapshot.
- Asset `as_of` with `as_of_semantics="analyzedSourceDate"` is the final underlying bar date, where RV arrays end. It is no later than generation. Paired-IV signals can use another intersecting source date that is not published. Do not label every metric with underlying-source freshness.
- The catalog has seven fixed classes and exposes each asset's ID, class, name and nullable IV-symbol identity. `member_count` is the fixed universe count. `available_member_count` counts analyses that succeeded in the generator; it does not establish per-asset availability, freshness or authorization.
- Known source failures return a typed asset that retains its identity, with `available=False`, `unavailable_reason="analysisFailed"`, `analysis=None` and `as_of=None`. A successful asset has analysis and a source date, with no failure reason. Missing, corrupt or incoherent artifacts produce sanitized 503 `VOLATILITY_UNAVAILABLE` errors, not fabricated analysis failures or empty successes.
- Term `analysis` is always present. `available` means only `ratio_today is not None`. When it is false, preserve the other supplied curves, VX, histories and state statistics. Curves and histories can have different source dates and lengths. Curve legs have no individual observation dates and do not form a synchronized or live curve.

## Values and units

- Asset `spot` is the native underlying close. `analysis.cone`, estimators (`close_to_close/high_low_range/open_high_low_close/open_close_range/overnight_adjusted`), `rv_series.rv21/rv63`, signal RV, the adaptive current estimate and the 21-session forecast use annualized decimals. A value of 0.20 means 20%, not 0.20 vol points. Cone horizons are trading sessions, and sample distributions are not confidence intervals. `current_pct` and signal trailing percentiles use [0,100]. `overnight_share` is a variance fraction.
- Signals preserve RV10, RV21, RV63 and RV252, decimal `rv21_change1w`, backend regime, RV ratio, vol-of-vol, correlation, absolute-return autocorrelation and persistence. Do not derive regime from percentile. `expected_moves` contains supplied one-sigma and two-sigma price bands for 1, 5 and 21 trading days, not outcome probabilities. `straddle21d_pct` is a fraction of spot despite its name. `vol_target_exposure` is a multiplier in [0,2].
- In paired `signals.vrp`, `iv` uses vol points, so 25 means 25%. `spread` is the supplied signed implied-versus-realized volatility spread in vol points. `spread_var` is the corresponding supplied variance spread in squared vol points. `pct1y/pct5y` use [0,100]. Do not rescale supplied output or substitute another IV identity.
- The `forecast` record's `adaptive` can exist with `forecast21d=None` and `fit_score=None`. `adaptive` is the annualized current volatility estimate, not a horizon-specific forecast. `forecast21d` is the annualized estimate for the next 21 trading sessions. `fit_score` is its in-sample fit diagnostic, not confidence or probability.
- Term `curve_today/curve1w/curve1m` contain available 9D, VIX, 3M and 6M IV legs at nominal 9, 30, 93 and 184 calendar days, respectively. Values use vol points. The one-week and one-month references look back 5 and 21 sessions independently for each source. `ratio_series/ratio_today` describe the VIX-to-VIX3M term ratio, with percentiles in [0,100]. `slope_today` is the supplied signed VIX3M-versus-VIX spread in vol points.
- VX expiry and DTE refer to generation. Last price, settlement price and `basis` versus VIX use vol points; they are not live quotes. `front_basis_pct_of_spot`, `basis_series` and `roll_yield_ann` are fractions, not [0,100] percentages. `basis_points_series` and `f2f1_series` are signed vol-point differences. Do not infer separate futures observation timestamps.
- In conditional and state statistics, `mean_fwd_pp` is the 21-session S&P return in percentage points, and `hit` is a fraction in [0,1]. `curve_states` retains the normal, watch, stress order, `days_pct` in [0,100], counts and null means and hits for zero-sample buckets. These in-sample statistics use non-overlapping windows. They are not next-move probabilities or forecasts.

## Bounds and access

- All numbers must be finite and bounded, and dates must be canonical. Cone windows, RV dates and IV legs must be ordered. RV arrays must align, the ratio tail must be exact, and the 21-session forecast and fit score must have paired availability. Identities and counts must be coherent. Limits are nine cones, 504 RV rows, three expected-move horizons, four IV legs, four conditional buckets, 32 VX rows and 20,000 rows independently per term history. There must be exactly three state rows. Do not silently truncate data. VX expiry may extend at most 3,660 days from generation, and DTE must equal that exact calendar-day difference. Other source dates end no later than generation.
- SDK HTTP has a default response bound of 1 MiB. Valid larger snapshots can exceed that default. For larger explicit bounded reads, use client `max_response_bytes=8_388_608`. This sets an 8 MiB client-wide response bound, not a per-Volatility override, and leaves global defaults unchanged. A larger response can still be rejected with `ProtocolError`. Keep a finite response bound rather than removing it to force success.
- Access requires effective Apex access through `developer_api`, an API key, verified email, `ApiKeys` and `Models`. Existing key restrictions and the shared-account budget of 60 requests per minute apply. Typed `APIError` preserves safe authentication, feature, entitlement and rate metadata. A 429 response has Retry-After; a quota dependency failure is 503 `DEPENDENCY_UNAVAILABLE`.

## Offline validation fixture, installed-only synthetic data

The bundled [synthetic fixture](volatility_fixture.py) exercises direct sync and async reads, full asset analytics, a known failure and preservation of partial term data.

```python
from importlib import resources
from runpy import run_path

fixture = resources.files("sharketo").joinpath(
    "_skills/sharketo-python/references/volatility_fixture.py"
)
with resources.as_file(fixture) as path:
    run_path(str(path), run_name="__main__")
```

For separately approved agent-run live validation, follow [workflow](workflow.md). See [SDK compatibility](sdk.md) and [installation](install.md).
