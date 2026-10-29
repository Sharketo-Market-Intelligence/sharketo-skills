# CTA Flow, SDK 0.1.14b4

For client reuse and repeated reads, see [application integration](integration.md#http-reads).

## Verified boundary

- Call `client.cta_flow.get_snapshot()` synchronously, or await the same call on
  `AsyncSharketoClient`. It makes a GET to the fixed `/v1/developer/cta-flow/snapshot`
  endpoint. It accepts no arguments, query, ticker or arbitrary artifact path. There is no
  preflight, WebSocket, built-in poller or client cache. One explicit call fetches one snapshot.
  `get_access()` remains inventory-specific.
- The root-exported frozen `CtaFlowSnapshotV1`, `CtaFlowPositioningV1` and
  `CtaFlowScenarioFlowsV1` use snake_case attributes. `.model_dump(mode="json", by_alias=True)`
  emits camelCase. Numeric fields are required and nullable. Non-null values are finite.
  Preserve signed values, zero, null and source rounding. All-null data is valid, not an
  unavailable artifact.
- `positioning.cta/risk_parity/volatility_control/total` are modeled global equity
  positioning across CTA, risk parity and volatility control. `scenario_flows.up/median/down`
  are combined modeled changes over `scenario_horizon_trading_days=5`. The horizon is
  measured in trading days, not application-derived calendar dates. The labels have no
  supplied fixed shocks or probabilities, and there is no promised scenario ordering.
- `unit="usdBillions"` is already scaled. Display literal values. Never multiply by a
  billion or recompute the authoritative server total from components. Components' last
  non-null values can differ from the total's common-date inputs. The SDK transports the
  backend's modeled scenarios without recomputing estimates or calculating additional
  forecasts. Keep application comparisons, rankings and alerts distinct from backend
  outputs. These are model estimates, not observed holdings or flows, executed trades,
  live data or recommendations.
- `as_of` is a required nullable canonical calendar date with
  `as_of_semantics="lastEngineIndexDate"`. It is not component freshness, publication
  time, artifact modification time or local fetch completion. Preserve
  `per_metric_freshness="unknown"`. Do not infer a TTL, readiness or live health.
  Keep local fetch metadata separate.
- Access requires effective Apex access through `developer_api`, an API key, verified
  email, `ApiKeys` and `Models`. Existing key
  restrictions and a separate shared-account CTA budget of 60 requests per minute apply.
  All responses are no-store.
  Typed `APIError` includes 404 `FEATURE_NOT_AVAILABLE`, 403 `EMAIL_NOT_VERIFIED` or
  `SUBSCRIPTION_REQUIRED`, 429 `RATE_LIMITED` with Retry-After, and sanitized 503
  `CTA_FLOW_UNAVAILABLE` or `DEPENDENCY_UNAVAILABLE`. Missing, corrupt, unreadable or
  oversized artifacts fail. Never replace these failures with successful zero or empty data.

## Offline validation fixture, synthetic HTTP

The total deliberately differs from the component sum. The fixture also
includes a negative up scenario, zero and null to check that these values retain their supplied meanings.

```python
import httpx
from sharketo import SharketoClient

payload = {
    "schemaVersion": "cta-flow-snapshot.v1",
    "asOf": "2026-01-30",
    "asOfSemantics": "lastEngineIndexDate",
    "perMetricFreshness": "unknown",
    "unit": "usdBillions",
    "scenarioHorizonTradingDays": 5,
    "positioning": {"cta": -12.375, "riskParity": 0.0, "volatilityControl": None, "total": 8.125},
    "scenarioFlows": {"up": -0.625, "median": None, "down": 0.0},
}
requests = []


def respond(request):
    requests.append(request)
    assert request.method == "GET"
    assert request.url.path == "/v1/developer/cta-flow/snapshot"
    assert not request.url.query
    return httpx.Response(200, json=payload)


def number(value):
    return "unknown" if value is None else str(value)


with SharketoClient(
    "sk-shark-synthetic-only",
    "http://localhost",
    transport=httpx.MockTransport(respond),
    max_retries=0,
) as client:
    snapshot = client.cta_flow.get_snapshot()

print("MODEL ESTIMATE: global equity, not observed holdings/flows, trades or recommendations")
print("asOf:", snapshot.as_of, "last engine index date; per-metric freshness unknown")
print("Local fetch label: synthetic completion, not publication/source freshness")
print("Positioning | USD billions; authoritative server total, no component sum")
for label, value in (
    ("CTA", snapshot.positioning.cta),
    ("Risk parity", snapshot.positioning.risk_parity),
    ("Volatility control", snapshot.positioning.volatility_control),
    ("Total (server)", snapshot.positioning.total),
):
    print(label, number(value), sep=" | ")
print(
    "Scenario changes | USD billions over", snapshot.scenario_horizon_trading_days, "trading days"
)
for label, value in (
    ("Up", snapshot.scenario_flows.up),
    ("Median", snapshot.scenario_flows.median),
    ("Down", snapshot.scenario_flows.down),
):
    print(label, number(value), sep=" | ")
print("Scenario labels have no supplied fixed shocks/probabilities; not live data.")
assert len(requests) == 1
assert snapshot.model_dump(mode="json", by_alias=True) == payload
assert number(snapshot.positioning.cta) == "-12.375"
assert number(snapshot.positioning.risk_parity) == "0.0"
assert number(snapshot.positioning.volatility_control) == "unknown"
assert number(snapshot.positioning.total) == "8.125"
assert number(snapshot.scenario_flows.up) == "-0.625"
assert number(snapshot.scenario_flows.median) == "unknown"
assert number(snapshot.scenario_flows.down) == "0.0"
```

For separately approved agent-run live validation, follow the
[validation workflow](workflow.md). Obtain `SHARKETO_API_KEY` and `SHARKETO_API_URL`
from the process environment or secret tooling.
