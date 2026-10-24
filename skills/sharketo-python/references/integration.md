# Application integration

Read the selected family's guide from the [capability router](../SKILL.md#select-a-capability) for selectors, units, availability and access. For agent-run live checks, follow the [validation workflow](workflow.md).

## Personal-use boundaries

Personal applications may run on the subscriber's devices or in a private cloud environment
under their control. Shared dashboards and public charts fall outside personal access,
including free applications.

For broader-use requests, explain the personal-use scope and offer a synthetic-data prototype
while the user confirms permissions with Sharketo.

The SDK's MIT license covers its code. API content follows the Developer API terms and
content-specific conditions, including copies, caching and retention. Application code may
be published separately from credentials and restricted content.
For user-led portal terms acceptance and key creation, follow [first-time API key setup](setup.md).
Acceptance is durable account state, not a visit-only acknowledgement or a key rotation.
For missing/stale acceptance, follow [terms-required diagnostics](sdk.md#read-only-diagnostics-and-terminal-errors).

## Endpoints and environment configuration

### Production defaults and explicit endpoints

Constructors require an explicit `api_key` and never read environment variables.
Omitting `api_url` or passing `None` selects `https://api.sharketo.com`.
For `AsyncSharketoClient`, omitting `websocket_url` or passing `None` selects
`wss://socket.sharketo.com/v1/ws` only when the resolved API URL is production.

Pass an existing server-side secret when calling these functions:

```python
from sharketo import AsyncSharketoClient, SharketoClient


def read_production_summary(api_key, ticker):
    with SharketoClient(api_key) as client:
        return client.index_inventory.get_summary(ticker)


async def consume_production_prices(api_key, ticker, consume):
    async with AsyncSharketoClient(api_key) as client:
        async with client.subscribe_prices(ticker) as subscription:
            async for snapshot in subscription:
                consume(snapshot)
```

A custom API URL without a WebSocket URL creates an HTTP-only client. Subscribing raises
`ValueError`. A custom WebSocket URL with an omitted or `None` API URL also raises
`ValueError`. Supply both URLs for custom streaming. The SDK accepts explicit API and
WebSocket URLs without inferring hosts or ports. It appends API routes to the HTTP base URL.
The WebSocket URL is independent and must include its actual path.

Use production defaults unless Sharketo supplies a different endpoint configuration.
Use a key authorized for the selected service. Construct, use and close each async client
in the same event loop.

### Environment-based switching

`SharketoClient.from_env()` and `AsyncSharketoClient.from_env()` read process environment
once at construction and return the corresponding client. Both read `SHARKETO_API_KEY`
and `SHARKETO_API_URL`. Only the async factory reads `SHARKETO_WEBSOCKET_URL`.
A missing or invalid key, or a blank or invalid URL variable, raises `ValueError`.
Missing URL variables use the constructor defaults and pairing rules above. Factories
accept the same keyword-only limits and HTTP transport options as their constructors,
including async `max_reconnects`. They do not accept key or endpoint overrides.
Use a constructor to pass those values explicitly.

```python
async def consume_configured_prices(ticker, consume):
    async with AsyncSharketoClient.from_env() as client:
        async with client.subscribe_prices(ticker) as subscription:
            async for snapshot in subscription:
                consume(snapshot)
```

Provision `SHARKETO_API_KEY` through server-side secret tooling. For production defaults,
leave both URL variables unset. Set URL variables only for a configuration supplied by Sharketo;
streaming with a custom API requires both URLs.

Environment changes affect new clients only. The SDK does not scan dotenv files,
derive endpoints or fall back to production after a failure.

HTTPS and WSS require verified TLS. The SDK rejects plain HTTP and WS except for
`localhost` or literal loopback IP addresses. Endpoints cannot contain credentials, queries
or fragments. Endpoint overrides do not bypass API-key authentication or authorization.

Default HTTP transports disable redirects and do not use proxy or CA settings from the
environment, through `trust_env=False`. For a private CA, supply a verified SSL context
through the appropriate HTTPX `transport`. That transport does not configure WebSocket TLS.
WebSockets use normal verified Python SSL trust and disable redirects and proxies.
Keep verification enabled for HTTPS and WSS.

## HTTP reads

Reuse a client across related reads and close it when that work ends. This example reads a bounded list of dealer tickers chosen by the application. Dealer Exposures supports SPX, NDX, SPY and QQQ. Read its [data semantics](dealer-exposures.md) before using the results. See the [SDK reference](sdk.md#http-methods) for other HTTP methods.

```python
from sharketo import SharketoClient


def read_dealer_snapshots(api_key, api_url, tickers, *, max_retries=2):
    with SharketoClient(api_key=api_key, api_url=api_url, max_retries=max_retries) as client:
        return tuple(client.dealer_exposures.get_snapshot(ticker) for ticker in tickers)
```

Pass the immutable records to the application's consumer. This example collects the batch before returning. Consume each result separately if the application needs partial progress. A long-running service can open the client at startup and close it at shutdown instead of opening one per request.

With `AsyncSharketoClient`, use `async with` and await each HTTP method. HTTP methods read on demand. To repeat reads, schedule calls within access and rate budgets. Repeated reads do not force a backend refresh, guarantee newer data or make separate requests transactional. Unless a family documents otherwise, it has no SDK background poller or stream.

Choose timeouts, response-size limits and bounded retries for the application. See [client options](sdk.md#clients-and-subscriptions) for defaults and limits.

## Streams

Construct, use and close each async client in one event loop. Close its subscriptions and the client on stop, cancellation or failure. Reuse a client across related subscriptions instead of creating one on each display rerun.

For prices, retain the snapshot wrapper and the subscription. The holder below keeps only the latest snapshot. The consumer receives complete immutable replacement quotes, not ticks or raw protocol frames. See [price semantics](prices.md). Keep callback work short and nonblocking, or pass it to a bounded queue or adapter.

```python
from dataclasses import dataclass
from sharketo import AsyncSharketoClient, PriceStreamSnapshot, PriceSubscription


@dataclass
class PriceState:
    subscription: PriceSubscription | None = None
    snapshot: PriceStreamSnapshot | None = None


async def watch_prices(
    api_key, api_url, websocket_url, ticker, state, consume, *, max_reconnects=5
):
    state.subscription = None
    state.snapshot = None
    async with AsyncSharketoClient(
        api_key=api_key,
        api_url=api_url,
        websocket_url=websocket_url,
        max_reconnects=max_reconnects,
    ) as client:
        async with client.subscribe_prices(ticker) as sub:
            state.subscription = sub
            async for snapshot in sub:
                state.snapshot = snapshot
                consume(snapshot)


def price_status(state):
    snapshot = state.snapshot
    return {
        "transport": state.subscription.status if state.subscription else None,
        "disconnected": snapshot.disconnected if snapshot else None,
        "receipt_age_seconds": snapshot.receipt_age_seconds if snapshot else None,
    }
```

Have the application's runner await the coroutine or task. Cancel it or use the application's stop mechanism, then wait for cleanup. Set an explicit timeout when the application or validation session needs one. A script can use `asyncio.run()`. Jupyter uses top-level await on its existing loop. Do not share a client across loops. If the UI runs elsewhere, pass data and status through a thread-safe adapter.

Refresh status independently of snapshot arrival. Subscription iteration yields replacement snapshots, ends or raises an error. Connectivity changes and advancing ages do not yield items. Have the application's timer or status endpoint re-read `price_status(state)` at its chosen interval. Retained wrappers become disconnected during recovery or cleanup and stay disconnected across connection generations until a new baseline replaces them. Receipt age is not source freshness or a price TTL.

For rich inventory, retain `InventoryStreamSnapshot`, consume its complete `.inventory`, and follow [inventory rendering](inventory-rendering.md). Disable `include_history` and `include_bookmap` for current-only views. Enable profiles separately when needed. Summary and crypto wrappers have their own documented age semantics.

A subscription-local `StreamError` ends that subscription and its shared consumers, not
unrelated healthy subscriptions. The application may explicitly create a new subscription
on the same healthy client after resolving the cause, under its bounded recovery policy.
Retirement/version errors do not trigger automatic reconnects. See
[terminal service errors](sdk.md#service-availability-and-compatible-versions).

`max_reconnects` applies across the client's stream manager lifetime. It does not reset after a successful connection. A terminal manager failure affects its subscriptions. Opening a new subscription on that client raises the stored error. Mark any retained result disconnected and close the failed client. Create a new client only under the application's bounded recovery policy. Diagnose authentication, entitlement and protocol failures instead of restarting blindly. The SDK handles transport recovery and new baselines. Applications do not reconstruct wire deltas.

## Configuration and error boundaries

Handle missing configuration and invalid arguments separately from operational `SharketoError` failures. Environment lookups can raise `KeyError`. SDK configuration and argument checks raise `ValueError`. Validate selections before starting background work. Report sanitized SDK metadata, not raw exceptions, bodies, headers, endpoint inputs or keys.

The recipe below calls the HTTP helper above. Its consumer runs outside the SDK error handler so application failures are not reported as SDK failures.

```python
import os
from sharketo import SharketoError


def sdk_error_metadata(error):
    fields = (
        "status_code",
        "code",
        "request_id",
        "retry_after",
        "required_capability",
        "suggested_plan",
    )
    return {
        "kind": type(error).__name__,
        **{name: getattr(error, name) for name in fields if getattr(error, name, None) is not None},
    }


def run_report(tickers, consume, report_issue):
    try:
        api_key = os.environ["SHARKETO_API_KEY"]
        api_url = os.environ.get("SHARKETO_API_URL")
        snapshots = read_dealer_snapshots(api_key, api_url, tickers)
    except (KeyError, ValueError):
        report_issue({"kind": "configuration"})
        return
    except SharketoError as error:
        report_issue(sdk_error_metadata(error))
        return
    for snapshot in snapshots:
        consume(snapshot)
```

Handle errors and observe task failures and cancellation in the application's stream task too. Do not fabricate fallback results or silently replace live data with synthetic data. See [SDK diagnostics](sdk.md#read-only-diagnostics-and-terminal-errors) for operational errors and read-only access checks.

## Separate application results from supplied data

Keep supplied SDK records, units, nulls and provenance unchanged. Label application calculations separately from SDK analytics. Do not replace a server total with a display subtotal.

### Calendar-date display

Render fields documented as calendar dates with their supplied meaning. Do not add midnight,
convert timezones or use these dates to estimate intraday freshness. Keep declared unknown
freshness separate from local receipt time.

```python
def calendar_date_label(value: str | None, *, label: str) -> str:
    return f"{label}: {value if value is not None else 'unknown'}"


assert calendar_date_label("2026-01-30", label="Engine index date") == (
    "Engine index date: 2026-01-30"
)
assert calendar_date_label(None, label="Analyzed source date") == "Analyzed source date: unknown"
```

Choose the label from the selected family's semantics. For CTA, pass `snapshot.as_of` with
`label="Engine index date"`; for RRG detail, use `label="Analyzed source date"`.
