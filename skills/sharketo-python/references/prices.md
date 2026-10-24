# Prices, SDK 0.1.14b3

For stream lifecycle and status refresh, see [application integration](integration.md#streams).

## Verified boundary

- Async-only `client.subscribe_prices(ticker)` returns `PriceSubscription`. Do not await
  the factory. Use async contexts for the client and subscription.
  Only canonical `SPX` and `NDX` are supported. A resolved `websocket_url` is required.
  Use the documented production default or an explicitly approved custom URL, as described
  in [configuration](integration.md#endpoints-and-environment-configuration). There is no
  SDK HTTP quote endpoint or polling API. Do not use `get_access()` as a preflight because
  that diagnostic remains inventory-specific.
- Iterate frozen `PriceStreamSnapshot` records. Each contains `.quote: RealTimePriceV1`,
  local wall-clock `.received_at_ms`, monotonic `.receipt_age_seconds` and dynamic
  `.disconnected`. The subscription exposes `.ticker`, `.latest`, `.status` and
  `.aclose()`. Quote attributes are snake_case. `.model_dump(mode='json', by_alias=True)`
  returns camelCase JSON with RFC3339 timestamps. Records are immutable.
- The `realTimePrice` v1 service sends `full` and `price` as complete server-merged
  replacements, never client field deltas. All fields are required, including nullable
  metrics and the nullable source timestamp. Replace the entire quote and preserve null
  versus zero. SPX and NDX `price` is the underlying index level. Metrics can be signed
  or fractional and are not restricted to positive values. Display change and volume as
  the supplied provider-mapped values. Do not recompute them or infer units. Keep separately
  identified application analytics distinct from SDK quote fields. `change_percentage`
  is already a percentage. `1.25` displays as `1.25%`, not `125%`.
- `ingested_at` is backend ingestion time, not local receipt time. `source_timestamp`
  belongs to the accepted price. It is either valid provider time or the ingestion-time
  fallback for that price-bearing update. Timestamp-only partial updates and partial updates
  with invalid prices retain the prior price and source timestamp together. Absent provider
  metrics retain the previous server-merged metrics. Public null means unknown, not a
  provider clear instruction. The SDK does not repeat the server's merge.
- The startup full snapshot may be cached, preserving source and ingestion clocks, or empty,
  with all nullable fields null and the current ingestion time. The service can suppress
  unchanged observations without refreshing ingestion. There is no freshness TTL for source
  or receipt, or any guarantee of revisions, timestamp ordering, replay, continuity or every
  event. Source time need not originate with the provider or be monotonic. A recent receipt
  does not prove fresh market data, and silence does not prove disconnection. Do not apply
  summary's ten-second TTL to prices.
- One client shares its WebSocket across prices and inventory. Identical price subscriptions
  share a reference-counted quote and its original receipt metadata. Slow consumers receive
  latest-only state. Closing or cancelling one consumer preserves the others. Always close
  the subscription and client. Reconnect requires a new full baseline. Retained values stay
  transport-stale until replacement, and old wrappers remain disconnected even after a new
  baseline. A connected downstream socket does not prove provider health.
- API-key access requires effective Apex access through `developer_api`, verified email,
  `api_keys` and `market_prices.live`. Pro browser-session price eligibility does not
  authorize SDK/API-key subscriptions to the shared service.
  Inventory access diagnostics do not establish price access. Existing shared subscription,
  rate and revocation policies apply. Transport errors use the
  [SDK error boundary](sdk.md#read-only-diagnostics-and-terminal-errors).

The SDK handles v1 JSON and gzip framing, ACK and channel routing, and bounded decoding.
Applications must not reconstruct the protocol.

## Offline validation fixture (installed package)

The inputs are invented server-complete quotes, not provider partial updates.
For agent-run live checks, follow the [validation workflow](workflow.md).

```python
from sharketo import RealTimePriceV1
from sharketo.models import parse_price

full = {
    "updateType": "full",
    "ticker": "SPX",
    "price": 5000.0,
    "volume": None,
    "change": -2.5,
    "changePercentage": 1.25,
    "sourceTimestamp": "2025-01-02T14:30:00Z",
    "ingestedAt": "2025-01-02T14:30:02Z",
}
seed = parse_price(full)
assert isinstance(seed, RealTimePriceV1)
assert seed.source_timestamp != seed.ingested_at
# A cached full preserves backend clocks; it does not become newly sourced data.
cached = parse_price(seed.model_dump(mode="json", by_alias=True))
assert cached.source_timestamp == seed.source_timestamp
assert cached.ingested_at == seed.ingested_at

replacement = parse_price(
    {
        **full,
        "updateType": "price",
        "price": 0.0,
        "volume": 0.0,
        "change": None,
        "sourceTimestamp": "2025-01-02T14:29:00Z",
        "ingestedAt": "2025-01-02T14:29:00Z",
    }
)
latest = replacement  # Replace the whole quote, even with older timestamps.
assert latest.source_timestamp < seed.source_timestamp
assert latest.source_timestamp == latest.ingested_at  # Possible ingestion fallback.
assert latest.change is None and seed.change == -2.5
assert latest.price == 0.0 and latest.volume == 0.0


def display(value):
    return "—" if value is None else f"{value:.2f}"


assert display(latest.change) == "—"
assert display(latest.price) == "0.00"
assert f"{display(latest.change_percentage)}%" == "1.25%"
empty = parse_price(
    {
        **full,
        "ticker": "NDX",
        "price": None,
        "volume": None,
        "change": None,
        "changePercentage": None,
        "sourceTimestamp": None,
    }
)
assert empty.price is None and empty.source_timestamp is None
assert display(empty.price) != display(latest.price)
print("synthetic prices: unknown=— zero=0.00 percentage=1.25%; clocks separate")
```
