# Agent validation

Use this workflow for agent-run checks of the user's application. For application integration, use the [application recipes](integration.md).

## Offline validation

1. Check the application's Python environment and match its SDK version to `metadata.version` in [SKILL.md](../SKILL.md). For install and upgrade steps, see [installation](install.md).
2. Select a family from the [capability router](../SKILL.md#select-a-capability) and run its installed-package synthetic fixture. `python -m sharketo.quickstart` also checks the installed package offline.
3. Check the application's behavior with synthetic or recorded inputs. Cover relevant distinctions such as null versus zero, units, supplied versus filtered values, availability, source time, receipt time, transport status and cleanup. Inventory fixtures also cover sparse observations, replacement state and continuity.

## Optional bounded live validation

Live checks require explicit user or operator approval and existing access. Without approval, stay offline. Never enable features, change billing or entitlements, provision or rotate keys, or weaken authentication to make a check pass.

For agent-run live checks, use an existing server-side `SHARKETO_API_KEY` and an explicit approved `SHARKETO_API_URL`. Streams also require `SHARKETO_WEBSOCKET_URL`. Configure secrets and environment variables before launching the process or notebook. Keep secrets out of browser widgets, notebooks and their outputs, URLs and logs. Clear live notebook outputs before sharing.

For a validation check:

- Use finite client and subscription contexts with explicit request and time limits. Set `max_retries=0` and, for streams, `max_reconnects=0`. Make only the approved reads and selections.
- For HTTP, call the selected family's documented methods directly. One read is enough to check one snapshot. For multi-endpoint behavior, make only the necessary calls.
- For prices and crypto, call their subscription factories without `await` or an inventory `get_access()` preflight. For inventory, `get_access()` provides optional read-only summary diagnostics, not rich-interest readiness. Use summaries for compact checks. Use rich streams only for selected chart state, with history and Bookmap disabled for current-only views.
- Retain the snapshot wrapper and payload to preserve disconnect and age signals. Follow [stream integration](integration.md#streams) for status refresh outside the iterator, bounded state and cleanup. End the check on timeout instead of silently restarting it.
- Follow [configuration and error handling](integration.md#configuration-and-error-boundaries) and collect only [sanitized diagnostics](sdk.md#read-only-diagnostics-and-terminal-errors). Stop on terminal or protocol errors. Report live failures rather than substituting synthetic data.
