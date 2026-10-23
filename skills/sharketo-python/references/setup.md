# First-time API key setup

For existing access failures, use [read-only access diagnostics](sdk.md#read-only-diagnostics-and-terminal-errors).
Live checks follow the separate [validation workflow](workflow.md#optional-bounded-live-validation).

## 1. Open the portal and check eligibility

Direct the user to [Sharketo User Profile](https://sharketo.com/user/profile), then the
**API Key** section. The user completes sign-in, email verification and any identity
re-verification. Do not collect their password, verification codes or session tokens.

The labels below are in English and may be localized. If controls differ or **Generate Key**
is unavailable, ask for non-secret labels or the eligibility message. Follow the portal's
current requirements; leave account and subscription changes to the user or operator.
Continue when the user can identify the key section and its current state.

## 2. Review the terms and reuse or generate a key

The user personally reviews and accepts the current terms through **Read Developer API terms**
in the API Key section. Wait for the portal to confirm acceptance: the server records the
accepted version and time for the account, not just the current visit or key. Acceptance
survives later visits, key rotation and deletion. Existing keys and prior visits do not
imply acceptance; existing key holders can accept without replacing their key.

Agents must not check the agreement box, submit acceptance or call an acceptance endpoint
on the user's behalf. Never generate or rotate a key to satisfy agreement. If the portal
cannot load the status or reports a document-version mismatch, stop and ask the user to
reload/update the portal and review the displayed current document; do not accept an
unseen revision. Account acceptance does not bypass feature availability, entitlements or
content-specific conditions.

- If the portal shows a masked key, help the user locate their saved secret in their own
  secret tooling. The portal cannot reveal the full existing key again.
- If there is no key, explain the one-time reveal before the user chooses **Generate Key**.
  The user completes the terms agreement and any re-verification before key creation,
  copies the new key directly into their secret tooling, and selects **I've Saved It** only
  after storing it.
- If the key is lost, stop. Explain that **Regenerate Key** immediately invalidates the current
  key and can break every integration using it. Rotation requires a separate explicit request
  that acknowledges this impact and a plan to update affected applications. **Delete Key**
  also breaks integrations immediately.

Never ask the user to paste the key into chat. Do not read the clipboard or capture a key
reveal through screenshots, page or DOM extraction, browser recordings or tool output.
Finish this step when the user confirms they have stored the key securely.

### Optional browser-assisted navigation

Use browser tools only with explicit permission for the browser session and navigation.
Inspect only pages or regions without keys, and pause for the user to authenticate.
Stop automation before any terms agreement/acceptance and let the user complete it personally.
Also stop before **Generate Key** or any action that can reveal a secret. The user generates,
copies and saves the key manually. Resume inspection only after the user confirms acceptance
is complete and any key reveal is closed.

## 3. Configure the application's server-side secret

Have the user supply the saved key as `SHARKETO_API_KEY` through the application's existing
server-side environment or secret manager. Keep it out of shell commands and history,
source control, frontend bundles, browser widgets, notebook cells and outputs, URLs and logs.
Do not add a credential input widget to the application. Use masked secret-entry tooling.

Follow [endpoint and environment configuration](integration.md#endpoints-and-environment-configuration)
for `from_env()`, default and custom endpoints, and process lifetime. Match the key to the
intended environment.

With the user's permission, check only whether `SHARKETO_API_KEY` is nonempty in the
application's execution environment. Report only configured or missing. Do not dump the
environment or read secret-file contents. If the agent cannot check safely, ask the user to
confirm configuration.

## 4. Finish offline; validate live only on request

Run the [installed SDK's offline quickstart](install.md#verify-the-installed-sdk-offline)
if package usability needs checking. Setup is complete when the user has stored the key
and configured the intended server-side runtime.

If the user separately approves a live check, follow the
[bounded validation workflow](workflow.md#optional-bounded-live-validation) and the selected
[capability guide](../SKILL.md#select-a-capability). Check only the requested capability.
Use `get_access()` only for inventory-summary diagnostics.
