# Inventory rendering contract, SDK 0.1.15b1

For stream lifecycle and status refresh, see [application integration](integration.md#streams).

Summary and rich inventory require effective Apex access through `developer_api`, along
with existing verified API-key, terms and family requirements. The backend is authoritative;
see [access diagnostics](sdk.md#read-only-diagnostics-and-terminal-errors). Do not add a
`get_access()` preflight for rich options.

## Upgrading from 0.1.14b4 or earlier

The service retired the v1 inventory summary, access and chart contracts. SDK 0.1.14b4 and
earlier fail on those calls with terminal `SERVICE_RETIRED`; upgrade to 0.1.15b1 (see
[installation](install.md)). Version 0.1.15b1 reads the v2 contracts:

- The chart state is a whole series book (`series`) instead of a per-contract `entries` map.
  `InventoryEntry`, ATM IV evolution, `tracking_start_time`, `last_update_time` and
  `metadata.stale_volatility_share` were removed. Readings and statistics can be `None`
  (unavailable); history and Bookmap rows can carry an `origin`.
- Exposure profiles and `include_profiles` were removed; the service no longer provides them.
- The summary drops `stale_volatility_share`. Its `regime_id` is 1–16 or `None` (also on a ready
  summary), and its tracked-activity counters count the live session and can be `None`.
- Exposure units changed (see below). Do not compare or chart v2 numbers against values recorded
  with earlier SDK versions.

## Ownership and product choice

- Preserve the supplied financial meaning rather than recomputing Greeks, IV, forecasts or classifications in Python.
- Use HTTP summaries or `subscribe_summary()` for compact metrics. Use `subscribe_inventory(ticker, include_bookmap=True, include_history=True, time_window='session')` for the series book and charts. This method creates an async context manager and is not awaitable. It supports only SPX and NDX. Rich state has no summary-style `ready` field.
- Rich subscriptions are not lightweight quote streams. History and Bookmap both default to true and add cost. For current-only views, pass `include_history=False, include_bookmap=False`. Setting both to false omits chart histories, not the current series book. Only `time_window='session'` is accepted.
- The public service is `indexInventory.v2`. The independent history and Bookmap interests control their full baselines and subsequent tails. The service carries the market maker's estimated series book, its exposure readings, spot, ATM IV, trade statistics, session metadata, history and Bookmap.
- `time_window` selects retained chart history, independently of the current book and current totals. It does not turn the book into rolling session trade flow. Expiry windows `ALL`, `0DTE`, `1DTE`, `WEEKLY`, `MONTHLY` are a different dimension.

Use [daily history](daily-history.md) for separate reconstructed daily HTTP tables. That API does not expand the resolved-session rich stream into an intraday multi-session archive.

## Public state and chart inputs

`InventoryStreamSnapshot.inventory` is `IndexInventoryState`, a frozen dataclass. State and row collections are tuples and read-only mappings, not wire-model `.model_dump()` objects. Series and nested leaf records are frozen Pydantic models with snake_case attributes.

| Display | Exact inputs |
| --- | --- |
| Current series or strike table | `series` is a tuple of `InventorySeries` with `.root`, `.expiration`, `.expiration_timestamp`, `.strike`, `.option_type`, `.open_interest`, `.volume`, `.position`, `.position_sd`, `.carried_position`, `.iv`, `.exposures` and `.unvalued`. `None` means the book has not arrived yet (unavailable); `()` is a real empty book. |
| Server aggregate cards | `exposure_totals` (ALL) and `exposure_totals_by_window[window]`. A `None` window value is unavailable. |
| Unavailable windows | `unavailable_by_window[window].books` lists `InventoryUnvaluedBook` records (`.root`, `.expiration`, `.reason`: `NO_FORWARD` or `NO_SMILE`). An empty mapping means every window is valued. |
| Current spot, IV and regime | `spot_price`, `atm_iv`, `atm_iv_by_window[window]` and `regime_id`. |
| Whether a reading was supplied | `supplied_readings` names which of `exposure_totals`, `exposure_totals_by_window`, `unavailable_by_window`, `regime_id`, `atm_iv` and `atm_iv_by_window` the stream has carried since the latest baseline. |
| Activity | `stats` and `tracked_expirations`. |
| Aggregate history | The ordered `history` tuple contains `.timestamp`, `.spot_price`, nullable `.exposures`, `.regime_id` and `.atm_iv`, optional `.atm_iv_by_window` and `.exposures_by_window`, and optional `.origin`. |
| Bookmap | Use `.timestamps`, `.spot_history`, `.snapshots` and `.all_strikes` from `bookmap_history_by_window[window]`. `bookmap_history` is only the ALL alias. |
| Session and freshness context | Use `metadata`, `session`, `timestamp` and `reference_timestamp`. `session` is an alias for `metadata.resolved_session`. |

`InventoryExposureTotals` has ten exposures: `dex`, `gex`, `spex`, `vex`, `vax`, `vox`, `tex`, `cex`, `zex` and `kex`. `InventorySeriesExposures` has the same ten, each nullable when the volatility smile cannot price that exposure at the strike. Bookmap `InventoryBookmapStrike` leaves carry the ten exposures plus the market maker's position at the strike, `.pos` and `.pos_sd` in contracts, which are `None` where position by strike does not cover the strike.

`stats` exposes `total_trades`, `total_contracts`, `last_trade_time` and `trades_per_second` (prints taken by the live session: activity, not book size) and `unique_strikes` and `unique_expirations` (strikes and expirations the book holds a position in). Each is `None` until reported; `None` is unavailable, never zero. Prefer those server values to locally reconstructed activity rates.

## Identity, grouping, units and totals

- A series is identified by `(root, expiration, strike, option_type)`. `state.ticker` identifies the underlying and `.root` the listed option root; SPX and SPXW, or NDX and NDXP, can share expirations and strikes. Never key a series table by strike alone. Join tracked-expiration labels using at least `(root, expiration)`.
- `.position` is the market maker's estimated position in contracts (positive is long) with standard deviation `.position_sd`; `.carried_position` is the part carried from earlier sessions. A series whose book cannot be valued has `.iv` and `.exposures` `None` and `.unvalued` set to `NO_FORWARD` or `NO_SMILE`; its position is still measured.
- Strike bars may sum `series.exposures.<metric>` over the selected series at a strike. Series exposures are already position-weighted US dollars. Never multiply again by `position`, contract multipliers, spot or a percent move. If any contributing value is `None` or a series is unvalued, mark the bar unavailable or label it partial; never treat the gap as zero.
- Use server values for aggregate cards. A filtered view may show a clearly labeled display-only subtotal of supplied series exposures. That subtotal must not replace `exposure_totals` or appear to be a server window total. Do not require series and totals to reconcile on each delivered state.
- Units are US dollars: `dex` is delta notional (no 1% factor); `gex` and `spex` are per 1% move of the underlying; `vex`, `vax`, `vox` and `zex` per volatility point; `tex`, `cex` and `kex` per hour. They are signed sums, not scaled to millions. You may scale them for display with an explicit unit label, but do not recalculate them. SPX and NDX spot and strike units are index points. IV is an annualized decimal, so display `0.20` as `20%`.
- `regime_id` is the sign regime 1–16 of the ALL window's GEX, VEX, VAX and VOX. It is `None` when any of those signs is not identified or unavailable; show "unidentified", not a regime.
- Preserve `None` as unknown or unavailable. Display a missing-value marker or chart gap, not `0`. Numeric zero is a real supplied value, including spot zero during initialization.

## Unavailable versus not supplied

- A supplied `series` replaces the whole book. There are no per-series updates; do not merge with the previous tuple.
- A reading that is `None` **and** listed in `supplied_readings` is unavailable: never draw it as zero, never interpolate across it and do not keep showing the previous value. A `None` reading not listed there has not been supplied since the latest baseline; show it as pending or unknown.
- A window is unavailable as a whole when any book it sums cannot be valued. Use `unavailable_by_window` to explain which books and why. No assumed volatility or forward stands in for the missing one.
- Applications receive already-resolved state, not patches. A supplied map replaces the prior map; keys absent from that replacement do not retain old values.

## Expiry and resolved-session labels

- `tracked_expirations` records expose `.root`, `.expiration`, `.settlement_style`, `.maturity_timestamp`, `.expiration_timestamp`, optional `.expiration_type` and nullable `.primary_bucket`. Use server `.primary_bucket` for primary expiry labels. `None` is unbucketed, not automatically MONTHLY. Treat missing tracked classification as unknown.
- The backend assigns primary maturity groups that are disjoint except for ALL. 0DTE and 1DTE identify the current and next trading-date groups. WEEKLY and MONTHLY identify broader maturity groups, not listing types or guaranteed calendar weeks or months. Preserve nullable classification and use the supplied labels. Do not classify locally from calendars, weekends or month names.
- `.expiration_timestamp` is the contribution cutoff, distinct from `.maturity_timestamp`. The server determines book membership; a series leaves the book at settlement. Do not remove series locally or rebucket them using the machine's clock.
- Use nullable `state.session` for the resolved session. Its exact fields are `.date_key`, `.resolution` (`current` or `last_completed`), `.start_ms`, nullable `.regular_close_ms`, `.data_end_ms`, `.axis_end_ms`, `.is_fallback` and `.time_zone`. Times are UTC Unix milliseconds. Label them in the supplied America/New_York zone, not the workstation zone.
- Off-session may resolve to the last completed session rather than today's date. Show the resolved date, resolution and fallback indicator. Use the start and axis bounds for chart layout and the data end for observed extent. Axis extent is not evidence of samples. If the session is absent, show unknown context rather than constructing today's market schedule.

## Sample semantics and origin

- Bookmap histories expose aligned immutable tuples of timestamps, spot values and snapshots, plus a numerically sorted strike axis. A row's `.strikes` maps preserved server strike strings to `InventoryBookmapStrike` leaves. Use numeric sorting only for layout, not key reconstruction. A window that cannot be valued records no Bookmap row.
- In an existing supplied sparse row, an omitted strike means no contributing inventory at that strike for that row. Render an empty cell that indicates no contribution. Do not carry a previous row's value forward. An explicit numeric zero exposure is a supplied zero.
- A missing timestamp or sample is unsampled, not an observed all-zero row. Do not fabricate regular-grid observations or bridge missing sessions. A history sample's `None` exposures, regime or IV mean unavailable at that sample: break the line there.
- History samples and Bookmap rows carry `.origin`: `"live"` (recorded as the session happened), `"reconstructed"` (a completed session's published record) or `None` (not reported: unknown, not live). Label samples by origin if useful; never drop, blend or recompute them by origin. Minutes the live book did not record stay missing.
- SDK tails replace whole samples at equal timestamps. Replacing a sparse row must not union its old strikes. Full baselines reset state. Session replacement clears aggregate history and every Bookmap window and axis, even for empty replacements. Metadata-only heartbeats preserve history. Trimming retains samples equal to the cutoff.

## Freshness, delivery and lifecycle

- Rich wrapper `.received_at_ms` records local wall-clock receipt. `.receipt_age_seconds` advances monotonically. Attaching to a cached subscription retains the original receipt metadata rather than recording a new receipt. Rich state has no `.stale` property or ten-second publication guarantee.
- `state.timestamp` and `reference_timestamp` are chart and valuation references, not freshness clocks. Keep `state.metadata.data_as_of_timestamp`, `state.metadata.runtime_status`, receipt age and wrapper `.disconnected` separate. Check `state.metadata.runtime_status` for `None` before reading `.health` or `.reason`. Do not infer provider health from age or invent a provider freshness threshold.
- Summary wrappers instead expose publication age, nullable source age and `.stale`, which includes disconnect and the ten-second publication lifetime. Readiness, producer health, provider age and connectivity are independent for either product. Never label rich state fresh using the summary clock.
- Consume complete immutable replacement state. The SDK applies every accepted full frame, patch and tail in receive order before its capacity-one latest-only delivery. Equal timestamps do not imply duplicate frames. Do not coalesce raw frames or mutate retained `inventory` or rows. Replace the application's state pointer and throttle rendering, not SDK financial-state processing.
- Latest-only delivery, server coalescing and soft omissions do not provide a complete tape, replay cursor or gap-detection guarantee. Keep SDK consumption and rendering bounded. Define a retention policy for any application storage and do not claim that it contains a complete tape. Reconnect clears the accumulator and requires a full inventory baseline. Retained old `.latest` wrappers remain disconnected even after the new transport connects. If you retain displayed values, mark them disconnected until replacement.
- One client shares one socket across summary and rich subscriptions. Subscriptions with identical service, ticker and options share materialization. See [application integration](integration.md#streams), [workflow](workflow.md) and [SDK failure budgets](sdk.md#rich-safety-limits-and-failure-scope).

## Offline validation fixture: compact synthetic edge case

```python
from sharketo import (
    InventoryBookmapSnapshot,
    InventoryBookmapStrike,
    InventoryExposureTotals,
    InventorySeries,
)

metrics = tuple(InventoryExposureTotals.model_fields)


def series(root, option_type, gex, unvalued=None):
    exposures = None if unvalued else {m: (gex if m == "gex" else 0.0) for m in metrics}
    return InventorySeries.model_validate(
        {
            "root": root,
            "expiration": "2026-07-17",
            "expirationTimestamp": 1784295000000,
            "strike": 6000.0,
            "optionType": option_type,
            "openInterest": 100.0,
            "volume": 10.0,
            "position": 99.0,
            "positionSd": 4.0,
            "carriedPosition": 90.0,
            "iv": None if unvalued else 0.2,
            "exposures": exposures,
            "unvalued": unvalued,
        }
    )


book = (series("SPX", "call", 12.0), series("SPXW", "put", -2.0))
subtotal = sum(s.exposures.gex for s in book)
assert len({(s.root, s.expiration, s.strike, s.option_type) for s in book}) == 2
assert subtotal == 10.0
partial = book + (series("SPXW", "call", 0.0, unvalued="NO_SMILE"),)
assert any(s.exposures is None for s in partial)
cell = InventoryBookmapStrike.model_validate(
    {**{m: (10.0 if m == "gex" else 0.0) for m in metrics}, "pos": 5.0, "posSd": 1.0}
)
uncovered = InventoryBookmapStrike.model_validate({m: 0.0 for m in metrics})
assert cell.pos == 5.0 and uncovered.pos is None
old = InventoryBookmapSnapshot(timestamp=1000, spot_price=6000.0, strikes={"6000": cell})
replacement = InventoryBookmapSnapshot(timestamp=1000, spot_price=6000.0, strikes={})
assert "6000" in old.strikes and "6000" not in replacement.strikes
assert replacement.origin is None
supplied_readings = frozenset({"atm_iv", "regime_id"})
atm_iv, regime_id, totals = None, None, None
assert atm_iv is None and "atm_iv" in supplied_readings
assert totals is None and "exposure_totals" not in supplied_readings
iv = {"ALL": None, "0DTE": 0.0}
assert iv["ALL"] is None and iv["0DTE"] == 0.0
```

The expected display has two series at one strike and a grouped GEX subtotal of `10`. Never multiply that subtotal by the fixture positions. Once the unvalued `NO_SMILE` series joins, the strike's GEX is unavailable or labeled partial, not `10`. A server aggregate card retains the server-supplied value, not this subtotal. The `pos` of the uncovered strike is unavailable, not zero. The replacement row has no contribution at 6000, the old row is unchanged and the row's origin is unknown, not live. No timestamp 2000 was observed, so do not insert a zero row there. ATM IV was supplied as unavailable: show a gap, not the previous value. The regime is unidentified. Totals were not supplied yet: show them as pending. Display ALL IV as missing and 0DTE IV as the supplied `0%`. Given session resolution `last_completed`, use that supplied session date, not today's date.
