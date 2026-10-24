# Public SDK reference

## Clients and subscriptions

- `SharketoClient(api_key, api_url=None, *, timeout=10.0, max_retries=2, max_response_bytes=1_048_576, max_retry_sleep=30.0, transport=None)` is a sync context manager; explicit cleanup is `close()`.
- `AsyncSharketoClient(api_key, api_url=None, *, websocket_url=None, timeout=10.0, max_retries=2, max_reconnects=5, max_response_bytes=1_048_576, max_retry_sleep=30.0, transport=None)` is an async context manager. Use `aclose()` for explicit cleanup. Construct, use and close the client in the same event loop. The production API has a default WebSocket URL. Custom API configurations need an explicit `websocket_url` for subscriptions.
- Both clients expose `get_access()` and `index_inventory.get_summary(ticker)`. Await HTTP methods on the async client. HTTP summaries require ready state. Use `get_access()` for summary diagnostics, not as a preflight for other families.
- `max_retries` limits HTTP retries. `max_retry_sleep` limits total retry sleep per HTTP call, not the call's duration. HTTP `timeout` sets HTTPX operation timeouts, not an end-to-end deadline. `max_response_bytes` limits each response's size.
- `transport` accepts the corresponding HTTPX transport, including `MockTransport` for offline fixtures. It does not replace the WebSocket transport.
- Omitting `api_url` or passing `None` selects `https://api.sharketo.com`. The async client defaults to `wss://socket.sharketo.com/v1/ws` only when the resolved API URL is production. A custom API URL alone creates an HTTP-only client. A custom WebSocket URL with an omitted or `None` API URL raises `ValueError`. Explicit API and WebSocket URLs are independent.
- Constructors do not read environment variables. `SharketoClient.from_env(*, ...) -> Self` and `AsyncSharketoClient.from_env(*, ...) -> Self` read key and URL variables once. They accept limits and transport options, but no key or endpoint overrides. See [endpoint configuration](integration.md#endpoints-and-environment-configuration) for environment switching, validation and TLS rules. Plain HTTP and WS are loopback-only.

Call the synchronous subscription factories below without `await`. Enter the returned subscription with `async with` and iterate with `async for snapshot in sub`.

| Async-client factory | Delivered wrapper and payload | Reference |
| --- | --- | --- |
| `client.index_inventory.subscribe_summary(ticker)` | `StreamSnapshot.summary: IndexInventorySummaryV1` | [Summary interpretation](#models-and-interpretation) |
| `client.index_inventory.subscribe_inventory(ticker, include_bookmap=True, include_history=True, include_profiles=False, time_window="session")` | `InventoryStreamSnapshot.inventory: IndexInventoryState` | [Inventory rendering](inventory-rendering.md), [profiles](profiles.md) |
| `client.subscribe_prices(ticker)` | `PriceStreamSnapshot.quote: RealTimePriceV1` | [Prices](prices.md) |
| `client.crypto_inventory.subscribe_inventory(currency, time_window="24h")` | `CryptoInventoryStreamSnapshot.inventory: CryptoInventoryState` | [Crypto inventory](crypto-inventory.md) |

Index subscriptions and prices support SPX and NDX. Crypto supports BTC, ETH and the windows listed in its guide. Rich interests require strict booleans and `time_window="session"`. History and Bookmap default to true. Disable both for current-only views. Enable profiles separately when needed.

Subscriptions expose `.status`, `.latest`, `aclose()` and async context management. One client shares one socket. Subscriptions with identical service, ticker and options share materialized state. The SDK applies every accepted raw delta before latest-only delivery, which may skip intermediate complete states. A reconnect requires a new full baseline.

Wrappers expose dynamic `.disconnected` and age properties. Rich, price and crypto receipt ages are not publication TTLs. Connectivity and age changes do not yield iterator items. See [stream integration](integration.md#streams) for status refresh, cleanup, the shared lifetime reconnect budget and terminal client failures.

## HTTP methods

Both clients expose the same HTTP families. Await each method on the async client. The table lists methods relative to `client`. Family guides define selectors, root-exported response types, units, limits and availability. They also provide executable offline fixtures.

| Family | Public methods | Reference |
| --- | --- | --- |
| Index summary | `index_inventory.get_summary(ticker)` | [Summary interpretation](#models-and-interpretation) |
| Daily inventory history | `index_inventory.get_daily_history(ticker, *, start_date, end_date)` | [Daily history](daily-history.md) |
| Expiry flow | `index_inventory.get_expiry_flow_latest(ticker)`; `get_expiry_flow_series(ticker, *, root, expiration, start_date, end_date)` on the same namespace | [Expiry flow](expiry-flow.md) |
| Dealer Exposures | `dealer_exposures.get_snapshot(ticker)` | [Dealer Exposures](dealer-exposures.md) |
| CTA Flow | `cta_flow.get_snapshot()` | [CTA Flow](cta-flow.md) |
| Seasonality | `seasonality.get_asset(asset_id)`, `get_catalog()`, `get_monitor(*, ids=None)`, `get_momentum(*, ids=None)` on that namespace | [Seasonality](seasonality.md) |
| Volatility | `volatility.get_catalog()`, `get_asset(asset_id)`, `get_term_structure()` on that namespace | [Volatility](volatility.md) |
| RRG | `rrg.get_catalog()`, `get_group(group_id)`, `get_screener()` on that namespace | [RRG](rrg.md) |

Read a canonical asset or group directly without fetching its catalog first. For HTTP examples and client reuse, see [application integration](integration.md#http-reads).

## Models and interpretation

- `IndexInventorySummary` aliases root-exported `IndexInventorySummaryV1`. `DeveloperAccess` aliases `DeveloperAccessV1`. Generated attributes use snake_case. `.model_dump(by_alias=True)` emits wire aliases. Summary generation and revision are strings. Revision is a decimal u64 and orders results only within one generation. Rich state has no public generation, revision or replay cursor.
- Summary `exposures_by_expiry_window` is a nullable model, not a dictionary. Its attributes are `.all`, `.monthly`, `.weekly`, `.field_0_dte` and `.field_1_dte`. Their wire aliases are `ALL`, `MONTHLY`, `WEEKLY`, `0DTE` and `1DTE`. Supplied metrics are `gex/dex/vex/vax/vox/tex`.
- HTTP summaries must be ready. WebSocket summaries can deliver `ready=False`. Ready does not prove current-session trading, complete fields or fresh inputs. Spot, ATM IV, regime, window exposures, session and source timestamps can be null. Zero is not missing.
- `StreamSnapshot` exposes `.received_at_ms`, dynamic `.disconnected` and `.stale`, `.publication_age_seconds` and nullable `.source_age_seconds`. Summary publication lifetime is ten seconds. Source age comes from nullable `data_as_of_ms`. Producer health and reason in `runtime_status.health/reason`, source freshness and transport connectivity are independent. A disconnect marks retained wrappers transport-stale even if publication is recent.
- Rich state contains frozen dataclasses, read-only maps, tuples and frozen Pydantic leaves. It is not a wire patch, and the whole state has no `.model_dump()` method. See [inventory rendering](inventory-rendering.md) for fields, metadata paths, sparse and null semantics, and continuity. See [profiles](profiles.md) for whole-map profile replacement and separate curve timestamps. Preserve supplied dollarized contributions and financial fields.

## Rich safety limits and failure scope

A hydrated session can exceed these SDK limits. The SDK then raises a sanitized `ProtocolError` instead of silently cropping state or substituting synthetic data. Accumulated limits apply across patches and full frames.

| Boundary | Supported limit |
| --- | --- |
| Encoded binary frame / decoded JSON body | 16 MiB / 64 MiB |
| Summary routing / text controls | 1 MiB summary ceiling / 64 KiB controls |
| JSON traversal | 8,000,000 value nodes; depth 64, including ignored/additive properties; finite numbers only |
| Current entries / aggregate history | 20,000 entries / 10,000 rows |
| Bookmap retained state, across five expiry windows | 50,000 rows; 1,000,000 sparse cells; ALL source alias not counted twice |
| Exposure profiles | 20,000 total points across every metric/window; reject, never crop |
| Strike axis | 4,096 values per Bookmap window |
| Entry/removal/upsert keys / Bookmap keys | ≤256 / ≤64 characters |
| Continuity tokens / expiration-type strings | 1–256 / ≤64 characters |
| Tracked expirations / metadata available-window labels | 20,000 records / ≤16 labels of ≤64 characters |

A protocol failure terminates the shared stream manager and affects its other consumers. Investigate malformed, unsupported or oversized state. Do not retry blindly or replace the stream with unbounded polling. Subscription errors scoped to a feature, parameter or access level can leave unrelated subscriptions live.

Server omissions, coalescing and latest-only delivery mean replay may be incomplete. For bounded historical selections, see [daily history](daily-history.md) and [expiry flow](expiry-flow.md).

## Read-only diagnostics and terminal errors

- `ValueError` covers invalid configuration and arguments, including URLs, keys, tickers, windows, rich interests and missing `websocket_url` for subscriptions. `from_env()` also raises `ValueError` for missing or invalid keys and blank or invalid URL variables. Handle these separately from operational SDK failures. Application code that indexes environment variables may raise `KeyError`. Validate inputs before launching background work.
- Catch `SharketoError` for operational SDK failures. `APIError` exposes `status_code`, `code`, `request_id`, `retry_after`, `required_capability` and optional `suggested_plan`. `StreamError` has corresponding stream metadata. `ProtocolError`, `TransportError` and `SDKClosedError` cover schema, transport and lifecycle failures. Follow [sanitized error handling](integration.md#configuration-and-error-boundaries). Keep raw bodies, headers, credentials and transport exceptions out of diagnostics.
- `get_access()` validates existing inventory-summary credentials and reports inventory access and budgets. The API rejects browser sessions and requires current account-level Developer API terms acceptance, verified email, effective Apex access through `developer_api`, and `api_keys` / `inventory.index` capabilities. The v1 response's `required_capabilities` remains the inventory-family pair `api_keys` / `inventory.index`, not every admission rule; Apex is enforced independently. Keys have a one-IP-per-minute limit. Read other request budgets from the response.
- `DEVELOPER_TERMS_REQUIRED` means missing or stale account acceptance, not a bad key. HTTP returns terminal `APIError` with status 403; a subscription-addressed WebSocket error raises terminal `StreamError` for that subscription (including shared consumers), leaving unrelated subscriptions live. Neither triggers automatic retry/reconnect. Ask the user to personally review and accept the current terms in the portal via [setup](setup.md#2-review-the-terms-and-reuse-or-generate-a-key); agents must not accept or rotate keys for agreement. Existing customers also need explicit acceptance before Developer requests resume. Resume only after user confirmation, with a new subscription/request under the application’s bounded policy.
- All SDK Developer HTTP/WS data requires effective Apex access, including prices and `get_access()`. The server evaluates valid paid or explicit grants and their expiry, not just a billing label. Pro portal features, approved Key Levels integrations and API-key management keep their existing rules. When access is denied, preserve sanitized `required_capability="developer_api"` and `suggested_plan="apex"` if returned. HTTP subscription/capability denials are terminal without retries, even with retry headers. A correctly subscription-addressed WebSocket denial ends that subscription and all shared consumers without reconnecting; unrelated streams remain usable. Resolve authorized access before an explicit new request/subscription. Do not add a client-side plan gate or an extra `get_access()` preflight.
- Diagnose authentication, entitlement, feature-disabled, retired-service and unsupported-version/schema failures instead of retrying indefinitely. For rate or IP restrictions, use returned retry metadata, bound retries and confirm single-egress deployment. A new subscription on the same client cannot recover a terminal stream manager. See [stream recovery](integration.md#streams).

### Service availability and compatible versions

| Code | Meaning and action |
| --- | --- |
| `FEATURE_NOT_AVAILABLE` | The feature is disabled. HTTP returns 404. No automatic retry; confirm availability before explicitly trying again. |
| `SERVICE_RETIRED` | The operation/service has been withdrawn. HTTP returns 410. No automatic retry; investigate alternatives. |
| `UNSUPPORTED_API_VERSION` | The requested API/service version is unsupported. HTTP returns 400. No automatic retry; confirm a compatible contract. |

These codes remain terminal even if an HTTP response includes `Retry-After` or a transient
status. Other incidental backend failures keep bounded HTTP retry behavior. Ordinary unknown
routes/services remain not-found, not version errors.

A valid WebSocket lifecycle error addressed to a subscription ends that subscription and all
its shared consumers, leaving unrelated healthy streams usable. This also applies to
unfamiliar future codes. Known transient `RATE_LIMITED`, `SLOW_CONSUMER` and `INTERNAL_ERROR`
controls retain bounded connection-wide reconnect behavior. Connection-level
authentication/security and unsupported-schema errors still fail the shared manager;
malformed routing raises `ProtocolError`. After a subscription-local failure,
create a new subscription only as an explicit application decision under a bounded policy.
Do not turn an unknown error code into an automatic reconnect loop.

SDK release versions and API contract versions are separate. An installed package does not
guarantee continued service availability. Future breaking HTTP contracts use new URL versions
and breaking streams use distinct versioned service identifiers. Unexpected response schemas
raise `ProtocolError`. Do not bypass validation, automatically upgrade/downgrade packages or
rewrite endpoints to work around these errors. Optional future error fields are ignored.

For agent-run live checks, follow [validation](workflow.md).
