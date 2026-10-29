# Crypto current inventory, SDK 0.1.14b4

For stream lifecycle and status refresh, see [application integration](integration.md#streams).

## Public usage

`client.crypto_inventory.subscribe_inventory("BTC", time_window="24h")` is an async-only,
nonawaitable lazy factory. Use `async with ... as sub` and `async for snapshot in sub`.
Close the subscription and client on cancellation. A resolved `websocket_url` is required.
Use the documented production default or an explicitly approved custom URL, as described in
[configuration](integration.md#endpoints-and-environment-configuration).

Only canonical BTC and ETH are supported. The windows are 1h, 4h, 8h, 24h (default), 7d,
1m, 3m, 6m, 1y and max. Currency and window identify a subscription on `cryptoInventory.v1`.
One async client shares its socket with SPX and NDX inventory and prices. This stream has
no HTTP endpoint, polling API or optional section parameters. It needs no access or catalog preflight.
Browser credentials are unsupported. `get_access()` remains index-specific.

`CryptoInventorySubscription` exposes currency, time_window, status, latest and `aclose()`.
Every `CryptoInventoryStreamSnapshot.inventory` is a complete `CryptoInventoryState`.
It contains read-only entries with opaque keys, frozen leaves and a tracked_expirations tuple.
Totals and market metadata replace the previous values. The SDK applies full resets, then
removals, then whole-entry upserts before latest-only delivery. Applications consume the
complete state rather than accumulate deltas. Reconnect requires a new baseline. There is
no sequence, replay or every-provider-event guarantee. Never parse entry map keys.

The window identifies the selector and its history metadata, not a rolling position interval.
Every window exposes the current active flow-formed book. `window_duration_ms` is fixed
selector metadata (max=None), not coverage. Preserve backend-computed financial values.
Python formulas are not a substitute for missing SDK fields.

## Display and units

- Entry position and OI are underlying BTC or ETH coin quantities, not contracts multiplied
  by 100 or dollar amounts. OI is nullable as a whole. Null means unknown, not zero.
  Positions and exposures are signed, and zero is valid. Spot and strike are USD per
  underlying coin.
- Entry `iv.call/put`, `atm_iv` and IV buckets are annualized decimals (0.65 = 65%).
  `dvol` is a percentage-index level (65 = 65%). Preserve explicit nulls in IV buckets.
- The server computes `entry.exposures.call/put` and `exposure_totals.all/by_category`.
  Preserve all supplied exposure fields and their backend dollar-scaled sensitivity
  conventions. Do not re-dollarize them or infer shock normalization. Raw delta is a
  signed delta measure. Raw theta is USD/year, not per day. Some higher-order measures
  can be zero when not computed. Use the supplied server totals rather than summing
  displayed rows.
- The IV accessors are `.field_0_dte`, `.field_1_dte`, `.weekly`, `.monthly` and `.all`.
  Category totals also have `.long`. Tracked expirations have `.expiration`,
  `.expiration_timestamp` and nullable `.primary_bucket`. Crypto settlement is 08:00 UTC.
- `reference_timestamp_ms` is server reference time and can advance without new market
  observations. `emitted_at_ms` is publication time. Neither measures per-metric
  provider freshness. `received_at_ms` and monotonic `receipt_age_seconds` measure local
  receipt. `disconnected` means retained data is transport-stale. Old wrappers remain
  disconnected after reconnect. Keep retained values marked disconnected until replacement.
  Do not infer a TTL, stale property, source-age SLA, timestamp ordering, readiness or source
  freshness. Empty startup zero market values are not live quotes.
- The SDK rejects data that exceeds its bounds rather than cropping it. The limits are
  10,000 accumulated entries, 10,000 removals per frame, 10,000 tracked expirations,
  128-byte opaque keys, 32-byte expiration text and 8 MiB decoded envelopes.
  The materialized payload reserves 1 KiB. Slow consumers may close.

Access requires effective Apex access through `developer_api` and an API key with
verified email, ApiKeys and InventoryCrypto. Existing
quotas and policy apply. For agent-run live checks, follow the
[validation workflow](workflow.md).

## Offline validation fixture (installed package)

```python
from types import MappingProxyType
from dataclasses import FrozenInstanceError
from pydantic import ValidationError
from sharketo import (
    CryptoFullExposures,
    CryptoInventoryEntry,
    CryptoInventoryState,
    CryptoExposureTotals,
    CryptoAtmIvByBucket,
)

metrics = tuple(CryptoFullExposures.model_fields)
zero = dict.fromkeys(metrics, 0.0)  # Invented values, not computed finance.
entry = CryptoInventoryEntry.model_validate(
    {
        "strike": 60000.0,
        "expiration": "2026-01-31",
        "expirationTimestampMs": 1769846400000,
        "position": {"call": -2.0, "put": 0.0},
        "exposures": {"call": {**zero, "gex": -2500.0}, "put": zero},
        "iv": {"call": 0.65, "put": 0.0},
        "openInterest": None,
    }
)
totals = CryptoExposureTotals.model_validate(
    {
        "all": {**zero, "gex": -2500.0},
        "byCategory": {key: zero for key in ("0DTE", "1DTE", "WEEKLY", "MONTHLY", "LONG")},
    }
)
iv = CryptoAtmIvByBucket.model_validate(
    {
        "0DTE": None,
        "1DTE": 0.0,
        "WEEKLY": None,
        "MONTHLY": 0.65,
        "ALL": 0.65,
    }
)
state = CryptoInventoryState(
    currency="BTC",
    time_window="24h",
    reference_timestamp_ms=1769760000000,
    emitted_at_ms=1769760001000,
    window_duration_ms=86400000,
    entries=MappingProxyType({"opaque": entry}),
    exposure_totals=totals,
    spot_price=60000.0,
    dvol=65.0,
    atm_iv=0.65,
    atm_iv_by_bucket=iv,
    tracked_expirations=(),
)
assert state.entries["opaque"].position.call == -2.0
assert state.entries["opaque"].position.put == 0.0
assert state.entries["opaque"].open_interest is None
assert state.atm_iv_by_bucket.field_0_dte is None
assert state.atm_iv_by_bucket.field_1_dte == 0.0
assert state.exposure_totals.all.gex == -2500.0
for mutate, error in (
    (lambda: state.entries.__setitem__("bad", entry), AttributeError),
    (lambda: setattr(entry.position, "call", 99), ValidationError),
    (lambda: setattr(state, "currency", "ETH"), FrozenInstanceError),
):
    try:
        mutate()
    except error:
        pass
    else:
        raise AssertionError("Synthetic public state lost immutability")
print("Synthetic BTC current book: signed/zero/null and frozen state preserved")
```
