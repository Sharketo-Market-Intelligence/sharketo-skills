---
name: sharketo-python
description: Use when integrating the Sharketo Python SDK into an application, service, report, notebook or dashboard. Covers Index Inventory, prices, crypto inventory, Dealer Exposures, expiry flow, daily history, Seasonality, Volatility, RRG and CTA Flow APIs, async streams, data interpretation, installation, first-time API key setup and read-only access diagnostics.
license: LICENSE
metadata:
  version: "0.1.14b2"
---

# Sharketo Python SDK

## Personal-use scope

Developer access covers private, noncommercial applications used only by the subscriber.
Work for an employer or client is outside this scope. See
[personal-use boundaries](references/integration.md#personal-use-boundaries) for hosting,
sharing and code publication.

## Start from the user's application

1. If the SDK is missing or its version is uncertain, follow [installation](references/install.md) for the matching TestPyPI beta and offline verification. Skill installation alone does not install the SDK.
2. Select a family below and read its API and data semantics before coding. For client options, summary models, errors or stream limits, read the relevant section of the [SDK reference](references/sdk.md).
3. Use [application integration](references/integration.md) for client reuse, stream lifecycle, status refresh and error handling.
4. Check the changed behavior with the application's tests and the relevant guide's offline fixture. For agent-run live checks, follow the [validation workflow](references/workflow.md).

## Select a capability

| Requested data | Reference |
| --- | --- |
| SPX/NDX compact inventory summaries | [SDK clients and summary models](references/sdk.md#clients-and-subscriptions) |
| SPX/NDX strike contributions, exposure/spot/IV history, session Bookmap | [Inventory rendering](references/inventory-rendering.md) |
| Opt-in conditional-price exposure profiles | [Profiles](references/profiles.md) |
| SPX/NDX replacement quotes | [Prices](references/prices.md) |
| BTC/ETH current crypto exposure state | [Crypto inventory](references/crypto-inventory.md) |
| SPX/NDX/SPY/QQQ cache-only dealer snapshots | [Dealer Exposures](references/dealer-exposures.md) |
| SPX/NDX expiry-flow latest and selected hourly history | [Expiry flow](references/expiry-flow.md) |
| Bounded daily reconstructed inventory history | [Daily history](references/daily-history.md) |
| Full per-asset seasonal analysis and compact seasonal tables | [Seasonality](references/seasonality.md) |
| Curated volatility catalog, asset and term-structure snapshots | [Volatility](references/volatility.md) |
| Curated relative-rotation catalog, group and screener snapshots | [RRG](references/rrg.md) |
| Modeled positioning and scenario-flow snapshot | [CTA Flow](references/cta-flow.md) |
| SDK/skill installation, version matching, host discovery or export | [Installation](references/install.md) |
| Portal API key creation or first-time server-side credential configuration | [First-time API key setup](references/setup.md) |
| Access failures and sanitized diagnostics | [SDK error boundary](references/sdk.md#read-only-diagnostics-and-terminal-errors) |

## Common boundaries

- Consume complete replacement states instead of handling raw full, delta or tail messages.
- Preserve supplied financial values, classifications, units, signs, provenance and null versus zero. Label application calculations separately.
- Keep source time, publication time, receipt time and transport status separate. If source freshness is unknown, leave it unknown.
- Keep API keys server-side and out of browser inputs, frontend bundles, notebook cells and outputs, URLs and logs.
- For production defaults or custom environments, follow [endpoint configuration](references/integration.md#endpoints-and-environment-configuration).
