# Inventory rendering contract, SDK 0.1.14b3

For stream lifecycle and status refresh, see [application integration](integration.md#streams).

Summary and rich inventory require effective Apex access through `developer_api`, along
with existing verified API-key, terms and family requirements. The backend is authoritative;
see [access diagnostics](sdk.md#read-only-diagnostics-and-terminal-errors). Do not add a
`get_access()` preflight for rich options.

## Ownership and product choice

- Preserve the supplied financial meaning rather than recomputing Greeks, IV, forecasts or classifications in Python.
- Use HTTP summaries or `subscribe_summary()` for compact metrics. Use `subscribe_inventory(ticker, include_bookmap=True, include_history=True, time_window='session')` for entries and charts. This method creates an async context manager and is not awaitable. It supports only SPX and NDX. Rich state has no summary-style `ready` field.
- Rich subscriptions are not lightweight quote streams. History and Bookmap both default to true and add cost. For current-only views, pass `include_history=False, include_bookmap=False`. Setting both to false omits chart histories, not the current inventory book. Only `time_window='session'` is accepted.
- The public service is `indexInventory.v1`. The independent history and Bookmap interests control their full baselines and subsequent tails. The service includes supported exposures, spot, IV, session metadata and opt-in profiles. It excludes entry Greeks, IV, volume, trade census and timestamps.
- `time_window` selects retained chart history, independently of cumulative active inventory in `entries` and current totals. It does not turn the book into rolling session trade flow. Expiry windows `ALL`, `0DTE`, `1DTE`, `WEEKLY`, `MONTHLY` are a different dimension.

Use [daily history](daily-history.md) for separate reconstructed daily HTTP tables. That API does not expand the resolved-session rich stream into an intraday multi-session archive.

Use [profiles](profiles.md) for opt-in conditional price curves, not strike grouping or history interpolation. `include_profiles=False` remains the default. `True` is independent of both history interests. Scenario prices are not strike keys. Preserve the separate reference for the last supplied curve.

## Public state and chart inputs

`InventoryStreamSnapshot.inventory` is `IndexInventoryState`, a frozen dataclass. State and row collections are tuples and read-only mappings, not wire-model `.model_dump()` objects. Nested generated leaf records are frozen Pydantic models with snake_case attributes.

| Display | Exact inputs |
| --- | --- |
| Current strike or contract table | `entries` maps opaque keys to `InventoryEntry` records with `.root`, `.expiration`, `.strike`, `.settlement_style`, `.maturity_timestamp`, `.expiration_timestamp`, `.time_to_maturity`, optional `.expiration_type`, `.position.call/put` and `.exposures.call/put`. |
| Server aggregate cards | Use `exposure_totals` and optional `exposure_totals_by_window[window]`. |
| Current spot and IV | Use `spot_price`, `atm_iv`, `atm_iv_by_window[window]` and optional `atm_iv_evolution_by_window[window]`. |
| Activity and classification | Use `regime_id`, `stats` and `tracked_expirations`. |
| Aggregate history | The ordered `history` tuple contains `.timestamp`, `.spot_price`, `.exposures`, `.regime_id`, and optional `.atm_iv`, `.atm_iv_by_window`, `.atm_iv_evolution_by_window` and `.exposures_by_window`. |
| Bookmap | Use `.timestamps`, `.spot_history`, `.snapshots` and `.all_strikes` from `bookmap_history_by_window[window]`. `bookmap_history` is only the ALL alias. |
| Conditional price scenarios | Optional `profiles_by_window[window]` contains `gex/spex/vax/vox/cex` point tuples. `profiles_reference_timestamp` is the last supplied curve reference, not the latest current-state reference. |
| Session and freshness context | Use `metadata`, `session`, `timestamp`, `reference_timestamp`, `tracking_start_time` and `last_update_time`. `session` is an alias for `metadata.resolved_session`. |

`InventoryExposureTotals` preserves every supported exposure metric, including `gex`, `vex`, `vax`, `vox`, `dex`, `tex`, `cex` and raw `delta` and `theta`. Enumerate the installed public model's fields for complete tables rather than inferring identities or dropping additional measures. Bookmap `InventoryBookmapStrike` leaves contain only the seven `gex/vex/vax/vox/dex/tex/cex` metrics. Do not infer missing analytics from that narrower set.

`stats` exposes `total_trades`, `total_contracts`, `unique_strikes`, `unique_expirations`, `trades_per_second` and `last_trade_time`. Prefer those server values to locally reconstructed activity rates.

## Identity, grouping, units and totals

- Preserve `entries` keys as opaque identities. Their current wire shape is not an API for parsing or reconstructing them. Root, expiration and strike are display dimensions, not substitutes for identity. Never key a mutable contract table by strike alone or regenerate keys from rounded prices.
- `state.ticker` identifies the underlying. `.root` identifies the listed option root. SPX and SPXW, or NDX and NDXP, can share expiration dates and strikes with different settlement styles. Join tracked-expiration labels using at least `(root, expiration)`, not date alone. Retain settlement and cutoff context.
- Strike bars may sum `entry.exposures.call.<metric> + entry.exposures.put.<metric>` over the selected entries. Contributions already incorporate signed inventory and dollarization. Never multiply again by `position`, contract multipliers, spot or a percent move. `delta` and `theta` are raw engine fields, not additional dollarized bars.
- Use server values for aggregate cards. A view filtered by strike, root or expiration may show a clearly labeled display-only subtotal of supplied contributions. That subtotal must not replace `exposure_totals` or appear to be a server expiry-window total. Entries and aggregate totals are updated independently, so do not require them to reconcile on each delivered state. Treat missing window totals as unavailable rather than synthesizing them.
- SPX and NDX spot and strike units are index points. IV is an annualized decimal, so display `0.20` as `20%`. Exposure outputs are raw and are not already scaled to millions. You may scale them for display with an explicit unit label, but do not recalculate them.
- Preserve `None` as unknown or unavailable. Display a missing-value marker or chart gap, not `0`. Numeric zero is a real supplied value, including spot and ATM zeros during rich initialization. Some higher-order measures can be zero when not computed. Zero alone is not evidence of historical flatness.

## Expiry and resolved-session labels

- `tracked_expirations` records expose `.root`, `.expiration`, `.settlement_style`, `.maturity_timestamp`, `.expiration_timestamp`, optional `.expiration_type` and nullable `.primary_bucket`. Use server `.primary_bucket` for primary expiry labels. `None` is unbucketed, not automatically MONTHLY. Treat missing tracked classification as unknown.
- The backend assigns primary maturity groups that are disjoint except for ALL. 0DTE and 1DTE identify the current and next trading-date groups. WEEKLY and MONTHLY identify broader maturity groups, not listing types or guaranteed calendar weeks or months. Preserve nullable classification and use the supplied labels. Do not classify locally from calendars, weekends or month names.
- `.expiration_timestamp` is the contribution cutoff, distinct from `.maturity_timestamp`. The server determines current entry membership. Do not remove entries locally or rebucket them using the machine's clock.
- Use nullable `state.session` for the resolved session. Its exact fields are `.date_key`, `.resolution` (`current` or `last_completed`), `.start_ms`, nullable `.regular_close_ms`, `.data_end_ms`, `.axis_end_ms`, `.is_fallback` and `.time_zone`. Times are UTC Unix milliseconds. Label them in the supplied America/New_York zone, not the workstation zone.
- Off-session may resolve to the last completed session rather than today's date. Show the resolved date, resolution and fallback indicator. Use the start and axis bounds for chart layout and the data end for observed extent. Axis extent is not evidence of samples. If the session is absent, show unknown context rather than constructing today's market schedule.

## Sample semantics and IV continuity

- Bookmap histories expose aligned immutable tuples of timestamps, spot values and snapshots, plus a numerically sorted strike axis. A row's `.strikes` maps preserved server strike strings to seven-metric leaves. Use numeric sorting only for layout, not key reconstruction.
- In an existing supplied sparse row, an omitted strike means no contributing inventory at that strike for that row. Render an empty cell that indicates no contribution. Do not carry a previous row's value forward. An explicit numeric zero leaf is a supplied zero. Bookmap leaves are not nullable. Nullable IV and window maps follow a separate contract.
- A missing timestamp or sample is unsampled, not an observed all-zero row. Do not fabricate regular-grid observations or bridge missing sessions. A plotting library may need empty geometry, but do not treat that geometry as a source observation, statistic or carried-forward financial value.
- When a patch omits an optional outer wire field, that field is unchanged because no value was supplied. Explicit null `atm_iv_by_window` values and `atm_iv_evolution_by_window` points mean unknown. A supplied map replaces the prior map. Keys absent from that replacement do not retain old values. Applications receive the already-resolved state, not patches.
- Each evolution point exposes only `.value` and opaque `.continuity_id`. Break IV segments when continuity IDs change or points are unknown or missing. Do not use the scalar `atm_iv` to fabricate a continuation. `metadata.atm_iv_evolution_available` is a separate availability signal.
- SDK tails replace whole samples at equal timestamps. Replacing a sparse row must not union its old strikes. Full baselines reset state. Session replacement clears aggregate history and every Bookmap window and axis, even for empty replacements. Metadata-only heartbeats preserve history. Trimming retains samples equal to the cutoff.

## Freshness, delivery and lifecycle

- Rich wrapper `.received_at_ms` records local wall-clock receipt. `.receipt_age_seconds` advances monotonically. Attaching to a cached subscription retains the original receipt metadata rather than recording a new receipt. Rich state has no `.stale` property or ten-second publication guarantee.
- `state.timestamp` and `reference_timestamp` are chart and valuation references, not freshness clocks. `tracking_start_time` and `last_update_time` are baseline fields, not receive times. Keep `state.metadata.data_as_of_timestamp`, `state.metadata.runtime_status`, `state.metadata.stale_volatility_share`, receipt age and wrapper `.disconnected` separate. Check `state.metadata.runtime_status` for `None` before reading `.health` or `.reason`. Do not infer provider health from age or invent a provider freshness threshold.
- Summary wrappers instead expose publication age, nullable source age and `.stale`, which includes disconnect and the ten-second publication lifetime. Readiness, producer health, provider age and connectivity are independent for either product. Never label rich state fresh using the summary clock.
- Consume complete immutable replacement state. The SDK applies every accepted full frame, delta and tail in receive order before its capacity-one latest-only delivery. Equal timestamps do not imply duplicate frames. Do not coalesce raw deltas or mutate retained `inventory` or rows. Replace the application's state pointer and throttle rendering, not SDK financial-state processing.
- Latest-only delivery, server coalescing and soft omissions do not provide a complete tape, replay cursor or gap-detection guarantee. Keep SDK consumption and rendering bounded. Define a retention policy for any application storage and do not claim that it contains a complete tape. Reconnect clears the accumulator and requires a full inventory baseline. Retained old `.latest` wrappers remain disconnected even after the new transport connects. If you retain displayed values, mark them disconnected until replacement.
- One client shares one socket across summary and rich subscriptions. Subscriptions with identical service, ticker and options share materialization. See [application integration](integration.md#streams), [workflow](workflow.md) and [SDK failure budgets](sdk.md#rich-safety-limits-and-failure-scope).

## Offline validation fixture: compact synthetic edge case

```python
from sharketo import (
    InventoryAtmIvEvolutionPoint,
    InventoryBookmapSnapshot,
    InventoryBookmapStrike,
    InventoryEntry,
    InventoryExposureTotals,
)

metrics = tuple(InventoryExposureTotals.model_fields)


def totals(gex):
    return InventoryExposureTotals(**{m: float(gex if m == "gex" else 0) for m in metrics})


def entry(root, style, call, put):
    return InventoryEntry(
        root=root,
        expiration="2026-07-17",
        strike=6000.0,
        settlementStyle=style,
        maturityTimestamp=1784295000000,
        expirationTimestamp=1784295000000,
        timeToMaturity=0.01,
        position={"call": 99.0, "put": -8.0},
        exposures={"call": totals(call), "put": totals(put)},
    )


entries = {"opaque-a": entry("SPX", "am_cash", 12, -2), "opaque-b": entry("SPXW", "pm_cash", 5, -5)}
subtotal = sum(e.exposures.call.gex + e.exposures.put.gex for e in entries.values())
assert len(entries) == 2 and subtotal == 10.0
cell = InventoryBookmapStrike(
    **{m: 10.0 if m == "gex" else 0.0 for m in ("gex", "vex", "vax", "vox", "dex", "tex", "cex")}
)
old = InventoryBookmapSnapshot(timestamp=1000, spot_price=6000.0, strikes={"6000": cell})
replacement = InventoryBookmapSnapshot(timestamp=1000, spot_price=6000.0, strikes={})
assert "6000" in old.strikes and "6000" not in replacement.strikes
iv = {"ALL": None, "0DTE": 0.0}
assert iv["ALL"] is None and iv["0DTE"] == 0.0
points = [
    InventoryAtmIvEvolutionPoint(value=0.20, continuityId="a"),
    InventoryAtmIvEvolutionPoint(value=0.21, continuityId="b"),
]
assert points[0].continuity_id != points[1].continuity_id
```

The expected display has two contracts at one strike and a grouped GEX subtotal of `10`. Never multiply that subtotal by the fixture positions. A server aggregate card retains the server-supplied value, not this subtotal. The replacement row has no contribution at 6000, and the old row is unchanged. No timestamp 2000 was observed, so do not insert a zero row there. Display ALL IV as missing and 0DTE IV as the supplied `0%`. The two positive IV points form separate segments. Given session resolution `last_completed`, use that supplied session date, not today's date.
