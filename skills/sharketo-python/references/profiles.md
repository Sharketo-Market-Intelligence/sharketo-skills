# Exposure profiles, SDK 0.1.14b2

For stream lifecycle and status refresh, see [application integration](integration.md#streams).

## Opt-in public boundary

- Use `client.index_inventory.subscribe_inventory("SPX", include_profiles=True, include_history=False, include_bookmap=False)` inside async client and subscription contexts. This method is not awaitable. Only SPX, NDX and `time_window="session"` are supported. All interest options require actual booleans. History and Bookmap still default to true, and profiles default to false. Profiles are independent of both history interests.
- Consume `snapshot.inventory.profiles_by_window: Mapping[str, InventoryProfiles] | None`. SDK state maps are read-only. The root-exported frozen `InventoryProfiles` exposes `gex/spex/vax/vox/cex` tuples of root-exported frozen generated `InventoryProfilePoint(price, value)` models. Use keyword constructors. State and profile dataclasses are not whole-wire `.model_dump()` models.
- A supplied profile map replaces the entire prior map. `{}` clears it. An empty metric tuple is a supplied empty curve. `None` means profiles were absent or not supplied in the current baseline, not zero exposure. Omitted incremental sections preserve prior curves. A new full baseline without profiles resets them to `None`. Reconnect requires a fresh full baseline. Consume resolved SDK state, not wire deltas. Do not reconstruct SDK state by appending curves or merging by array index. Samples stored by an application are not a supplied curve-history archive.
- `state.profiles_reference_timestamp: int | None` records `data.referenceTimestamp` of the last supplied profile map, including an empty map. Later updates to current state, metadata or history can change `state.timestamp/reference_timestamp` without changing that curve reference. A full baseline without profiles resets both profile fields. There is no independent profile timestamp, revision or refresh cadence, and no archive or replay API.
- Shared subscription identity includes the profile interest. Opt in only when the application uses the curves, since they add server valuation work and payload size. The SDK rejects more than 20,000 total profile points across all metrics and windows with a sanitized `ProtocolError`. It never crops them. That protocol failure terminates the shared stream manager. Other frame and state budgets still apply. These are client budgets, not backend size guarantees.

## Meaning and clocks

- Each point's `price` is a hypothetical underlying price in index points, not a strike identity or observation time. `value` is the supplied signed inventory exposure. It is already position-weighted and dollarized, but not scaled to millions for display. Never multiply by position or re-dollarize. SPEX is the supplied dollar-GEX slope measure per underlying price unit, not raw gamma speed. CEX retains the annual time basis. Do not convert it to per-day values.
- Curves describe conditional current-inventory exposure at hypothetical underlying prices. They retain the backend's IV and maturity context. Inputs can be retained or stale. These curves are not forecasts, models of future inventory or IV, or time-decay paths. Do not present separately identified downstream analysis as a backend-supplied curve or a missing SDK value.
- Preserve the supplied price grid and sample order. Different buckets can use different grids. No fixed grid size or range is promised. Empty buckets have empty metric tuples. The grid need not include current spot. Do not assert that sampled or interpolated values equal `exposure_totals` or window totals. Those are separate current-state products.
- `0DTE/1DTE/WEEKLY/MONTHLY/ALL` are expiry groupings, unrelated to `time_window`. At the valuation reference, the four primary groups are disjoint. They cover the New York date, the next open-market date, the following four open-market dates and then the following seventeen. They are not calendar-week or calendar-month labels, nor nested totals. ALL can include eligible expirations beyond them. Use supplied `tracked_expirations.primary_bucket`, including unknown and unbucketed values. Do not reproduce calendar or fallback classification.
- The curve reference describes the backend's valuation context, not the wall clock used to resolve session history. A newly received full baseline may have older curves and a newer session reference. Keep the curve reference, current-state reference, nullable `metadata.data_as_of_timestamp`, runtime and stale-volatility signals, local `snapshot.received_at_ms`, monotonic `receipt_age_seconds` and dynamic `disconnected` separate. Neither recent receipt nor curve reference proves fresh provider inputs. Rich streams have no summary ten-second TTL.
- Profiles use the existing inventory policy for API keys, verified email and capabilities. `get_access()` remains summary-specific and does not discover profile availability.

## Offline validation fixture (installed package)

```python
from types import MappingProxyType
from sharketo import InventoryProfilePoint, InventoryProfiles

curves = InventoryProfiles(
    gex=(
        InventoryProfilePoint(price=4900.0, value=-12.0),
        InventoryProfilePoint(price=5100.0, value=0.0),
    ),
    spex=(
        InventoryProfilePoint(price=4900.0, value=0.0),
        InventoryProfilePoint(price=5100.0, value=3.0),
    ),
    vax=(
        InventoryProfilePoint(price=4900.0, value=7.0),
        InventoryProfilePoint(price=5100.0, value=-2.0),
    ),
    vox=(
        InventoryProfilePoint(price=4900.0, value=-4.0),
        InventoryProfilePoint(price=5100.0, value=1.0),
    ),
    cex=(
        InventoryProfilePoint(price=4900.0, value=2.0),
        InventoryProfilePoint(price=5100.0, value=-5.0),
    ),
)
empty = InventoryProfiles(gex=(), spex=(), vax=(), vox=(), cex=())
windows = MappingProxyType({"ALL": curves, "0DTE": empty})
assert windows["ALL"].gex[1].value == 0.0  # Supplied zero, not missing.
assert windows["0DTE"].gex == ()  # Supplied empty bucket, not a zero sample.
assert 5000.0 not in tuple(point.price for point in curves.gex)
absent, cleared = None, MappingProxyType({})
assert absent is None and cleared == {} and cleared is not absent
for window, profile in windows.items():
    for metric in ("gex", "spex", "vax", "vox", "cex"):
        points = getattr(profile, metric)
        if not points:
            print(window, metric, "empty curve")
        for point in points:
            print(window, metric, point.price, point.value)
print("synthetic profiles: scenario prices; signed/zero/empty preserved; no valuation")
```

For separately approved live validation, finite retry/reconnect budgets and credential-safe failure handling, follow [workflow](workflow.md).
